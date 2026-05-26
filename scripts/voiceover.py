"""
TTS Voiceover Generator — Microsoft Edge-TTS
Converts narration text to MP3 audio.

Tunable via .env:
  TTS_VOICE   = en-US-GuyNeural   (any edge-tts voice)
  TTS_RATE    = +5%               (speaking rate offset, e.g. +10%, -5%)
  TTS_PITCH   = +2Hz              (pitch offset in Hz, e.g. +10Hz, -5Hz)
  TTS_VOLUME  = +0%               (volume offset)

NOTE: edge_tts.Communicate() does NOT support SSML — it HTML-escapes all input.
      Use the rate/pitch/volume constructor parameters for prosody control instead.
"""

import os
import re
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


async def generate_voiceover(text: str, voice: str, output_path: str) -> str:
    """Generate MP3 voiceover from plain text using Edge-TTS."""
    import edge_tts

    # Delete existing file first — on Windows a leftover file causes PermissionError
    try:
        os.remove(str(output_path))
    except OSError:
        pass

    rate   = os.getenv("TTS_RATE",   "+5%")
    pitch  = os.getenv("TTS_PITCH",  "+2Hz")
    volume = os.getenv("TTS_VOLUME", "+0%")

    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await communicate.save(str(output_path))
    return str(output_path)


def _extract_clean_text(script_json_path: str) -> str:
    """Extract clean narration text without [VISUAL:] tags from script.json."""
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
    Read voiceover.txt (or script.json) and generate audio.
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

    # Resolve voice: script.json suggestion → .env → default
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

    # Read narration text
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

    print(f"  🎙️  Voice: {voice}")
    print(f"  📝  Text: {len(text)} characters")

    await generate_voiceover(text, voice, str(output_path))

    size_kb = os.path.getsize(str(output_path)) / 1024
    print(f"  ✅  Audio saved ({size_kb:.0f} KB): {output_path}")
    return str(output_path)


def generate_voiceover_sync(
    script_path: str = None,
    voice: str = None,
    output_path: str = None,
    output_dir: str = None,
) -> str:
    """Synchronous wrapper for generate_from_script_file."""
    return asyncio.run(
        generate_from_script_file(script_path, voice, output_path, output_dir)
    )


def list_voices():
    """Print all available Edge-TTS voices."""
    async def _list():
        import edge_tts
        voices = await edge_tts.list_voices()
        en_voices = [v for v in voices if v["Locale"].startswith("en-")]
        for v in en_voices:
            print(f"  {v['ShortName']:35s} | {v['Gender']:6s} | {v['Locale']}")
    asyncio.run(_list())


if __name__ == "__main__":
    asyncio.run(generate_from_script_file())