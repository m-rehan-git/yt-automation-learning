"""
PHASE 2 — Retention-Driven Script Writer
Uses Gemini/OpenRouter to write scripts with [VISUAL:] tags every 3-4 seconds.
"""

import os
import json
import re
from dotenv import load_dotenv
from ai_client import get_client

load_dotenv()

SCRIPTWRITING_SYSTEM_PROMPT = """
You are an elite faceless YouTube scriptwriter and viral content engineer.
You write retention-maximising scripts for faceless YouTube channels.

STRICT RULES — NEVER BREAK THESE:

## HOOK (0–5 seconds)
- Start INSTANTLY with an aggressive disruptive statement or high-stakes question.
- FORBIDDEN OPENERS: "Hey guys", "Welcome back", "In this video", "Today we",
  "Subscribe", any greeting whatsoever.
- Create an immediate curiosity gap that makes it IMPOSSIBLE to click away.

## PACING
- Max 10–12 words per sentence.
- Short. Punchy. Direct.
- No passive voice. No jargon. No filler.
- Write purely for auditory clarity — optimised for TTS engines.

## VISUAL TAGS
- Embed a [VISUAL: keyword phrase] tag every 3–4 seconds of spoken content.
- Keywords must be short, searchable, and map to free stock footage on Pexels.
- Format EXACTLY: [VISUAL: description of footage]
- Example: [VISUAL: ancient stone ruins aerial view]

## STRUCTURE
1. Hook (0–5 sec) — disruptive opening statement
2. Problem/Tension (5–30 sec) — build dread or curiosity
3. Story/Evidence (30–90 sec) — reveal with pacing and beats
4. Climax (90–120 sec) — the shocking truth or twist
5. Resolution/CTA (last 15 sec) — close with value + soft call to action

## OUTPUT FORMAT
Return ONLY raw JSON. No markdown. No backticks. No preamble. Exactly:
{
  "title": "working title under 60 chars",
  "hook": "the exact hook sentence",
  "script": "full script text with [VISUAL: ...] tags embedded inline",
  "visual_tags": ["tag1", "tag2", ...],
  "word_count": 250,
  "estimated_duration_seconds": 120,
  "suggested_tts_voice": "en-US-GuyNeural"
}
"""


class ScriptGenerator:
    def __init__(self, output_dir: str = None):
        self.ai = get_client()
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_script(self, topic: str, concept: dict = None) -> dict:
        """
        Generate a full retention-driven script.

        Args:
            topic: Plain text topic e.g. "The Lost City of Atlantis"
            concept: Optional niche blueprint concept dict for richer context
        """
        print(f"  ✍️  Writing script for: {topic}")

        context = ""
        if concept:
            context = f"""
Use this researched concept as your foundation:
- Core Pain Point: {concept.get('core_pain_point', '')}
- Curiosity Gap: {concept.get('curiosity_gap', '')}
- Semantic Triggers: {', '.join(concept.get('semantic_triggers', []))}
- Retention Hook Style: {concept.get('estimated_retention_hook', '')}
- Visual Theme: {concept.get('suggested_visual_theme', '')}
"""

        prompt = f"""
Write a 2–3 minute retention-driven YouTube script about:

TOPIC: {topic}
{context}

The script MUST:
- Open with an aggressive hook in the first 5 seconds (no greetings)
- Include [VISUAL: ...] tags every 3–4 seconds throughout
- Be 200–300 words total (2–3 minutes at normal TTS speed)
- Follow the 5-part structure: Hook → Tension → Evidence → Climax → Resolution
- End with a soft call-to-action (e.g. "Hit subscribe if that shocked you.")
"""

        data = None
        try:
            raw = self.ai.generate(SCRIPTWRITING_SYSTEM_PROMPT, prompt)
            raw = raw.replace("```json", "").replace("```", "").strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print("  ⚠️  JSON parse failed — attempting recovery")
                data = self._recover_script(raw, topic)
        except Exception as e:
            print(f"  ⚠️  AI error: {e}")
            data = self._fallback_script(topic)

        # Ensure visual_tags list is populated from script text
        data["visual_tags"] = self._extract_visual_tags(data.get("script", ""))
        data["word_count"] = len(data.get("script", "").split())

        # Save script
        script_path = os.path.join(self.output_dir, "script.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Save clean voiceover text (no [VISUAL:] tags)
        clean_text = self._strip_visual_tags(data.get("script", ""))
        voice_path = os.path.join(self.output_dir, "voiceover.txt")
        with open(voice_path, "w", encoding="utf-8") as f:
            f.write(clean_text)

        print(f"  ✅ Script saved ({data['word_count']} words, "
              f"{len(data['visual_tags'])} visual cues)")
        return data

    # ------------------------------------------------------------------
    def _extract_visual_tags(self, script_text: str) -> list:
        """Extract all [VISUAL: ...] keyword strings from the script."""
        pattern = r"\[VISUAL:\s*(.+?)\]"
        tags = re.findall(pattern, script_text, re.IGNORECASE)
        return [t.strip() for t in tags]

    def _strip_visual_tags(self, script_text: str) -> str:
        """Remove [VISUAL: ...] tags, leaving clean narration text."""
        clean = re.sub(r"\[VISUAL:.*?\]", "", script_text, flags=re.IGNORECASE)
        # Collapse extra whitespace / blank lines
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    def _recover_script(self, raw: str, topic: str) -> dict:
        """Fallback if AI returns non-JSON."""
        visual_tags = self._extract_visual_tags(raw)
        return {
            "title": topic[:60],
            "hook": raw.split("\n")[0][:120],
            "script": raw,
            "visual_tags": visual_tags,
            "word_count": len(raw.split()),
            "estimated_duration_seconds": 150,
            "suggested_tts_voice": os.getenv("TTS_VOICE", "en-US-GuyNeural"),
        }

    def _fallback_script(self, topic: str) -> dict:
        """Return a fallback script when API is unavailable."""
        script = f"""What if everything you knew about {topic} was wrong?

[VISUAL: mysterious ancient ruins]

For centuries, historians have told us one story. But I'm here to reveal the truth that's been hidden in plain sight.

[VISUAL: old historical documents parchment]

The evidence is scattered across ancient texts, cryptic symbols, and archaeological anomalies that mainstream academia refuses to address.

[VISUAL: ancient symbols close up]

In 1922, archaeologist Howard Carter discovered something in the tomb of Tutankhamun that was immediately classified. What was it?

[VISUAL: Egyptian tomb excavation]

Recent analysis of carbon dating has revealed inconsistencies that suggest our timeline might be completely wrong.

[VISUAL: carbon dating equipment]

The truth is out there. And it's more shocking than you can imagine.

[VISUAL: night sky stars]

Hit subscribe if this blew your mind, and drop a comment with what mystery you want solved next."""
        visual_tags = self._extract_visual_tags(script)
        return {
            "title": f"The Truth About {topic[:40]}",
            "hook": f"What if everything you knew about {topic} was wrong?",
            "script": script,
            "visual_tags": visual_tags,
            "word_count": len(script.split()),
            "estimated_duration_seconds": 150,
            "suggested_tts_voice": os.getenv("TTS_VOICE", "en-US-GuyNeural"),
        }


if __name__ == "__main__":
    gen = ScriptGenerator()
    result = gen.generate_script("The Disappearance of the Roanoke Colony")
    print(json.dumps(result, indent=2))