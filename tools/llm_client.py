"""
llm_client.py — Groq API client (OpenAI-compatible) with retry/backoff.
"""

import time
import json
from openai import OpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def generate_json(prompt: str, api_key: str, model: str = "llama-3.3-70b-versatile", retries: int = 3) -> dict:
    """
    Call Groq for JSON output with automatic retry on rate limit errors.
    Returns parsed dict or raises exception.
    """
    client = get_client(api_key)
    last_error = None
    wait = 5

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a precise data extraction assistant. Always respond with valid JSON only, no markdown formatting."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower():
                delay = min(wait, 30)
                print(f"  [Groq] Rate limited. Retrying in {delay}s... (attempt {attempt+1}/{retries})")
                time.sleep(delay)
                wait *= 2
                last_error = e
            else:
                raise

    raise last_error
