"""
compare_with_job_description.py — Match resume content against a job description.

Two-layer matching:
  1. Keyword matching (exact + normalized)
  2. Semantic matching (OpenAI embeddings cosine similarity)

Usage:
    from tools.compare_with_job_description import compare_resume_with_jd
    result = compare_resume_with_jd(parsed_resume, jd_text, openai_api_key)
"""

import os
import sys
import json
import re
from pathlib import Path

import numpy as np


JD_EXTRACTION_PROMPT = """Extract structured information from this job description.

Return a JSON object with this structure:
{
  "title": "Job title",
  "company": "Company name or null",
  "experience_level": "entry/mid/senior/lead/principal/executive",
  "required_skills": ["Must-have skills and technologies"],
  "preferred_skills": ["Nice-to-have skills"],
  "responsibilities": ["Key job responsibilities"],
  "qualifications": ["Education and certification requirements"],
  "keywords": ["ALL important keywords for ATS matching — include skills, tools, concepts, methodologies"]
}

RULES:
1. Extract ALL technical skills, tools, frameworks, and methodologies mentioned.
2. "keywords" should be the comprehensive superset of everything relevant for ATS matching.
3. Distinguish clearly between required and preferred skills.
4. Return ONLY the JSON object.

JOB DESCRIPTION:
"""


def extract_jd_structure(jd_text: str, openai_api_key: str) -> dict:
    """Extract structured data from job description text via OpenAI."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You parse job descriptions into structured JSON. Output only valid JSON."},
                {"role": "user", "content": JD_EXTRACTION_PROMPT + jd_text},
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return {
            "success": True,
            "data": json.loads(content),
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
        }


def normalize_keyword(keyword: str) -> str:
    """Normalize a keyword for comparison."""
    k = keyword.lower().strip()
    k = re.sub(r"[^a-z0-9\+\#\.]", " ", k)
    k = re.sub(r"\s+", " ", k).strip()
    return k


def get_resume_keywords(parsed_resume: dict) -> set:
    """Extract all matchable keywords from a parsed resume."""
    keywords = set()

    # Skills
    skills = parsed_resume.get("skills", {})
    for category in ["languages", "frameworks", "tools", "databases", "cloud_platforms", "other"]:
        for skill in skills.get(category, []):
            keywords.add(normalize_keyword(skill))

    # Experience responsibilities
    for exp in parsed_resume.get("experience", []):
        for resp in exp.get("responsibilities", []):
            # Extract technical terms from bullet points
            words = resp.split()
            for word in words:
                cleaned = normalize_keyword(word)
                if len(cleaned) > 2:
                    keywords.add(cleaned)

    # Project technologies
    for proj in parsed_resume.get("projects", []):
        for tech in proj.get("technologies", []):
            keywords.add(normalize_keyword(tech))

    # Certifications
    for cert in parsed_resume.get("certifications", []):
        if cert.get("name"):
            keywords.add(normalize_keyword(cert["name"]))

    return keywords


def keyword_match(resume_keywords: set, jd_keywords: list) -> dict:
    """Perform keyword matching between resume and JD."""
    jd_normalized = {normalize_keyword(k): k for k in jd_keywords}

    matched = []
    missing = []

    for norm_key, original in jd_normalized.items():
        # Check exact match
        if norm_key in resume_keywords:
            matched.append(original)
        # Check if any resume keyword contains this JD keyword or vice versa
        elif any(norm_key in rk or rk in norm_key for rk in resume_keywords if len(rk) > 2):
            matched.append(original)
        else:
            missing.append(original)

    total = len(jd_normalized)
    match_ratio = len(matched) / total if total > 0 else 0

    return {
        "matched": matched,
        "missing": missing,
        "match_ratio": round(match_ratio, 3),
        "total_jd_keywords": total,
    }


def get_embedding(text: str, client, model: str = "text-embedding-3-small") -> list:
    """Get embedding vector for text."""
    response = client.embeddings.create(
        model=model,
        input=text[:8000],  # Truncate to stay within limits
    )
    return response.data[0].embedding


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))


def semantic_match(parsed_resume: dict, jd_text: str, openai_api_key: str) -> dict:
    """Compute semantic similarity between resume sections and JD."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        # Build resume section texts
        skills_text = ""
        skills = parsed_resume.get("skills", {})
        for category, items in skills.items():
            if items:
                skills_text += f"{category}: {', '.join(items)}. "

        experience_text = ""
        for exp in parsed_resume.get("experience", []):
            experience_text += f"{exp.get('role', '')} at {exp.get('company', '')}. "
            experience_text += " ".join(exp.get("responsibilities", [])) + " "

        projects_text = ""
        for proj in parsed_resume.get("projects", []):
            projects_text += f"{proj.get('title', '')}: {proj.get('description', '')}. "
            projects_text += f"Technologies: {', '.join(proj.get('technologies', []))}. "

        # Full resume text for overall similarity
        full_resume_text = f"{skills_text}\n{experience_text}\n{projects_text}"

        # Get embeddings
        jd_embedding = get_embedding(jd_text, client)

        results = {"overall_similarity": 0.0}

        if full_resume_text.strip():
            resume_embedding = get_embedding(full_resume_text, client)
            results["overall_similarity"] = round(cosine_similarity(resume_embedding, jd_embedding), 4)

        if skills_text.strip():
            skills_embedding = get_embedding(skills_text, client)
            results["skills_similarity"] = round(cosine_similarity(skills_embedding, jd_embedding), 4)

        if experience_text.strip():
            exp_embedding = get_embedding(experience_text, client)
            results["experience_similarity"] = round(cosine_similarity(exp_embedding, jd_embedding), 4)

        if projects_text.strip():
            proj_embedding = get_embedding(projects_text, client)
            results["projects_similarity"] = round(cosine_similarity(proj_embedding, jd_embedding), 4)

        return {
            "success": True,
            "data": results,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": {"overall_similarity": 0.0},
            "error": str(e),
        }


