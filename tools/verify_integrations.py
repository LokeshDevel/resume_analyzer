"""
verify_integrations.py — Pre-flight check for all external dependencies.

Run this before anything else to confirm OpenAI, OCR.Space, and MongoDB are reachable.

Usage:
    python tools/verify_integrations.py
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def check_env_vars():
    """Verify all required environment variables are set."""
    required = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OCR_SPACE_API_KEY": os.getenv("OCR_SPACE_API_KEY"),
        "MONGODB_URI": os.getenv("MONGODB_URI"),
    }
    optional = {
        "MONGODB_DB_NAME": os.getenv("MONGODB_DB_NAME", "resume_analyzer"),
        "MONGODB_COLLECTION": os.getenv("MONGODB_COLLECTION", "analyses"),
    }

    print("\n🔑  Environment Variables")
    print("=" * 50)

    all_set = True
    for key, val in required.items():
        if val and val not in ("", "your_openai_key_here", "your_ocr_space_key_here",
                               "mongodb+srv://username:password@cluster.mongodb.net/"):
            print(f"  ✅  {key}: {'*' * 8}...{val[-4:]}")
        else:
            print(f"  ❌  {key}: NOT SET or placeholder")
            all_set = False

    for key, val in optional.items():
        print(f"  ℹ️   {key}: {val}")

    return all_set


def check_openai():
    """Test OpenAI API connectivity."""
    print("\n🤖  OpenAI API")
    print("=" * 50)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_key_here":
        print("  ⏭️   Skipped — API key not configured")
        return False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Quick model list check (cheapest possible API call)
        models = client.models.list()
        model_ids = [m.id for m in models.data[:5]]
        print(f"  ✅  Connected successfully")
        print(f"  ℹ️   Available models (sample): {', '.join(model_ids)}")

        # Check if gpt-4.1 or gpt-4o is available
        all_ids = [m.id for m in models.data]
        for preferred in ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"]:
            if preferred in all_ids:
                print(f"  ✅  Preferred model available: {preferred}")
                break

        return True
    except ImportError:
        print("  ❌  openai package not installed. Run: pip install openai")
        return False
    except Exception as e:
        print(f"  ❌  Connection failed: {e}")
        return False


def check_ocr_space():
    """Test OCR.Space API connectivity."""
    print("\n📄  OCR.Space API")
    print("=" * 50)

    api_key = os.getenv("OCR_SPACE_API_KEY")
    if not api_key or api_key == "your_ocr_space_key_here":
        print("  ⏭️   Skipped — API key not configured")
        return False

    try:
        import requests

        # Use a minimal test — just ping the API with a tiny image URL
        response = requests.post(
            "https://api.ocr.space/parse/imageurl",
            data={
                "apikey": api_key,
                "url": "https://via.placeholder.com/1x1.png",
                "language": "eng",
            },
            timeout=15,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("OCRExitCode") is not None:
                print(f"  ✅  Connected successfully")
                print(f"  ℹ️   Exit code: {result.get('OCRExitCode')}")
                return True
            elif "ErrorMessage" in result:
                # Sometimes a 1x1 image returns an error but the API is still reachable
                print(f"  ✅  API reachable (test image too small, but connection works)")
                return True
        else:
            print(f"  ❌  HTTP {response.status_code}: {response.text[:200]}")
            return False

    except ImportError:
        print("  ❌  requests package not installed. Run: pip install requests")
        return False
    except Exception as e:
        print(f"  ❌  Connection failed: {e}")
        return False


def check_mongodb():
    """Test MongoDB connectivity."""
    print("\n🍃  MongoDB")
    print("=" * 50)

    uri = os.getenv("MONGODB_URI")
    if not uri or "username:password" in uri:
        print("  ⏭️   Skipped — URI not configured")
        return False

    try:
        from pymongo import MongoClient

        db_name = os.getenv("MONGODB_DB_NAME", "resume_analyzer")
        collection_name = os.getenv("MONGODB_COLLECTION", "analyses")

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)

        # Force connection test
        server_info = client.server_info()
        print(f"  ✅  Connected successfully")
        print(f"  ℹ️   MongoDB version: {server_info.get('version', 'unknown')}")

        db = client[db_name]
        collections = db.list_collection_names()
        print(f"  ℹ️   Database: {db_name}")
        print(f"  ℹ️   Collections: {collections if collections else '(none yet — will be created on first write)'}")

        client.close()
        return True

    except ImportError:
        print("  ❌  pymongo package not installed. Run: pip install pymongo[srv]")
        return False
    except Exception as e:
        print(f"  ❌  Connection failed: {e}")
        return False


def check_python_deps():
    """Verify all required Python packages are installed."""
    print("\n📦  Python Dependencies")
    print("=" * 50)

    packages = {
        "flask": "Flask",
        "flask_cors": "Flask-CORS",
        "openai": "OpenAI SDK",
        "PyPDF2": "PyPDF2 (PDF parsing)",
        "docx": "python-docx (DOCX parsing)",
        "pymongo": "PyMongo (MongoDB)",
        "dotenv": "python-dotenv",
        "requests": "Requests (HTTP)",
        "numpy": "NumPy",
    }

    all_installed = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"  ✅  {name}")
        except ImportError:
            print(f"  ❌  {name} — not installed")
            all_installed = False

    return all_installed


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║     Resume Analyzer — Integration Verification   ║")
    print("╚══════════════════════════════════════════════════╝")

    results = {}
    results["env_vars"] = check_env_vars()
    results["python_deps"] = check_python_deps()
    results["openai"] = check_openai()
    results["ocr_space"] = check_ocr_space()
    results["mongodb"] = check_mongodb()

    # Summary
    print("\n" + "=" * 50)
    print("📊  VERIFICATION SUMMARY")
    print("=" * 50)

    all_pass = True
    for check, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon}  {check.replace('_', ' ').title()}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n🎉  All checks passed! Ready to build.")
    else:
        print("\n⚠️   Some checks failed. Fix the issues above before proceeding.")
        print("    Run 'pip install -r requirements.txt' to install missing packages.")
        print("    Copy .env.example to .env and fill in your API keys.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
