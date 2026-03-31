"""
app.py — Flask backend for the Resume Analyzer.

Endpoints:
    POST /api/analyze  — Upload resume + JD, run full analysis pipeline
    GET  /api/health   — Server health check
    GET  /api/history  — Fetch past analyses from MongoDB
    GET  /api/analysis/<id> — Fetch single analysis result

Usage:
    python app.py
"""

import os
import sys
import io
import json
import uuid
import traceback
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project root to path for tool imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.parse_resume import extract_text
from tools.extract_entities import extract_entities
from tools.compare_with_job_description import compare_resume_with_jd
from tools.score_resume import calculate_ats_score
from tools.generate_feedback import generate_feedback, save_analysis
from tools.docx_generator import generate_docx_report
from tools.resume_updater import update_docx_in_place

# ─── App Configuration ───────────────────────────────────────────────────────

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
TMP_DIR = Path(__file__).resolve().parent / ".tmp"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg", "bmp", "tiff", "webp"}

# Environment variables
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OCR_KEY = os.getenv("OCR_SPACE_API_KEY", "")
MONGO_URI = os.getenv("MONGODB_URI", "")
MONGO_DB = os.getenv("MONGODB_DB_NAME", "resume_analyzer")
MONGO_COLLECTION = os.getenv("MONGODB_COLLECTION", "analyses")