def compare_resume_with_jd(parsed_resume: dict, jd_text: str, openai_api_key: str) -> dict:
    """
    Full comparison between parsed resume and job description.

    Returns:
        {
            "success": bool,
            "data": {
                "jd_structured": dict,
                "keyword_match": { "matched": [], "missing": [], "match_ratio": float },
                "semantic_match": { "overall_similarity": float, ... },
            },
            "error": str | None
        }
    """
    if not jd_text or len(jd_text.strip()) < 20:
        return {
            "success": False,
            "data": None,
            "error": "Job description is too short (< 20 characters)",
        }

    # Step 1: Extract structured JD data
    jd_result = extract_jd_structure(jd_text, openai_api_key)
    if not jd_result["success"]:
        return {
            "success": False,
            "data": None,
            "error": f"JD extraction failed: {jd_result['error']}",
        }

    jd_structured = jd_result["data"]

    # Step 2: Keyword matching
    resume_keywords = get_resume_keywords(parsed_resume)
    jd_keywords = jd_structured.get("keywords", [])
    kw_result = keyword_match(resume_keywords, jd_keywords)

    # Step 3: Semantic matching
    sem_result = semantic_match(parsed_resume, jd_text, openai_api_key)

    return {
        "success": True,
        "data": {
            "jd_structured": jd_structured,
            "keyword_match": kw_result,
            "semantic_match": sem_result.get("data", {}),
        },
        "error": None,
    }


def main():
    """CLI usage for testing."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    if len(sys.argv) < 3:
        print("Usage: python compare_with_job_description.py <parsed_resume.json> <jd_text_file>")
        sys.exit(1)

    resume_path = sys.argv[1]
    jd_path = sys.argv[2]

    with open(resume_path) as f:
        parsed_resume = json.load(f)
    jd_text = Path(jd_path).read_text(encoding="utf-8")

    api_key = os.getenv("OPENAI_API_KEY")
    result = compare_resume_with_jd(parsed_resume, jd_text, api_key)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
