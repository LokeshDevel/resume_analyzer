"""
compare_with_job_description.py — Match resume vs JD using DeepSeek + local keyword matching.
No embedding calls — uses deterministic keyword matching only (faster, no quota issues).
"""

import os, sys, json, re
from pathlib import Path

JD_EXTRACTION_PROMPT = """Extract structured information from this job description.

Return a JSON object:
{
  "title": "Job title",
  "company": null,
  "experience_level": "entry/mid/senior/lead/principal/executive",
  "required_skills": [],
  "preferred_skills": [],
  "responsibilities": [],
  "qualifications": [],
  "keywords": []
}

"keywords" must be the full ATS superset — all skills, tools, frameworks, technologies, concepts mentioned.
Return ONLY the JSON object.

JOB DESCRIPTION:
"""


def normalize_keyword(k: str) -> str:
    if not isinstance(k, str):
        return ""
    k = k.lower().strip()
    k = re.sub(r"[^a-z0-9\+\#\.]", " ", k)
    return re.sub(r"\s+", " ", k).strip()


def get_resume_keywords(parsed_resume: dict) -> set:
    keywords = set()
    for cat in ["languages", "frameworks", "tools", "databases", "cloud_platforms", "other"]:
        skills_list = parsed_resume.get("skills", {}).get(cat, []) or []
        for s in skills_list:
            if s: keywords.add(normalize_keyword(s))
    for exp in parsed_resume.get("experience", []) or []:
        for r in exp.get("responsibilities", []) or []:
            if r:
                for w in r.split():
                    c = normalize_keyword(w)
                    if len(c) > 2:
                        keywords.add(c)
    for proj in parsed_resume.get("projects", []) or []:
        for t in proj.get("technologies", []) or []:
            if t: keywords.add(normalize_keyword(t))
    return keywords


def keyword_match(resume_keywords: set, jd_keywords: list) -> dict:
    jd_keywords = jd_keywords or []
    jd_norm = {normalize_keyword(k): k for k in jd_keywords if isinstance(k, str)}
    matched, missing = [], []
    for norm, original in jd_norm.items():
        if norm in resume_keywords or any(norm in rk or rk in norm for rk in resume_keywords if len(rk) > 2):
            matched.append(original)
        else:
            missing.append(original)
    total = len(jd_norm)
    return {"matched": matched, "missing": missing,
            "match_ratio": round(len(matched) / total, 3) if total else 0,
            "total_jd_keywords": total}


def compare_resume_with_jd(parsed_resume: dict, jd_text: str, api_key: str) -> dict:
    if not jd_text or len(jd_text.strip()) < 20:
        return {"success": False, "data": None, "error": "Job description too short"}

    try:
        from tools.llm_client import generate_json

        # Step 1: Extract JD structure (1 LLM call)
        jd_structured = generate_json(JD_EXTRACTION_PROMPT + jd_text, api_key)

        # Step 2: Keyword matching (fully deterministic, no API call)
        resume_keywords = get_resume_keywords(parsed_resume)
        kw_result = keyword_match(resume_keywords, jd_structured.get("keywords", []) or [])

        # Use keyword match ratio as similarity proxy (no embedding calls needed)
        similarity = kw_result["match_ratio"]

        return {
            "success": True,
            "data": {
                "jd_structured": jd_structured,
                "keyword_match": kw_result,
                "semantic_match": {"overall_similarity": round(similarity, 4)},
            },
            "error": None,
        }

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if len(sys.argv) < 3:
        print("Usage: python compare_with_job_description.py <parsed_resume.json> <jd_text_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        parsed_resume = json.load(f)
    jd_text = Path(sys.argv[2]).read_text(encoding="utf-8")
    result = compare_resume_with_jd(parsed_resume, jd_text, os.getenv("GROQ_API_KEY"))
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
