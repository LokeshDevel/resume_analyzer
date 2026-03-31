"""
score_resume.py — Weighted ATS scoring engine.

Produces a score out of 100 across 7 categories with configurable weights.

Usage:
    from tools.score_resume import calculate_ats_score
    result = calculate_ats_score(parsed_resume, comparison_data, openai_api_key)
"""

import os
import sys
import json
from pathlib import Path


# Scoring weights (must sum to 100)
WEIGHTS = {
    "keyword_match": 30,
    "skill_relevance": 20,
    "project_quality": 15,
    "experience_alignment": 15,
    "resume_formatting": 10,
    "education_fit": 5,
    "grammar_readability": 5,
}

SCORE_BANDS = [
    (85, 100, "Excellent"),
    (70, 84, "Strong"),
    (50, 69, "Needs Improvement"),
    (0, 49, "Weak"),
]


def get_score_band(score: float) -> str:
    """Get the human-readable score band for a given score."""
    for low, high, band in SCORE_BANDS:
        if low <= score <= high:
            return band
    return "Unknown"


def score_keyword_match(comparison_data: dict) -> dict:
    """Score keyword matching (deterministic)."""
    kw = comparison_data.get("keyword_match", {})
    match_ratio = kw.get("match_ratio", 0)
    matched = kw.get("matched", [])
    missing = kw.get("missing", [])

    # Raw score based on match ratio
    raw_score = match_ratio * 100

    return {
        "score": round(raw_score, 1),
        "weight": WEIGHTS["keyword_match"],
        "weighted_score": round(raw_score * WEIGHTS["keyword_match"] / 100, 2),
        "details": f"Matched {len(matched)}/{len(matched) + len(missing)} JD keywords ({match_ratio:.0%})",
    }


def score_skill_relevance(parsed_resume: dict, comparison_data: dict) -> dict:
    """Score skill relevance against JD requirements (deterministic)."""
    jd = comparison_data.get("jd_structured", {})
    required = jd.get("required_skills", [])
    preferred = jd.get("preferred_skills", [])
    matched = [k.lower() for k in comparison_data.get("keyword_match", {}).get("matched", []) if k]

    # Count required skills matched
    required_matched = sum(1 for s in required if s.lower() in matched or
                           any(s.lower() in m for m in matched))
    required_ratio = required_matched / len(required) if required else 0.5

    # Count preferred skills matched
    preferred_matched = sum(1 for s in preferred if s.lower() in matched or
                            any(s.lower() in m for m in matched))
    preferred_ratio = preferred_matched / len(preferred) if preferred else 0.5

    # 80% weight on required, 20% on preferred
    raw_score = (required_ratio * 80 + preferred_ratio * 20)

    return {
        "score": round(raw_score, 1),
        "weight": WEIGHTS["skill_relevance"],
        "weighted_score": round(raw_score * WEIGHTS["skill_relevance"] / 100, 2),
        "details": f"Required: {required_matched}/{len(required)}, Preferred: {preferred_matched}/{len(preferred)}",
    }


def score_project_quality(parsed_resume: dict, comparison_data: dict) -> dict:
    """Score project quality (heuristic-based)."""
    projects = parsed_resume.get("projects", [])

    if not projects:
        return {
            "score": 20,
            "weight": WEIGHTS["project_quality"],
            "weighted_score": round(20 * WEIGHTS["project_quality"] / 100, 2),
            "details": "No projects section found",
        }

    total_points = 0
    max_points = len(projects) * 100

    jd_keywords = [k.lower() for k in comparison_data.get("jd_structured", {}).get("keywords", []) if k]

    for proj in projects:
        points = 0

        # Has title (10 pts)
        if proj.get("title"):
            points += 10

        # Has description (15 pts)
        if proj.get("description") and len(proj["description"]) > 20:
            points += 15

        # Has technologies listed (20 pts)
        techs = proj.get("technologies", [])
        if techs:
            points += 20

        # Technologies match JD (25 pts)
        if techs and jd_keywords:
            tech_matched = sum(1 for t in techs if t.lower() in jd_keywords or
                               any(t.lower() in k for k in jd_keywords))
            points += min(25, tech_matched * 10)

        # Quantified impact (20 pts)
        impact = proj.get("impact", "") or proj.get("description", "")
        if impact and any(c.isdigit() for c in impact):
            points += 20

        # Has URL/GitHub (10 pts)
        if proj.get("url") or proj.get("github"):
            points += 10

        total_points += min(100, points)

    raw_score = (total_points / max_points) * 100 if max_points > 0 else 0

    return {
        "score": round(raw_score, 1),
        "weight": WEIGHTS["project_quality"],
        "weighted_score": round(raw_score * WEIGHTS["project_quality"] / 100, 2),
        "details": f"{len(projects)} projects evaluated",
    }


