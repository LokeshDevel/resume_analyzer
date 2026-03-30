"""
generate_feedback.py — Produce detailed improvement suggestions for a resume.

Uses OpenAI to generate:
  - Rewritten professional summary
  - Improved bullet points
  - Section-specific recommendations

Usage:
    from tools.generate_feedback import generate_feedback
    result = generate_feedback(parsed_resume, score_data, comparison_data, jd_text, openai_api_key)
"""

import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone


FEEDBACK_PROMPT = """You are an expert career coach and resume reviewer. Given the following resume analysis data, generate detailed improvement suggestions.

RESUME DATA:
{resume_json}

JOB DESCRIPTION:
{jd_text}

ATS SCORE: {ats_score}/100 ({score_band})
MATCHED KEYWORDS: {matched}
MISSING KEYWORDS: {missing}

CATEGORY SCORES:
{category_details}

Generate a JSON response with this EXACT structure:
{{
  "strengths": ["3-5 specific resume strengths"],
  "weaknesses": ["3-5 specific resume weaknesses"],
  "recommendations": [
    {{
      "section": "skills|experience|projects|education|summary|formatting",
      "priority": "high|medium|low",
      "suggestion": "Specific, actionable suggestion"
    }}
  ],
  "rewritten_summary": "A compelling 2-3 sentence professional summary tailored to the job description. If the resume has no summary, create one.",
  "improved_bullet_points": [
    {{
      "original": "Original bullet point text",
      "improved": "Improved version with quantified impact and action verbs",
      "section": "experience|projects"
    }}
  ]
}}

RULES:
1. Recommendations must be specific and actionable — not generic advice.
2. Prioritize recommendations that will have the most ATS impact.
3. For bullet point improvements, use the STAR method (Situation, Task, Action, Result).
4. Include quantified results in improved bullets even if you need to add placeholder metrics like "X%" that the user can fill in.
5. Address every missing keyword — suggest WHERE in the resume to add each one.
6. Limit improved_bullet_points to the 5 weakest bullets that would benefit most from rewriting.
7. Return ONLY the JSON object.
"""


def generate_feedback(
    parsed_resume: dict,
    score_data: dict,
    comparison_data: dict,
    jd_text: str,
    openai_api_key: str,
) -> dict:
    """
    Generate detailed feedback and improvement suggestions.

    Args:
        parsed_resume: Parsed resume JSON
        score_data: ATS score results from score_resume
        comparison_data: Comparison results from compare_with_job_description
        jd_text: Original job description text
        openai_api_key: OpenAI API key

    Returns:
        {
            "success": bool,
            "data": dict (final analysis),
            "error": str | None
        }
    """
    if not openai_api_key:
        return {
            "success": False,
            "data": None,
            "error": "OPENAI_API_KEY not provided",
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        # Build category details string
        category_details = ""
        for name, cat in score_data.get("category_scores", {}).items():
            category_details += f"  - {name.replace('_', ' ').title()}: {cat['score']}/100 (weight: {cat['weight']}%) — {cat.get('details', '')}\n"

        kw_match = comparison_data.get("keyword_match", {})

        prompt = FEEDBACK_PROMPT.format(
            resume_json=json.dumps(parsed_resume, indent=2)[:3000],  # Truncate to manage tokens
            jd_text=jd_text[:2000],
            ats_score=score_data.get("ats_score", 0),
            score_band=score_data.get("score_band", "Unknown"),
            matched=", ".join(kw_match.get("matched", [])),
            missing=", ".join(kw_match.get("missing", [])),
            category_details=category_details,
        )

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert career coach. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        feedback = json.loads(content)

        # Compose the final analysis object
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
            "rewritten_summary": feedback.get("rewritten_summary", None),
            "improved_bullet_points": feedback.get("improved_bullet_points", []),
            "parsed_resume": parsed_resume,
            "job_description": comparison_data.get("jd_structured", {}),
        }

        return {
            "success": True,
            "data": final_analysis,
            "error": None,
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to parse feedback JSON: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Feedback generation failed: {e}",
        }


def save_analysis(analysis: dict, output_dir: str = "outputs") -> str:
    """Save analysis result to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"analysis_{analysis.get('analysis_id', 'unknown')}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    return filepath


def main():
    """CLI usage for testing."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    if len(sys.argv) < 4:
        print("Usage: python generate_feedback.py <parsed_resume.json> <score_data.json> <comparison_data.json> [jd_text_file]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        parsed_resume = json.load(f)
    with open(sys.argv[2]) as f:
        score_data = json.load(f)
    with open(sys.argv[3]) as f:
        comparison_data = json.load(f)
    jd_text = Path(sys.argv[4]).read_text(encoding="utf-8") if len(sys.argv) > 4 else ""

    api_key = os.getenv("OPENAI_API_KEY")
    result = generate_feedback(parsed_resume, score_data, comparison_data, jd_text, api_key)

    if result["success"]:
        filepath = save_analysis(result["data"])
        print(f"Analysis saved to: {filepath}")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
