import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available models:\n")
for model in client.models.list():
    print(f"- {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"  Supports: {model.supported_generation_methods}")
    print()