from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("[-] No GOOGLE_API_KEY found")
    exit(1)

try:
    print(f"[*] Checking models for key: {api_key[:8]}...")
    client = genai.Client(api_key=api_key)
    models = client.models.list()
    print("[+] Available Models:")
    for m in models:
        print(f"  - {m.name}")
except Exception as e:
    print(f"[!] Error: {e}")
