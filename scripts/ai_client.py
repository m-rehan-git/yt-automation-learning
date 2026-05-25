"""
AI Client - Gemini API
Provides interface to Google's Gemini models.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class AIClient:
    def __init__(self):
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(
                    model_name="gemini-1.5-flash-latest",
                )
            except Exception as e:
                print(f"  ⚠️  Gemini init failed: {e}")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate content using Gemini."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        try:
            response = self.client.generate_content(
                user_prompt,
                generation_config={"system_instruction": system_prompt}
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