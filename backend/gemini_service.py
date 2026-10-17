
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Load .env from the backend folder
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from backend/.env"
    )

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.8-flash"


def ask_gemini(prompt):
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if not response.text or not response.text.strip():
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return response.text.strip()

        except Exception as e:
            error_message = str(e).upper()

            temporary_error = any(
                marker in error_message
                for marker in [
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "INTERNAL"
                ]
            )

            if temporary_error and attempt < max_attempts - 1:
                wait_seconds = 2 ** attempt
                print(
                    f"Gemini temporary error. "
                    f"Retrying in {wait_seconds} seconds..."
                )
                time.sleep(wait_seconds)
                continue

            raise
