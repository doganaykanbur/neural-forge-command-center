from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("New SDK Client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize new SDK: {e}")