def score_experience_alignment(parsed_resume: dict, comparison_data: dict) -> dict:
    """Score experience alignment with JD (heuristic-based)."""
    experience = parsed_resume.get("experience", [])

    if not experience:
        return {
            "score": 15,
            "weight": WEIGHTS["experience_alignment"],
            "weighted_score": round(15 * WEIGHTS["experience_alignment"] / 100, 2),
            "details": "No experience section found",
        }

    jd = comparison_data.get("jd_structured", {})
    jd_responsibilities = [r.lower() for r in jd.get("responsibilities", []) if r]
    jd_keywords = [k.lower() for k in jd.get("keywords", []) if k]

    # Score based on semantic similarity if available
    sem = comparison_data.get("semantic_match", {})
    exp_similarity = sem.get("experience_similarity", 0.5)

    # Also check responsibility overlap
    all_responsibilities = []
    for exp in experience:
        all_responsibilities.extend(exp.get("responsibilities", []))

    resp_text = " ".join(all_responsibilities).lower()
    keyword_overlap = sum(1 for k in jd_keywords if k in resp_text)
    keyword_ratio = keyword_overlap / len(jd_keywords) if jd_keywords else 0.5

    # Combine semantic and keyword matching
    raw_score = (exp_similarity * 60 + keyword_ratio * 40) * 100

    return {
        "score": round(min(100, raw_score), 1),
        "weight": WEIGHTS["experience_alignment"],
        "weighted_score": round(min(100, raw_score) * WEIGHTS["experience_alignment"] / 100, 2),
        "details": f"{len(experience)} positions, semantic match: {exp_similarity:.2f}",
    }


def score_formatting(parsed_resume: dict) -> dict:
    """Score resume formatting and structure (deterministic)."""
    points = 0

    # Has summary (15 pts)
    if parsed_resume.get("personal_info", {}).get("summary"):
        points += 15

    # Has skills section with entries (15 pts)
    skills = parsed_resume.get("skills", {})
    total_skills = sum(len(v) for v in skills.values() if isinstance(v, list))
    if total_skills > 0:
        points += 15

    # Has experience with dates (15 pts)
    experience = parsed_resume.get("experience", [])
    if experience and any(e.get("start_date") for e in experience):
        points += 15

    # Has education (10 pts)
    if parsed_resume.get("education"):
        points += 10

    # Has projects (10 pts)
    if parsed_resume.get("projects"):
        points += 10

    # Uses bullet points in experience (10 pts)
    has_bullets = any(len(e.get("responsibilities", [])) > 1 for e in experience)
    if has_bullets:
        points += 10

    # Contact info completeness (10 pts)
    info = parsed_resume.get("personal_info", {})
    contact_fields = ["name", "email", "phone"]
    contact_complete = sum(1 for f in contact_fields if info.get(f))
    points += round(contact_complete / len(contact_fields) * 10)

    # Has links (5 pts)
    if info.get("linkedin") or info.get("github") or parsed_resume.get("links"):
        points += 5

    # Reasonable number of skills (not too few) (5 pts)
    if total_skills >= 5:
        points += 5

    raw_score = min(100, points)

    return {
        "score": raw_score,
        "weight": WEIGHTS["resume_formatting"],
        "weighted_score": round(raw_score * WEIGHTS["resume_formatting"] / 100, 2),
        "details": f"Structure score: {raw_score}/100",
    }


def score_education(parsed_resume: dict, comparison_data: dict) -> dict:
    """Score education fit (deterministic)."""
    education = parsed_resume.get("education", [])

    if not education:
        return {
            "score": 30,
            "weight": WEIGHTS["education_fit"],
            "weighted_score": round(30 * WEIGHTS["education_fit"] / 100, 2),
            "details": "No education section found",
        }

    jd = comparison_data.get("jd_structured", {})
    qualifications_list = jd.get("qualifications", []) or []
    qualifications = " ".join([q for q in qualifications_list if q]).lower()

    points = 0

    # Has degree (40 pts)
    has_degree = any(e.get("degree") for e in education)
    if has_degree:
        points += 40

    # Degree level match (30 pts)
    degrees = [(e.get("degree") or "").lower() for e in education]
    degree_text = " ".join(degrees)

    if "phd" in qualifications and "phd" in degree_text:
        points += 30
    elif "master" in qualifications and ("master" in degree_text or "ms" in degree_text):
        points += 30
    elif "bachelor" in qualifications and ("bachelor" in degree_text or "bs" in degree_text or "ba" in degree_text):
        points += 30
    elif has_degree:
        points += 15  # Has a degree but level doesn't match

    # Field relevance (20 pts)
    fields = [(e.get("field_of_study") or "").lower() for e in education]
    field_text = " ".join(fields)
    jd_keywords = [k.lower() for k in jd.get("keywords", [])]
    if any(k in field_text for k in jd_keywords):
        points += 20
    elif field_text:
        points += 10

    # GPA mentioned (10 pts)
    if any(e.get("gpa") for e in education):
        points += 10

    raw_score = min(100, points)

    return {
        "score": raw_score,
        "weight": WEIGHTS["education_fit"],
        "weighted_score": round(raw_score * WEIGHTS["education_fit"] / 100, 2),
        "details": f"{len(education)} education entries",
    }


