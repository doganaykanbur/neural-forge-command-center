from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash-latest",
    "models/gemini-1.5-flash",
]

for m in models_to_try:
    try:
        print(f"[*] Trying {m}...")
        res = client.models.generate_content(model=m, contents="hi")
        print(f"[+] SUCCESS with {m}: {res.text[:10]}...")
        break
    except Exception as e:
        print(f"[-] FAILED with {m}: {e}")
