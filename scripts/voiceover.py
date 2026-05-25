"""
TTS Voiceover Generator — Microsoft Edge-TTS with pyttsx3 fallback
Converts the clean narration text to MP3 audio.
"""

import os
import asyncio
import json
import edge_tts
import pyttsx3
from dotenv import load_dotenv

load_dotenv()

USE_PYTTX3 = os.getenv("USE_PYTTX3", "false").lower() == "true"


async def generate_voiceover(text: str, voice: str, output_path: str) -> str:
    """Generate MP3 voiceover from text using Edge-TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path


def generate_voiceover_pyttsx3(text: str, output_path: str) -> str:
    """Generate WAV voiceover using pyttsx3 (offline fallback)."""
    engine = pyttsx3.init()
    
    # Try to find a good voice
    voices = engine.getProperty('voices')
    for v in voices:
        if 'english' in v.name.lower() or 'en-us' in v.id.lower():
            engine.setProperty('voice', v.id)
            break
    
    engine.setProperty('rate', 200)
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path


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
    output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")

    # Resolve paths
    if script_path is None:
        script_path = os.path.join(output_dir, "voiceover.txt")
    if output_path is None:
        output_path = os.path.join(output_dir, "voiceover.mp3")

    # Get voice — check script.json first, then .env, then default
    if voice is None:
        script_json = os.path.join(output_dir, "script.json")
        if os.path.exists(script_json):
            with open(script_json, encoding="utf-8") as f:
                data = json.load(f)
                voice = data.get("suggested_tts_voice",
                                 os.getenv("TTS_VOICE", "en-US-GuyNeural"))
        else:
            voice = os.getenv("TTS_VOICE", "en-US-GuyNeural")

    # Read text
    with open(script_path, encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError(f"voiceover.txt is empty: {script_path}")

    print(f"  🎙️  Generating TTS with voice: {voice}")
    print(f"  📝  Text length: {len(text)} characters")

    # Try Edge-TTS first, fall back to pyttsx3
    try:
        if USE_PYTTX3:
            raise Exception("Forced pyttsx3")
        await generate_voiceover(text, voice, output_path)
    except Exception as e:
        print(f"  ⚠️  Edge-TTS failed: {e}")
        print("  🔄  Trying offline pyttsx3...")
        # pyttsx3 saves as WAV, convert to MP3 if needed
        wav_path = output_path.replace(".mp3", ".wav")
        generate_voiceover_pyttsx3(text, wav_path)
        # Rename to mp3 (ffmpeg can handle wav->mp3 conversion later)
        if os.path.exists(wav_path):
            os.replace(wav_path, output_path)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅  Audio saved ({size_kb:.0f} KB): {output_path}")
    return output_path


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
        voices = await edge_tts.list_voices()
        en_voices = [v for v in voices if v["Locale"].startswith("en-")]
        for v in en_voices:
            print(f"  {v['ShortName']:35s} | {v['Gender']:6s} | {v['Locale']}")
    asyncio.run(_list())


if __name__ == "__main__":
    asyncio.run(generate_from_script_file())