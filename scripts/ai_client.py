"""
AI Client - Unified interface for Gemini and OpenRouter
Provides fallback between providers when one is unavailable.
"""

import os
import json
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free models on OpenRouter (as of 2024)
FREE_MODELS = [
    "google/gemini-flash-1.5",  # Same model family as Gemini 2.0 Flash
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "microsoft/phi-3-mini-4k-instruct:free",
    "google/gemma-2-9b-it:free",
]


class AIClient:
    def __init__(self):
        self.gemini_client = None
        self.openrouter_client = None

        # Initialize Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_client = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                )
            except Exception as e:
                print(f"  ⚠️  Gemini init failed: {e}")

        # Initialize OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            try:
                self.openrouter_client = OpenAI(
                    api_key=openrouter_key,
                    base_url=OPENROUTER_BASE_URL,
                )
            except Exception as e:
                print(f"  ⚠️  OpenRouter init failed: {e}")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate content using available providers with fallback."""

        # Try Gemini first
        if self.gemini_client:
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=system_prompt,
                )
                response = model.generate_content(user_prompt)
                return response.text
            except Exception as e:
                print(f"  ⚠️  Gemini failed: {e}")

        # Fallback to OpenRouter
        if self.openrouter_client:
            try:
                for model in FREE_MODELS:
                    try:
                        response = self.openrouter_client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=temperature,
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        print(f"  ⚠️  OpenRouter model {model} failed: {e}")
                        continue

                raise Exception("All OpenRouter models failed")
            except Exception as e:
                print(f"  ⚠️  OpenRouter failed: {e}")

        raise RuntimeError("No AI provider available")


def get_client() -> AIClient:
    """Get or create the AI client singleton."""
    if not hasattr(get_client, "_client"):
        get_client._client = AIClient()
    return get_client._client