import os
from dotenv import load_dotenv
from google import genai
import httpx

load_dotenv()

def test_gemini():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return "MISSING KEY"
    client = genai.Client(api_key=api_key)
    try:
        # Try a variety of common IDs
        for m in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            try:
                client.models.generate_content(model=m, contents="hi")
                return f"OK ({m})"
            except Exception:
                continue
        return "ALL MODELS 404/FAILED"
    except Exception as e:
        return str(e)

def test_mistral():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key: return "MISSING KEY"
    try:
        resp = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "mistral-small-latest", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            timeout=5
        )
        if resp.status_code == 200:
            return "OK (mistral-small-latest)"
        return f"FAILED ({resp.status_code})"
    except Exception as e:
        return str(e)

print(f"--- PROVIDER DIAGNOSIS ---")
print(f"GEMINI:  {test_gemini()}")
print(f"MISTRAL: {test_mistral()}")
print(f"--------------------------")
