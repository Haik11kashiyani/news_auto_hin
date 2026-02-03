import google.generativeai as genai
import os
import sys

# Get API key from env
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found or empty.")
    sys.exit(1)

try:
    genai.configure(api_key=api_key)
    print("📋 Listing available models...")
    models = genai.list_models()
    
    found_any = False
    print(f"{'Name':<30} | {'Methods'}")
    print("-" * 50)
    
    for m in models:
        methods = ", ".join(m.supported_generation_methods)
        print(f"{m.name:<30} | {methods}")
        if 'generateContent' in m.supported_generation_methods:
            found_any = True
            
    if not found_any:
        print("\n❌ No models found supporting 'generateContent'.")
    else:
        print("\n✅ Found compatible models.")

except Exception as e:
    print(f"❌ Error listing models: {e}")
    sys.exit(1)
