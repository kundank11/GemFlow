import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    sys.exit(1)

def extract_text_from_response(response) -> str:
    if getattr(response, "text", None):
        return response.text
    candidates = getattr(response, "candidates", None)
    if candidates and len(candidates) > 0:
        content = getattr(candidates[0], "content", None)
        if content:
            parts = getattr(content, "parts", None)
            if parts and len(parts) > 0:
                part0 = parts[0]
                text = getattr(part0, "text", None)
                if text:
                    return text
    return None

def send_to_gemini(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
    except Exception as e:
        return f"[Error calling Gemini: {e}]"
    text = extract_text_from_response(response)
    if text:
        return text
    return "[No reply from Gemini or parsing failed]"
