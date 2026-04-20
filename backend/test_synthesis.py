import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add current dir to path to import orchestrator
sys.path.append(os.getcwd())
from orchestrator import Orchestrator, GeminiProvider
import google.generativeai as legacy_genai

load_dotenv()

def list_all_available_models():
    print(f"\n{'='*50}")
    print("LISTING ALL AVAILABLE MODELS (via LEGACY SDK)")
    print(f"{'='*50}")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY not found.")
        return
    
    try:
        legacy_genai.configure(api_key=api_key)
        models = legacy_genai.list_models()
        count = 0
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"[+] {m.name} (v1/v1beta)")
                print(f"    Description: {m.description}")
                count += 1
        if count == 0:
            print("[!] No models with generateContent support found.")
    except Exception as e:
        print(f"[ERROR] Failed to list models: {e}")

def debug_gemini_synthesis(model_id="gemini-1.5-pro"):
    print(f"\n{'='*50}")
    print(f"DEBUGGING GEMINI SYNTHESIS (Model: {model_id})")
    print(f"{'='*50}")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY not found in environment.")
        return

    # Initialize Provider directly to test it
    provider = GeminiProvider(api_key, model=model_id)
    
    test_prompt = "Write a simple 'Hello World' function in Python. No explanations, code only."
    test_system = "You are a helpful coding assistant."
    
    print(f"[*] Sending test request to {model_id}...")
    try:
        # We call complete directly
        response, usage = provider.complete(test_prompt, system=test_system)
        
        if not response:
            print("[FAIL] Received EMPTY response from Gemini.")
        elif response.startswith("[Gemini Error"):
            print(f"[FAIL] Provider returned error string: {response}")
        else:
            print("[SUCCESS] Gemini responded successfully!")
            print("-" * 20)
            print(response)
            print("-" * 20)
            print(f"Usage: {usage}")
            
    except Exception as e:
        import traceback
        print(f"[FAIL] Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # First, list what's actually available
    list_all_available_models()
    
    # Test common IDs found in the list
    models_to_test = [
        "gemini-2.0-flash",
        "gemini-pro-latest",
        "gemini-flash-latest",
        "gemini-2.0-flash-lite-001"
    ]
    
    for m in models_to_test:
        debug_gemini_synthesis(m)
        print("\n" + "."*50 + "\n")
