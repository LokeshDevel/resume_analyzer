"""
gemini_client.py — Shared Gemini API client with retry/backoff for rate limits.
"""

import time
import json
import google.generativeai as genai


def configure(api_key: str):
    genai.configure(api_key=api_key)


def generate_json(prompt: str, api_key: str, model: str = "gemini-2.0-flash", retries: int = 3) -> dict:
    """
    Call Gemini for JSON output with automatic retry on 429 rate limit errors.
    Returns parsed dict or raises exception.
    """
    configure(api_key)
    m = genai.GenerativeModel(
        model_name=model,
        generation_config={"response_mime_type": "application/json", "temperature": 0.1},
    )

    last_error = None
    wait = 10  # start with 10s backoff

    for attempt in range(retries):
        try:
            response = m.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                # Extract retry-after if present
                import re
                match = re.search(r"retry.*?(\d+\.?\d*)\s*s", err_str, re.IGNORECASE)
                delay = float(match.group(1)) + 2 if match else wait
                delay = min(delay, 60)  # cap at 60s
                print(f"  [Gemini] Rate limited. Retrying in {delay:.0f}s... (attempt {attempt+1}/{retries})")
                time.sleep(delay)
                wait *= 2
                last_error = e
            else:
                raise  # non-rate-limit error — fail immediately

    raise last_error


def embed(text: str, api_key: str, retries: int = 3) -> list:
    """Get embedding with retry on rate limit."""
    configure(api_key)

    last_error = None
    wait = 10

    for attempt in range(retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text[:8000],
                task_type="SEMANTIC_SIMILARITY",
            )
            return result["embedding"]
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                import re
                match = re.search(r"retry.*?(\d+\.?\d*)\s*s", err_str, re.IGNORECASE)
                delay = float(match.group(1)) + 2 if match else wait
                delay = min(delay, 60)
                print(f"  [Gemini Embed] Rate limited. Retrying in {delay:.0f}s... (attempt {attempt+1}/{retries})")
                time.sleep(delay)
                wait *= 2
                last_error = e
            else:
                raise

    raise last_error
