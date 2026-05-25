"""
AI Client - Gemini API
Provides interface to Google's Gemini models.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class AIClient:
    def __init__(self):
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"  ⚠️  Gemini init failed: {e}")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate content using Gemini."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                )
            )
            return response.text
        except Exception as e:
            print(f"  ⚠️  Gemini failed: {e}")
            raise


def get_client() -> AIClient:
    """Get or create the AI client singleton."""
    if not hasattr(get_client, "_client"):
        get_client._client = AIClient()
    return get_client._client