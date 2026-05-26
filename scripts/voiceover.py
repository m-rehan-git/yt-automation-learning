"""
TTS Voiceover Generator — Microsoft Edge-TTS with pyttsx3 fallback
Converts narration text to MP3 audio with expressive SSML markup.

FIX: Plain text → SSML with pauses, emphasis, and prosody variation,
     making the voice sound far less robotic/monotone.
"""

import os
import re
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

USE_PYTTX3 = os.getenv("USE_PYTTX3", "false").lower() == "true"


# ─────────────────────────────────────────────
#  SSML builder  (FIX for monotone voice)
# ─────────────────────────────────────────────

def _text_to_ssml(text: str, voice: str) -> str:
    """
    Convert plain narration text to SSML that adds:
      • Natural pauses after sentences and at commas
      • Mild pitch/rate variation so the voice rises and falls
      • Soft emphasis on question sentences
      • A brief breath-pause before new paragraphs

    Edge-TTS accepts full SSML when you pass it via the Communicate class.
    """
    # Split into paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    ssml_parts = [
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">',
        f'<voice name="{voice}">',
        # Global: slight expressiveness boost
        '<mstts:express-as style="newscast-casual" styledegree="1.5">',
    ]

    for p_idx, paragraph in enumerate(paragraphs):
        if p_idx > 0:
            # Paragraph break — 600 ms pause + small pitch drop to signal new topic
            ssml_parts.append('<break time="600ms"/>')

        # Split paragraph into sentences
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        for s_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Detect sentence type for prosody tuning
            is_question   = sentence.endswith("?")
            is_exclamation = sentence.endswith("!")
            is_last_in_para = (s_idx == len(sentences) - 1)

            # Vary rate slightly: questions slightly slower, exclamations slightly faster
            if is_question:
                rate, pitch = "95%", "+5%"
            elif is_exclamation:
                rate, pitch = "105%", "+8%"
            elif is_last_in_para:
                # Trailing sentences slow down a little → natural paragraph cadence
                rate, pitch = "93%", "-3%"
            else:
                rate, pitch = "100%", "0%"

            # Add inline comma pauses for longer sentences
            processed = re.sub(r',\s+', ', <break time="200ms"/> ', sentence)
            # Em-dash pause
            processed = re.sub(r'\s*—\s*', ' <break time="300ms"/> ', processed)
            # Colon pause
            processed = re.sub(r':\s+', ': <break time="250ms"/> ', processed)

            # Wrap in prosody
            ssml_parts.append(
                f'<prosody rate="{rate}" pitch="{pitch}">{processed}</prosody>'
            )

            # Post-sentence pause
            if is_question or is_exclamation:
                ssml_parts.append('<break time="400ms"/>')
            elif is_last_in_para:
                ssml_parts.append('<break time="350ms"/>')
            else:
                ssml_parts.append('<break time="200ms"/>')

    ssml_parts += ['</mstts:express-as>', '</voice>', '</speak>']
    return "\n".join(ssml_parts)


# ─────────────────────────────────────────────
#  TTS generators
# ─────────────────────────────────────────────

async def generate_voiceover(text: str, voice: str, output_path: str) -> str:
    """Generate MP3 voiceover from text using Edge-TTS with SSML."""
    import edge_tts

    ssml = _text_to_ssml(text, voice)

    # edge_tts.Communicate accepts raw SSML when the string starts with <speak>
    communicate = edge_tts.Communicate(ssml, voice)
    await communicate.save(output_path)
    return output_path


def generate_voiceover_pyttsx3(text: str, output_path: str) -> str:
    """Generate WAV voiceover using pyttsx3 (offline fallback, no SSML)."""
    import pyttsx3
    engine = pyttsx3.init()

    voices = engine.getProperty("voices")
    for v in voices:
        if "english" in v.name.lower() or "en-us" in v.id.lower():
            engine.setProperty("voice", v.id)
            break

    # pyttsx3 can't do SSML — at least slow it down a bit for clarity
    engine.setProperty("rate", 175)
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path


