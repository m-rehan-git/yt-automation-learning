"""
PHASE 1 — Competitive Research & Niche Blueprint
Uses Gemini/OpenRouter to reverse-engineer top content patterns
and produce 5 hyper-optimised video concepts.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from ai_client import get_client

load_dotenv()

SYSTEM_PROMPT = """
You are an elite YouTube content strategist and viral content engineer.
Your job is to analyse a niche or competitor content, then produce a
"Niche Blueprint" with 5 hyper-optimised video concepts designed to
outperform the existing competition.

For each concept output STRICT JSON with this exact structure:
{
  "niche_blueprint": [
    {
      "rank": 1,
      "concept_title": "...",
      "target_audience": "...",
      "core_pain_point": "...",
      "curiosity_gap": "...",
      "semantic_triggers": ["...", "...", "..."],
      "estimated_retention_hook": "...",
      "suggested_visual_theme": "..."
    }
  ]
}

Rules:
- Output ONLY the raw JSON. No markdown fences. No preamble.
- Concepts must exploit curiosity gaps, fear of missing out, or shocking facts.
- Titles must be under 60 characters.
- Each concept must be distinctly different from the others.
"""


class NicheResearcher:
    def __init__(self, output_dir: str = None):
        self.ai = get_client()
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")

    def research(self, niche: str, competitor_info: str = "") -> dict:
        """
        Research a niche and return a blueprint of 5 video concepts.

        Args:
            niche: e.g. "Mystery and Ancient History"
            competitor_info: Optional transcript/title snippets from competitors
        """
        print(f"  🔍 Researching niche: {niche}")

        user_prompt = f"""
Niche: {niche}

{"Competitor content samples:" + competitor_info if competitor_info else ""}

Analyse this niche and produce a Niche Blueprint with 5 viral video concepts
that will outperform existing content. Focus on:
1. Structural patterns of top-performing content in this niche
2. Exact semantic triggers and curiosity gaps
3. Audience pain points and desires
4. Timing and pacing of retention drops
"""

        try:
            raw = self.ai.generate(SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            print(f"  ⚠️  AI error: {e}")
            return self._fallback_blueprint(niche)

        # Strip accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw)
            concepts = data.get("niche_blueprint", [])
            print(f"  ✅ Generated {len(concepts)} video concepts")
            return data
        except json.JSONDecodeError:
            print("  ⚠️  JSON parse failed — returning raw text")
            return {"niche_blueprint": [], "raw": raw}

    def _fallback_blueprint(self, niche: str) -> dict:
        """Return a fallback blueprint when API is unavailable."""
        return {
            "niche_blueprint": [
                {
                    "rank": 1,
                    "concept_title": f"The Lost Secrets of {niche.split()[0]}",
                    "target_audience": "History enthusiasts, mystery lovers",
                    "core_pain_point": "Want to know the truth about ancient mysteries",
                    "curiosity_gap": "What they never taught you in school",
                    "semantic_triggers": ["shocking", "unexplained", "hidden"],
                    "estimated_retention_hook": "Aggressive hook with shocking fact",
                    "suggested_visual_theme": "Dark ancient ruins, mysterious atmosphere"
                },
                {
                    "rank": 2,
                    "concept_title": f"5 Unexplained Events in {niche.split()[0]}",
                    "target_audience": "Mystery seekers, documentary fans",
                    "core_pain_point": "Baffled by unexplained historical events",
                    "curiosity_gap": "These events still puzzle experts today",
                    "semantic_triggers": ["mystery", "unsolved", "shocking"],
                    "estimated_retention_hook": "Numbered list with suspense",
                    "suggested_visual_theme": "Dramatic reenactments, archival footage"
                }
            ]
        }

    def pick_top_concept(self, blueprint: dict) -> dict:
        """Return the rank-1 concept from the blueprint."""
        concepts = blueprint.get("niche_blueprint", [])
        if not concepts:
            return {}
        return sorted(concepts, key=lambda x: x.get("rank", 99))[0]


if __name__ == "__main__":
    researcher = NicheResearcher()
    niche = os.getenv("CHANNEL_NICHE", "Mystery and Ancient History")
    blueprint = researcher.research(niche)
    print(json.dumps(blueprint, indent=2))