def get_mongo_collection():
    """Get MongoDB collection. Returns None if not configured."""
    if not MONGO_URI or "username:password" in MONGO_URI:
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[MONGO_DB]
        return db[MONGO_COLLECTION]
    except Exception:
        return None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def api_response(success: bool, data=None, error=None, status_code=200):
    """Standardized API response format."""
    return jsonify({
        "success": success,
        "data": data,
        "error": error,
    }), status_code


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    """Serve the frontend SPA."""
    return send_from_directory("frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """Serve static frontend files."""
    return send_from_directory("frontend", path)


@app.route("/api/health", methods=["GET"])
def health_check():
    """Server health check."""
    mongo_ok = False
    collection = get_mongo_collection()
    if collection is not None:
        try:
            collection.database.client.server_info()
            mongo_ok = True
        except Exception:
            pass

    return api_response(True, {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "groq": bool(GROQ_KEY and len(GROQ_KEY) > 10),
            "ocr_space": bool(OCR_KEY and OCR_KEY != "your_ocr_space_key_here"),
            "mongodb": mongo_ok,
        },
    })


@app.route("/api/download/docx", methods=["POST"])
def download_docx():
    """Generates a DOCX from the provided analysis JSON."""
    try:
        import json
        if request.is_json:
            data = request.json
        else:
            raw_data = request.form.get("data")
            data = json.loads(raw_data) if raw_data else None
            
        if not data:
            return api_response(False, error="No JSON data provided", status_code=400)
            
        docx_bytes = generate_docx_report(data)
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"Resume_Analysis_{data.get('ats_score', 'Report')}.docx"
        )
    except Exception as e:
        return api_response(False, error=str(e), status_code=500)


@app.route("/api/download/autofix-docx", methods=["POST"])
def autofix_docx():
    """Patches the original DOCX with AI-improved bullet points and returns the patched file."""
    try:
        import json
        if request.is_json:
            data = request.json
        else:
            raw_data = request.form.get("data")
            data = json.loads(raw_data) if raw_data else None

        if not data:
            return api_response(False, error="No JSON data provided", status_code=400)
            
        safe_filename = data.get("safe_filename")
        if not safe_filename:
            return api_response(False, error="No valid file reference found", status_code=400)
            
        file_path = str(TMP_DIR / safe_filename)
        if not os.path.exists(file_path):
            return api_response(False, error="Original file expired or missing from server", status_code=404)
            
        patched_bytes = update_docx_in_place(file_path, data)
        
        return send_file(
            io.BytesIO(patched_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"AutoFixed_{data.get('original_filename', 'Resume.docx')}"
        )
    except Exception as e:
        traceback.print_exc()
        return api_response(False, error="Failed to patch DOCX: " + str(e), status_code=500)


@app.route("/api/analyze", methods=["POST"])
def analyze_resume():
    """
    Full resume analysis pipeline.

    Expects multipart form data:
        - file: Resume file (PDF/DOCX/Image)
        - job_description: Target job description text
    """

    # ── Validate inputs ──────────────────────────────────────────────────────
    if "file" not in request.files:
        return api_response(False, error="No file uploaded", status_code=400)

    file = request.files["file"]
    if file.filename == "":
        return api_response(False, error="No file selected", status_code=400)

    if not allowed_file(file.filename):
        return api_response(
            False,
            error=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            status_code=400,
        )

    jd_text = request.form.get("job_description", "").strip()
    if not jd_text or len(jd_text) < 50:
        return api_response(
            False,
            error="Job description is required (minimum 50 characters)",
            status_code=400,
        )

    if not GROQ_KEY or len(GROQ_KEY) < 10:
        return api_response(
            False,
            error="Groq API key not configured. Set GROQ_API_KEY in .env",
            status_code=500,
        )

    # ── Save uploaded file ───────────────────────────────────────────────────
    try:
        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = str(UPLOAD_DIR / safe_filename)
        file.save(file_path)
    except Exception as e:
        return api_response(False, error=f"Failed to save uploaded file: {e}", status_code=500)

    # ── Pipeline ─────────────────────────────────────────────────────────────
    pipeline_status = {"stage": "starting", "stages_completed": []}

    try:
        # Stage 1: Extract text
        pipeline_status["stage"] = "text_extraction"
        text_result = extract_text(file_path, OCR_KEY)  # OCR unchanged
        if not text_result["success"]:
            return api_response(False, error=f"Text extraction failed: {text_result['error']}", status_code=422)
        if len(text_result["text"].strip()) < 20:
            return api_response(False, error="Could not extract meaningful text from resume. Try a different file format.", status_code=422)
        pipeline_status["stages_completed"].append("text_extraction")

        # Save intermediate
        tmp_text_path = TMP_DIR / f"{safe_filename}_text.txt"
        tmp_text_path.write_text(text_result["text"], encoding="utf-8")

        # Stage 2: Extract entities
        pipeline_status["stage"] = "entity_extraction"
        entity_result = extract_entities(text_result["text"], GROQ_KEY)
        if not entity_result["success"]:
            return api_response(False, error=f"Entity extraction failed: {entity_result['error']}", status_code=422)

        parsed_resume = entity_result["data"]
        parsed_resume["raw_text"] = text_result["text"]
        parsed_resume["extraction_method"] = text_result["method"]
        pipeline_status["stages_completed"].append("entity_extraction")

        # Save intermediate
        tmp_parsed_path = TMP_DIR / f"{safe_filename}_parsed.json"
        tmp_parsed_path.write_text(json.dumps(parsed_resume, indent=2), encoding="utf-8")

        # Stage 3: Compare with JD
        pipeline_status["stage"] = "jd_comparison"
        comparison_result = compare_resume_with_jd(parsed_resume, jd_text, GROQ_KEY)
        if not comparison_result["success"]:
            return api_response(False, error=f"JD comparison failed: {comparison_result['error']}", status_code=422)

        comparison_data = comparison_result["data"]
        pipeline_status["stages_completed"].append("jd_comparison")

        # Stage 4: Calculate ATS score
        pipeline_status["stage"] = "scoring"
        score_result = calculate_ats_score(parsed_resume, comparison_data, GROQ_KEY)
        if not score_result["success"]:
            return api_response(False, error=f"Scoring failed: {score_result['error']}", status_code=422)

        score_data = score_result["data"]
        pipeline_status["stages_completed"].append("scoring")

        # Stage 5: Generate feedback
        pipeline_status["stage"] = "feedback_generation"
        feedback_result = generate_feedback(parsed_resume, score_data, comparison_data, jd_text, GROQ_KEY)
        if not feedback_result["success"]:
            return api_response(False, error=f"Feedback generation failed: {feedback_result['error']}", status_code=422)

        final_analysis = feedback_result["data"]
        final_analysis["original_filename"] = file.filename
        final_analysis["safe_filename"] = safe_filename
        pipeline_status["stages_completed"].append("feedback_generation")

        # ── Save results ─────────────────────────────────────────────────────
        output_path = save_analysis(final_analysis, str(OUTPUT_DIR))

        # Save to MongoDB if configured
        collection = get_mongo_collection()
        if collection is not None:
            try:
                # MongoDB doesn't like the full parsed_resume embedded (too large sometimes)
                mongo_doc = {**final_analysis}
                collection.insert_one(mongo_doc)
                final_analysis.pop("_id", None)  # Remove MongoDB _id from response
            except Exception as e:
                # Don't fail the whole request if MongoDB write fails
                final_analysis["mongodb_error"] = str(e)

        pipeline_status["stage"] = "complete"
        pipeline_status["stages_completed"].append("storage")

        return api_response(True, final_analysis)

    except Exception as e:
        traceback.print_exc()
        return api_response(
            False,
            error=f"Pipeline failed at stage '{pipeline_status['stage']}': {str(e)}",
            status_code=500,
        )
    finally:
        # Clean up uploaded file (keep a copy in .tmp for debugging)
        try:
            import shutil
            shutil.copy2(file_path, str(TMP_DIR / safe_filename))
            os.remove(file_path)
        except Exception:
            pass


@app.route("/api/history", methods=["GET"])
def get_history():
    """Fetch past analyses."""
    # Try MongoDB first
    collection = get_mongo_collection()
    if collection is not None:
        try:
            analyses = list(collection.find(
                {},
                {
                    "analysis_id": 1,
                    "timestamp": 1,
                    "ats_score": 1,
                    "score_band": 1,
                    "original_filename": 1,
                    "job_description.title": 1,
                    "_id": 0,
                },
            ).sort("timestamp", -1).limit(50))

            return api_response(True, analyses)
        except Exception as e:
            pass  # Fall through to file-based history

    # Fallback: read from outputs/ directory
    analyses = []
    for f in sorted(OUTPUT_DIR.glob("analysis_*.json"), reverse=True)[:50]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            analyses.append({
                "analysis_id": data.get("analysis_id"),
                "timestamp": data.get("timestamp"),
                "ats_score": data.get("ats_score"),
                "score_band": data.get("score_band"),
                "original_filename": data.get("original_filename"),
            })
        except Exception:
            continue

    return api_response(True, analyses)


@app.route("/api/analysis/<analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    """Fetch a single analysis result."""
    # Try MongoDB first
    collection = get_mongo_collection()
    if collection is not None:
        try:
            doc = collection.find_one({"analysis_id": analysis_id}, {"_id": 0})
            if doc:
                return api_response(True, doc)
        except Exception:
            pass

    filepath = OUTPUT_DIR / f"analysis_{analysis_id}.json"
    if filepath.exists():
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return api_response(True, data)

    return api_response(False, error="Analysis not found", status_code=404)


@app.route("/api/history/<analysis_id>", methods=["DELETE"])
def delete_history(analysis_id):
    """Delete a specific analysis from history."""
    
    # Try MongoDB first
    collection = get_mongo_collection()
    if collection is not None:
        try:
            collection.delete_one({"analysis_id": analysis_id})
        except Exception as e:
            print(f"MongoDB delete error for {analysis_id}: {e}")
            
    # Delete from local fallback storage
    filepath = OUTPUT_DIR / f"analysis_{analysis_id}.json"
    if filepath.exists():
        try:
            os.remove(filepath)
        except Exception as e:
            import time
            time.sleep(0.2) # Small wait if antivirus/Windows locked the read handle
            try:
                os.remove(filepath)
            except Exception as e2:
                print(f"Local delete error for {analysis_id}: {e2}")
            
    # For a DELETE op on history, it is idempotent. Always return success.
    return api_response(True, {"message": "Analysis deleted"})


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    print(f"\n🚀  Resume Analyzer API starting on http://localhost:{port}")
    print(f"    Groq:     {'configured' if GROQ_KEY and len(GROQ_KEY) > 10 else 'not configured'}")
    print(f"    OCR:      {'configured' if OCR_KEY and OCR_KEY != 'your_ocr_space_key_here' else 'not configured'}")
    print(f"    MongoDB:  {'configured' if MONGO_URI and 'username:password' not in MONGO_URI else 'not configured'}")
    print()

    app.run(host="0.0.0.0", port=port, debug=debug)
