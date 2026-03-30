"""
extract_entities.py — Convert raw resume text into structured JSON via OpenAI.

Uses a single GPT call with a detailed prompt to extract all entities from resume text
and return a parsed_resume.json compliant object.

Usage:
    from tools.extract_entities import extract_entities
    parsed = extract_entities(raw_text, openai_api_key="...")
"""

import os
import sys
import json
from pathlib import Path


EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured data from the following resume text.

Return a JSON object with EXACTLY this structure. If a field cannot be determined, use null for strings and empty arrays for lists.

{
  "personal_info": {
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, State/Country",
    "linkedin": "LinkedIn URL",
    "github": "GitHub URL",
    "portfolio": "Portfolio/website URL",
    "summary": "Professional summary or objective (exact text from resume)"
  },
  "education": [
    {
      "institution": "University/college name",
      "degree": "Degree type (BS, MS, PhD, etc.)",
      "field_of_study": "Major/field",
      "gpa": "GPA if mentioned",
      "start_date": "Start year or date",
      "end_date": "End year or date",
      "honors": "Honors, dean's list, etc."
    }
  ],
  "skills": {
    "languages": ["Programming languages"],
    "frameworks": ["Frameworks and libraries"],
    "tools": ["Tools, platforms, software"],
    "databases": ["Database technologies"],
    "cloud_platforms": ["Cloud services"],
    "soft_skills": ["Soft skills if mentioned"],
    "other": ["Any skills that don't fit above categories"]
  },
  "experience": [
    {
      "company": "Company name",
      "role": "Job title",
      "location": "City, State/Country",
      "start_date": "Start date",
      "end_date": "End date or 'Present'",
      "is_current": false,
      "responsibilities": ["Each bullet point as a separate string"]
    }
  ],
  "projects": [
    {
      "title": "Project name",
      "description": "Brief description",
      "technologies": ["Tech used"],
      "impact": "Quantified impact if mentioned",
      "url": "Project URL if available",
      "github": "GitHub repo URL if available"
    }
  ],
  "certifications": [
    {
      "name": "Certification name",
      "issuer": "Issuing organization",
      "date": "Date obtained",
      "credential_id": "Credential ID if mentioned"
    }
  ],
  "links": [
    {
      "label": "Description of link",
      "url": "URL"
    }
  ],
  "confidence_notes": ["List any fields where you were uncertain about the extraction"]
}

RULES:
1. Extract ONLY what is explicitly in the resume text. Do NOT invent or assume information.
2. If a field is ambiguous, set it to null and add a note to confidence_notes.
3. Keep bullet points exactly as written — do not rephrase.
4. Classify skills accurately — a programming language goes in "languages", not "tools".
5. If the resume has no projects section, return an empty array for projects.
6. For dates, preserve the original format from the resume.
7. Return ONLY the JSON object, no markdown formatting or explanation.

RESUME TEXT:
"""


def extract_entities(raw_text: str, openai_api_key: str) -> dict:
    """
    Extract structured entities from resume text using OpenAI.

    Args:
        raw_text: Raw text extracted from resume
        openai_api_key: OpenAI API key

    Returns:
        {
            "success": bool,
            "data": dict (parsed resume) | None,
            "error": str | None,
            "tokens_used": int
        }
    """
    if not raw_text or len(raw_text.strip()) < 20:
        return {
            "success": False,
            "data": None,
            "error": "Resume text is too short to parse (< 20 characters)",
            "tokens_used": 0,
        }

    if not openai_api_key:
        return {
            "success": False,
            "data": None,
            "error": "OPENAI_API_KEY not provided",
            "tokens_used": 0,
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_api_key)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise resume parser. Output only valid JSON.",
                },
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + raw_text,
                },
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        # Parse the JSON response
        parsed = json.loads(content)

        return {
            "success": True,
            "data": parsed,
            "error": None,
            "tokens_used": tokens_used,
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "data": None,
            "error": f"Failed to parse OpenAI response as JSON: {e}",
            "tokens_used": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Entity extraction failed: {e}",
            "tokens_used": 0,
        }


def main():
    """CLI usage for testing."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    if len(sys.argv) < 2:
        print("Usage: python extract_entities.py <text_file_or_string>")
        sys.exit(1)

    input_arg = sys.argv[1]

    # Check if it's a file path
    if Path(input_arg).exists():
        raw_text = Path(input_arg).read_text(encoding="utf-8")
    else:
        raw_text = input_arg

    api_key = os.getenv("OPENAI_API_KEY")
    result = extract_entities(raw_text, api_key)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
