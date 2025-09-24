# services/gemini_client.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure .env is loaded even if this module is imported first
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing. Put it in .env and restart the app.")

genai.configure(api_key=API_KEY)

DEFAULT_MODEL = "gemini-1.5-flash"   # or "gemini-1.5-flash" for cheaper/faster

def ask_gemini(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Send a simple prompt to Gemini and return plain text.
    """
    try:
        m = genai.GenerativeModel(model_name=model)
        resp = m.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        # Return a short error; upstream can format it
        return f"[Gemini error: {e}]"
