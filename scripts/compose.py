"""
Video Composer — FFmpeg + MoviePy
Stitches stock clips to match voiceover duration,
burns in subtitles, and outputs final 1080p MP4.
"""

import os
import json
import subprocess
import math
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ColorClip,
    )
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

# Force FFmpeg mode for compatibility
USE_FFMPEG_ONLY = os.getenv("USE_FFMPEG_ONLY", "true").lower() == "true"


class VideoComposer:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        self.clips_dir = os.path.join(self.output_dir, "clips")
        self.width = int(os.getenv("VIDEO_WIDTH", 1920))
        self.height = int(os.getenv("VIDEO_HEIGHT", 1080))
        self.fps = int(os.getenv("VIDEO_FPS", 30))

    def create_from_pipeline_output(self) -> str:
        """Main entry — builds the final video from pipeline outputs."""
        audio_path = os.path.join(self.output_dir, "voiceover.mp3")
        script_path = os.path.join(self.output_dir, "script.json")
        final_path = os.path.join(self.output_dir, "final_video.mp4")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Voiceover not found: {audio_path}")

        # Load script for subtitle text
        script_data = {}
        if os.path.exists(script_path):
            with open(script_path, encoding="utf-8") as f:
                script_data = json.load(f)

        # Get audio duration
        audio_duration = self._get_audio_duration(audio_path)
        print(f"  🎵  Audio duration: {audio_duration:.1f}s")

        # Collect clips
        clip_files = sorted(Path(self.clips_dir).glob("clip_*.mp4"))
        if not clip_files:
            raise FileNotFoundError("No video clips found. Run visuals.py first.")

        print(f"  🎬  Composing {len(clip_files)} clips → {audio_duration:.1f}s video")

        # Build with FFmpeg (more reliable)
        final_path = self._compose_ffmpeg(
            clip_files, audio_path, audio_duration, final_path
        )

        size_mb = os.path.getsize(final_path) / 1_048_576
        print(f"  ✅  Final video: {final_path} ({size_mb:.1f} MB)")
        return final_path

    # ------------------------------------------------------------------
    # MoviePy path (richer — subtitles, transitions)
    # ------------------------------------------------------------------
    def _compose_moviepy(self, clip_files, audio_path,
                         audio_duration, script_data, final_path) -> str:
        print("  🎬  Using MoviePy renderer...")

        audio = AudioFileClip(audio_path)
        n_clips = len(clip_files)
        seg_duration = audio_duration / n_clips

        processed = []
        for i, clip_file in enumerate(clip_files):
            try:
                clip = VideoFileClip(str(clip_file), audio=False)
                # Loop if clip is shorter than segment
                if clip.duration < seg_duration:
                    loops = math.ceil(seg_duration / clip.duration)
                    from moviepy.editor import concatenate_videoclips
                    clip = concatenate_videoclips([clip] * loops)
                clip = clip.subclip(0, seg_duration)
                clip = clip.resize((self.width, self.height))
                # Fade in/out
                clip = clip.fadein(0.5).fadeout(0.5)
                processed.append(clip)
            except Exception as e:
                print(f"  ⚠️  Skipping {clip_file.name}: {e}")

        if not processed:
            raise RuntimeError("All clips failed to load.")

        final_clip = concatenate_videoclips(processed, method="compose")
        final_clip = final_clip.set_audio(audio)
        final_clip = final_clip.subclip(0, min(audio_duration, final_clip.duration))

        final_clip.write_videofile(
            final_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",          # CPU-friendly
            ffmpeg_params=["-crf", "23"],
            logger=None,
        )

        # Cleanup
        for c in processed:
            c.close()
        audio.close()
        final_clip.close()

        # Burn subtitles via FFmpeg (separate step — more reliable)
        subtitle_path = self._generate_srt(script_data, audio_duration)
        if subtitle_path:
            final_path = self._burn_subtitles(final_path, subtitle_path)

        return final_path

    # ------------------------------------------------------------------
    # Pure FFmpeg fallback
    # ------------------------------------------------------------------
    def _compose_ffmpeg(self, clip_files, audio_path,
                        audio_duration, final_path) -> str:
        print("  🎬  Using FFmpeg renderer (MoviePy not available)...")
        seg = audio_duration / len(clip_files)

        # Write concat list
        concat_list = os.path.join(self.output_dir, "concat.txt")
        trimmed_clips = []
        for i, cf in enumerate(clip_files):
            trimmed = os.path.join(self.output_dir, f"trim_{i:03d}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-stream_loop", "-1",
                "-i", str(cf),
                "-t", str(seg),
                "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                       f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-an", trimmed
            ], check=True, capture_output=True)
            trimmed_clips.append(trimmed)

        with open(concat_list, "w") as f:
            for tc in trimmed_clips:
                f.write(f"file '{os.path.abspath(tc)}'\n")

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-shortest",
            final_path
        ], check=True, capture_output=True)

        # Cleanup trimmed
        for tc in trimmed_clips:
            try:
                os.remove(tc)
            except Exception:
                pass
        return final_path

    # ------------------------------------------------------------------
    # Subtitle helpers
    # ------------------------------------------------------------------
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

        srt_path = os.path.join(self.output_dir, "subtitles.srt")
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

        return srt_path

    def _burn_subtitles(self, video_path: str, srt_path: str) -> str:
        """Burn subtitles into video using FFmpeg."""
        burned_path = video_path.replace(".mp4", "_subtitled.mp4")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path,
                "-vf", (
                    f"subtitles={srt_path}:force_style='"
                    "FontName=Arial,FontSize=14,Bold=1,"
                    "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                    "Outline=2,Alignment=2,MarginV=40'"
                ),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "copy", burned_path
            ], check=True, capture_output=True)
            os.replace(burned_path, video_path)
            print("  ✅  Subtitles burned in")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Subtitle burn failed (continuing without): {e}")
        return video_path

    @staticmethod
    def _get_audio_duration(path: str) -> float:
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
