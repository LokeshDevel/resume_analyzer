"""
extract_entities.py — Convert raw resume text into structured JSON via DeepSeek.
"""

import os, sys, json
from pathlib import Path

EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured data from the following resume text.

Return a JSON object with EXACTLY this structure. Use null for missing strings, empty arrays for missing lists.

{
  "personal_info": {
    "name": null, "email": null, "phone": null, "location": null,
    "linkedin": null, "github": null, "portfolio": null, "summary": null
  },
  "education": [
    { "institution": "", "degree": "", "field_of_study": null, "gpa": null,
      "start_date": null, "end_date": null, "honors": null }
  ],
  "skills": {
    "languages": [], "frameworks": [], "tools": [], "databases": [],
    "cloud_platforms": [], "soft_skills": [], "other": []
  },
  "experience": [
    { "company": "", "role": "", "location": null, "start_date": null,
      "end_date": null, "is_current": false, "responsibilities": [] }
  ],
  "projects": [
    { "title": "", "description": null, "technologies": [], "impact": null, "url": null, "github": null }
  ],
  "certifications": [
    { "name": "", "issuer": null, "date": null, "credential_id": null }
  ],
  "links": [ { "label": "", "url": "" } ],
  "confidence_notes": []
}

RULES:
1. Extract ONLY what is in the text. Never invent information.
2. Keep bullet points exactly as written.
3. Return ONLY the JSON object — no markdown, no explanation.

RESUME TEXT:
"""


def extract_entities(raw_text: str, api_key: str) -> dict:
    if not raw_text or len(raw_text.strip()) < 20:
        return {"success": False, "data": None, "error": "Resume text too short", "tokens_used": 0}
    if not api_key:
        return {"success": False, "data": None, "error": "GROQ_API_KEY not provided", "tokens_used": 0}
    try:
        from tools.llm_client import generate_json
        parsed = generate_json(EXTRACTION_PROMPT + raw_text, api_key)
        return {"success": True, "data": parsed, "error": None, "tokens_used": 0}
    except Exception as e:
        return {"success": False, "data": None, "error": f"Entity extraction failed: {e}", "tokens_used": 0}


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if len(sys.argv) < 2:
        print("Usage: python extract_entities.py <text_file>")
        sys.exit(1)
    raw_text = Path(sys.argv[1]).read_text(encoding="utf-8") if Path(sys.argv[1]).exists() else sys.argv[1]
    result = extract_entities(raw_text, os.getenv("GROQ_API_KEY"))
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
