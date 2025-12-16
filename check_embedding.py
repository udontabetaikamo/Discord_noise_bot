
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("Listing embedding models...")
for m in genai.list_models():
    if 'embedContent' in m.supported_generation_methods:
        print(m.name)
