"""
Thumbnail Generator — Pillow (100% free, no AI image gen required)
Creates bold, high-CTR thumbnails with title text overlay.
"""

import os
import json
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from dotenv import load_dotenv

load_dotenv()


class ThumbnailGenerator:
    W = 1280
    H = 720
    BG_COLOR = (25, 25, 50, 255)
    ACCENT_1 = (220, 30, 30, 255)
    ACCENT_2 = (255, 200, 0, 255)
    TEXT_COLOR = (255, 255, 255, 255)

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def create_from_script(self, script_data: dict) -> str:
        """Generate a thumbnail from script data. Returns path."""
        # Use recommended title from metadata if available
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        title = script_data.get("title", "Untitled")
        if os.path.exists(metadata_path):
            with open(metadata_path, encoding="utf-8") as f:
                meta = json.load(f)
            titles = meta.get("titles", [])
            idx = meta.get("recommended_title_index", 0)
            if titles:
                title = titles[idx]

        hook = script_data.get("hook", "")
        output_path = os.path.join(self.output_dir, "thumbnail.jpg")

        # Use first available clip as background, or solid color
        bg = self._load_background()
        img = bg.copy()

        # Dark overlay for text readability
        overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 140))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

        # Red accent stripe (left)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (12, self.H)], fill=self.ACCENT_1)

        # Title text (large, centered)
        self._draw_text_block(draw, title, y_center=320,
                              max_width=55, font_size=68,
                              color=self.TEXT_COLOR)

        # Hook subtext (smaller, below title)
        if hook:
            short_hook = hook[:80] + ("..." if len(hook) > 80 else "")
            self._draw_text_block(draw, short_hook, y_center=530,
                                  max_width=70, font_size=34,
                                  color=self.ACCENT_2)

        # Bottom accent bar
        draw.rectangle([(0, self.H - 8), (self.W, self.H)], fill=self.ACCENT_1)

        # Save
        final = img.convert("RGB")
        final.save(output_path, "JPEG", quality=95)
        print(f"  ✅  Thumbnail saved: {output_path}")
        return output_path

    def _load_background(self) -> Image.Image:
        """Try to use first video frame as background, else solid colour."""
        clips_dir = os.path.join(self.output_dir, "clips")
        clips = sorted(Path(clips_dir).glob("clip_*.mp4"))
        if clips:
            try:
                import subprocess, tempfile
                frame_path = os.path.join(self.output_dir, "thumb_frame.jpg")
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(clips[0]),
                    "-vframes", "1", "-q:v", "2", frame_path
                ], capture_output=True, check=True)
                bg = Image.open(frame_path).resize((self.W, self.H))
                # Darken + blur for text contrast
                bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
                bg = ImageEnhance.Brightness(bg).enhance(0.4)
                return bg
            except Exception:
                pass
        return Image.new("RGBA", (self.W, self.H), self.BG_COLOR)

    def _draw_text_block(self, draw: ImageDraw.Draw, text: str,
                         y_center: int, max_width: int,
                         font_size: int, color: tuple):
        """Draw centred, wrapped text with drop shadow."""
        font = self._get_font(font_size)
        lines = textwrap.wrap(text, width=max_width)
        line_height = font_size + 8
        total_height = len(lines) * line_height
        y = y_center - total_height // 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (self.W - text_w) // 2

            # Shadow
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200))
            # Main text
            draw.text((x, y), line, font=font, fill=color)
            y += line_height

    @staticmethod
    def _get_font(size: int) -> ImageFont.FreeTypeFont:
        """Try to load a bold system font, fallback to default."""
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()


if __name__ == "__main__":
    gen = ThumbnailGenerator()
    script_path = os.path.join(os.getenv("OUTPUT_DIR", "output"), "script.json")
    with open(script_path, encoding="utf-8") as f:
        script_data = json.load(f)
    gen.create_from_script(script_data)
