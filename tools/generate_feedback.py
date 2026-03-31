"""
generate_feedback.py — Produce improvement suggestions via DeepSeek with retry.
"""

import os, sys, json, uuid
from pathlib import Path
from datetime import datetime, timezone

FEEDBACK_PROMPT = """You are an expert career coach. Given this resume analysis, generate improvement suggestions.

RESUME DATA:
{resume_json}

JOB DESCRIPTION:
{jd_text}

ATS SCORE: {ats_score}/100 ({score_band})
MATCHED KEYWORDS: {matched}
MISSING KEYWORDS: {missing}

CATEGORY SCORES:
{category_details}

Return a JSON object with EXACTLY this structure:
{{
  "strengths": ["3-5 specific resume strengths"],
  "weaknesses": ["3-5 specific resume weaknesses"],
  "recommendations": [
    {{ "section": "skills|experience|projects|education|summary|formatting", "priority": "high|medium|low", "suggestion": "Specific actionable suggestion" }}
  ],
  "rewritten_summary": "Compelling 2-3 sentence professional summary tailored to the JD.",
  "improved_bullet_points": [
    {{ "original": "Original bullet", "improved": "Improved with STAR method and metrics", "section": "experience|projects" }}
  ]
}}

RULES: Be specific and actionable. Address missing keywords. Max 5 improved bullet points. Return ONLY JSON.
"""


def generate_feedback(parsed_resume, score_data, comparison_data, jd_text, api_key):
    if not api_key:
        return {"success": False, "data": None, "error": "GROQ_API_KEY not provided"}
    try:
        from tools.llm_client import generate_json

        category_details = "\n".join(
            f"  - {n.replace('_',' ').title()}: {c['score']}/100 (weight:{c['weight']}%) — {c.get('details','')}"
            for n, c in score_data.get("category_scores", {}).items()
        )

        kw_match = comparison_data.get("keyword_match", {})
        prompt = FEEDBACK_PROMPT.format(
            resume_json=json.dumps(parsed_resume, indent=2)[:3000],
            jd_text=jd_text[:2000],
            ats_score=score_data.get("ats_score", 0),
            score_band=score_data.get("score_band", "Unknown"),
            matched=", ".join(kw_match.get("matched", [])),
            missing=", ".join(kw_match.get("missing", [])),
            category_details=category_details,
        )

        feedback = generate_json(prompt, api_key)

        final_analysis = {
            "analysis_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ats_score": score_data.get("ats_score", 0),
            "score_band": score_data.get("score_band", "Unknown"),
            "category_scores": score_data.get("category_scores", {}),
            "matched_keywords": kw_match.get("matched", []),
            "missing_keywords": kw_match.get("missing", []),
            "semantic_similarity": comparison_data.get("semantic_match", {}).get("overall_similarity", 0),
            "strengths": feedback.get("strengths", []),
            "weaknesses": feedback.get("weaknesses", []),
            "recommendations": feedback.get("recommendations", []),
            "rewritten_summary": feedback.get("rewritten_summary"),
            "improved_bullet_points": feedback.get("improved_bullet_points", []),
            "parsed_resume": parsed_resume,
            "job_description": comparison_data.get("jd_structured", {}),
        }
        return {"success": True, "data": final_analysis, "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": f"Feedback generation failed: {e}"}


def save_analysis(analysis: dict, output_dir: str = "outputs") -> str:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"analysis_{analysis.get('analysis_id','unknown')}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    return filepath


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if len(sys.argv) < 4:
        print("Usage: python generate_feedback.py <parsed_resume.json> <score_data.json> <comparison_data.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f: parsed_resume = json.load(f)
    with open(sys.argv[2]) as f: score_data = json.load(f)
    with open(sys.argv[3]) as f: comparison_data = json.load(f)
    jd_text = Path(sys.argv[4]).read_text(encoding="utf-8") if len(sys.argv) > 4 else ""
    result = generate_feedback(parsed_resume, score_data, comparison_data, jd_text, os.getenv("GROQ_API_KEY"))
    if result["success"]:
        print(f"Saved to: {save_analysis(result['data'])}")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