def _extract_clean_text(script_json_path: str) -> str:
    """Extract clean text without [VISUAL:] tags from script.json."""
    with open(script_json_path, encoding="utf-8") as f:
        data = json.load(f)
    script = data.get("script", "")
    clean = re.sub(r"\[VISUAL:.*?\]", "", script, flags=re.IGNORECASE)
    return re.sub(r"\n{3,}", "\n\n", clean).strip()


async def generate_from_script_file(
    script_path: str = None,
    voice: str = None,
    output_path: str = None,
    output_dir: str = None,
) -> str:
    """
    Read voiceover.txt (clean script) and generate audio.
    Returns path to the generated MP3.
    """
    output_dir = Path(output_dir or os.getenv("OUTPUT_DIR", "output"))

    if script_path is None:
        script_path = output_dir / "voiceover.txt"
    else:
        script_path = Path(script_path)
    if output_path is None:
        output_path = output_dir / "voiceover.mp3"
    else:
        output_path = Path(output_path)

    # Resolve voice
    if voice is None:
        script_json = output_dir / "script.json"
        if script_json.exists():
            with open(script_json, encoding="utf-8") as f:
                data = json.load(f)
                voice = data.get(
                    "suggested_tts_voice",
                    os.getenv("TTS_VOICE", "en-US-GuyNeural")
                )
        else:
            voice = os.getenv("TTS_VOICE", "en-US-GuyNeural")

    # Read text
    if script_path.exists():
        with open(script_path, encoding="utf-8") as f:
            text = f.read().strip()
    else:
        script_json = output_dir / "script.json"
        if script_json.exists():
            text = _extract_clean_text(str(script_json))
        else:
            raise FileNotFoundError(
                f"No script file found. Tried: {script_path}, {script_json}"
            )

    if not text:
        raise ValueError("Script text is empty")

    print(f"  🎙️  Generating TTS with voice: {voice}")
    print(f"  📝  Text length: {len(text)} characters")
    print(f"  🎭  SSML expressiveness: enabled")

    try:
        if USE_PYTTX3:
            raise Exception("Forced pyttsx3")
        await generate_voiceover(text, voice, str(output_path))
    except Exception as e:
        print(f"  ⚠️  Edge-TTS failed: {e}")
        print("  🔄  Trying offline pyttsx3...")
        wav_path = str(output_path).replace(".mp3", ".wav")
        generate_voiceover_pyttsx3(text, wav_path)
        if os.path.exists(wav_path):
            os.replace(wav_path, str(output_path))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅  Audio saved ({size_kb:.0f} KB): {output_path}")
    return str(output_path)


def generate_voiceover_sync(
    script_path: str = None,
    voice: str = None,
    output_path: str = None,
    output_dir: str = None,
) -> str:
    """Synchronous wrapper for generate_from_script_file."""
    return asyncio.run(generate_from_script_file(script_path, voice, output_path, output_dir))


def list_voices():
    """Print all available Edge-TTS voices (for reference)."""
    async def _list():
        import edge_tts
        voices = await edge_tts.list_voices()
        en_voices = [v for v in voices if v["Locale"].startswith("en-")]
        for v in en_voices:
            print(f"  {v['ShortName']:35s} | {v['Gender']:6s} | {v['Locale']}")
    asyncio.run(_list())


# ─────────────────────────────────────────────
#  Recommended expressive voices  (reference)
# ─────────────────────────────────────────────
EXPRESSIVE_VOICES = {
    # These Edge-TTS voices support mstts:express-as styles
    "en-US-GuyNeural":       "Male   – general, supports newscast/chat",
    "en-US-JennyNeural":     "Female – general, many styles",
    "en-US-AriaNeural":      "Female – very expressive, many styles",
    "en-US-DavisNeural":     "Male   – casual/chat friendly",
    "en-GB-RyanNeural":      "Male   – British, natural prosody",
    "en-AU-WilliamNeural":   "Male   – Australian accent",
}


if __name__ == "__main__":
    asyncio.run(generate_from_script_file())