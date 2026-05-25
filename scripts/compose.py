"""
Video Composer — FFmpeg-based video assembly
Stitches stock clips to match voiceover duration, burns in subtitles, outputs 1080p MP4.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class VideoComposer:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or os.getenv("OUTPUT_DIR", "output"))
        self.clips_dir = self.output_dir / "clips"
        self.width = int(os.getenv("VIDEO_WIDTH", 1920))
        self.height = int(os.getenv("VIDEO_HEIGHT", 1080))
        self.fps = int(os.getenv("VIDEO_FPS", 30))

    def create_from_pipeline_output(self) -> str:
        """Main entry — builds the final video from pipeline outputs."""
        audio_path = self.output_dir / "voiceover.mp3"
        script_path = self.output_dir / "script.json"
        final_path = self.output_dir / "final_video.mp4"

        if not audio_path.exists():
            raise FileNotFoundError(f"Voiceover not found: {audio_path}")

        # Load script for subtitle text
        script_data = {}
        if script_path.exists():
            with open(script_path, encoding="utf-8") as f:
                script_data = json.load(f)

        # Get audio duration
        audio_duration = self._get_audio_duration(str(audio_path))
        print(f"  🎵  Audio duration: {audio_duration:.1f}s")

        # Collect clips
        clip_files = sorted(self.clips_dir.glob("clip_*.mp4"))
        if not clip_files:
            raise FileNotFoundError("No video clips found. Run visuals.py first.")

        print(f"  🎬  Composing {len(clip_files)} clips → {audio_duration:.1f}s video")

        # Build with FFmpeg
        final_path = self._compose_ffmpeg(
            clip_files, str(audio_path), audio_duration, str(final_path), script_data
        )

        size_mb = os.path.getsize(final_path) / 1_048_576
        print(f"  ✅  Final video: {final_path} ({size_mb:.1f} MB)")
        return final_path

    def _compose_ffmpeg(
        self, clip_files, audio_path: str, audio_duration: float,
        final_path: str, script_data: dict
    ) -> str:
        """Compose video using pure FFmpeg."""
        print("  🎬  Using FFmpeg renderer...")
        seg = audio_duration / len(clip_files)
        final_path = Path(final_path)

        # Write concat list and trim clips
        concat_list = self.output_dir / "concat.txt"
        trimmed_clips = []
        for i, cf in enumerate(clip_files):
            trimmed = self.output_dir / f"trim_{i:03d}.mp4"
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-stream_loop", "-1",
                    "-i", str(cf),
                    "-t", str(seg),
                    "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                           f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-an", str(trimmed)
                ], check=True, capture_output=True)
                trimmed_clips.append(trimmed)
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  Failed to process clip {cf.name}: {e.stderr.decode()[:200]}")

        if not trimmed_clips:
            raise RuntimeError("All clips failed to process.")

        # Write concat file
        with open(concat_list, "w") as f:
            for tc in trimmed_clips:
                f.write(f"file '{tc.absolute()}'\n")

        # Create video with audio
        temp_output = self.output_dir / "temp_video.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-shortest",
            str(temp_output)
        ], check=True, capture_output=True)

        # Burn subtitles
        srt_path = self._generate_srt(script_data, audio_duration)
        if srt_path and Path(srt_path).exists():
            final_output = str(temp_output)
            subprocess.run([
                "ffmpeg", "-y", "-i", str(temp_output),
                "-vf", (
                    f"subtitles={srt_path}:force_style='"
                    "FontName=Arial,FontSize=16,Bold=1,"
                    "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                    "Outline=2,Alignment=2,MarginV=50'"
                ),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "copy", str(final_path)
            ], check=True, capture_output=True)
            print("  ✅  Subtitles burned in")
        else:
            final_path = Path(temp_output)
            final_path.rename(self.output_dir / "final_video.mp4")

        # Cleanup
        for tc in trimmed_clips:
            try:
                tc.unlink()
            except Exception:
                pass
        try:
            (self.output_dir / "concat.txt").unlink()
            (self.output_dir / "temp_video.mp4").unlink()
        except Exception:
            pass

        return str(self.output_dir / "final_video.mp4")

    def _generate_srt(self, script_data: dict, total_duration: float) -> Optional[str]:
        """Generate a simple SRT file from the script text."""
        script_text = script_data.get("script", "")
        if not script_text:
            return None

        # Strip [VISUAL:] tags
        clean = re.sub(r"\[VISUAL:.*?\]", "", script_text, flags=re.IGNORECASE)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        if not sentences:
            return None

        srt_path = self.output_dir / "subtitles.srt"
        seg = total_duration / len(sentences)

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, sentence in enumerate(sentences):
                start = i * seg
                end = (i + 1) * seg
                f.write(f"{i+1}\n")
                f.write(f"{self._fmt_time(start)} --> {self._fmt_time(end)}\n")
                # Wrap long lines
                words = sentence.split()
                lines = []
                current = []
                for w in words:
                    current.append(w)
                    if len(" ".join(current)) > 42:
                        lines.append(" ".join(current[:-1]))
                        current = [w]
                if current:
                    lines.append(" ".join(current))
                f.write("\n".join(lines) + "\n\n")

        return str(srt_path)

    def _get_audio_duration(self, path: str) -> float:
        """Get audio duration using FFprobe."""
        result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ], capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 120.0

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """Format seconds as SRT timestamp HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    composer = VideoComposer()
    result = composer.create_from_pipeline_output()
    print(f"Video: {result}")