def score_grammar(parsed_resume: dict) -> dict:
    """Score grammar and readability (heuristic-based)."""
    # Collect all text from resume
    texts = []

    for exp in parsed_resume.get("experience", []):
        texts.extend(exp.get("responsibilities", []))

    for proj in parsed_resume.get("projects", []):
        if proj.get("description"):
            texts.append(proj["description"])

    summary = parsed_resume.get("personal_info", {}).get("summary", "")
    if summary:
        texts.append(summary)

    if not texts:
        return {
            "score": 50,
            "weight": WEIGHTS["grammar_readability"],
            "weighted_score": round(50 * WEIGHTS["grammar_readability"] / 100, 2),
            "details": "Insufficient text to evaluate grammar",
        }

    full_text = " ".join(texts)
    points = 60  # Base score

    # Check for action verbs at start of bullets (good sign)
    action_verbs = ["developed", "built", "created", "implemented", "designed", "led",
                    "managed", "improved", "reduced", "increased", "achieved", "delivered",
                    "engineered", "architected", "optimized", "deployed", "automated",
                    "spearheaded", "launched", "established", "analyzed", "integrated"]

    bullets_with_action = sum(1 for t in texts if t.split()[0].lower().rstrip(",.:") in action_verbs) if texts else 0
    action_ratio = bullets_with_action / len(texts) if texts else 0
    points += round(action_ratio * 20)

    # Check sentence length variety (not all super long or super short)
    words_per_bullet = [len(t.split()) for t in texts]
    if words_per_bullet:
        avg_words = sum(words_per_bullet) / len(words_per_bullet)
        if 8 <= avg_words <= 25:
            points += 10
        elif 5 <= avg_words <= 30:
            points += 5

    # Check for quantified results (numbers in text)
    has_numbers = sum(1 for t in texts if any(c.isdigit() for c in t))
    number_ratio = has_numbers / len(texts) if texts else 0
    points += round(number_ratio * 10)

    raw_score = min(100, points)

    return {
        "score": raw_score,
        "weight": WEIGHTS["grammar_readability"],
        "weighted_score": round(raw_score * WEIGHTS["grammar_readability"] / 100, 2),
        "details": f"Action verbs: {action_ratio:.0%}, Quantified: {number_ratio:.0%}",
    }


def calculate_ats_score(parsed_resume: dict, comparison_data: dict, openai_api_key: str = None) -> dict:
    """
    Calculate the full weighted ATS score.

    Args:
        parsed_resume: Parsed resume JSON (from extract_entities)
        comparison_data: Comparison results (from compare_with_job_description)
        openai_api_key: OpenAI API key (for LLM-based scoring categories)

    Returns:
        {
            "success": bool,
            "data": {
                "ats_score": float,
                "score_band": str,
                "category_scores": { ... },
            },
            "error": str | None
        }
    """
    try:
        category_scores = {}

        # Deterministic categories
        category_scores["keyword_match"] = score_keyword_match(comparison_data)
        category_scores["skill_relevance"] = score_skill_relevance(parsed_resume, comparison_data)
        category_scores["project_quality"] = score_project_quality(parsed_resume, comparison_data)
        category_scores["experience_alignment"] = score_experience_alignment(parsed_resume, comparison_data)
        category_scores["resume_formatting"] = score_formatting(parsed_resume)
        category_scores["education_fit"] = score_education(parsed_resume, comparison_data)
        category_scores["grammar_readability"] = score_grammar(parsed_resume)

        # Calculate total weighted score
        total_score = sum(cat["weighted_score"] for cat in category_scores.values())
        total_score = round(min(100, max(0, total_score)), 1)

        return {
            "success": True,
            "data": {
                "ats_score": total_score,
                "score_band": get_score_band(total_score),
                "category_scores": category_scores,
            },
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Scoring failed: {e}",
        }


def main():
    """CLI usage for testing."""
    if len(sys.argv) < 3:
        print("Usage: python score_resume.py <parsed_resume.json> <comparison_data.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        parsed_resume = json.load(f)
    with open(sys.argv[2]) as f:
        comparison_data = json.load(f)

    result = calculate_ats_score(parsed_resume, comparison_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
