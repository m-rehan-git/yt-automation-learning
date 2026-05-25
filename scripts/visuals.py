"""
Visual Assets Fetcher — Pexels API
Parses [VISUAL: ...] tags from script.json and downloads matching HD clips.
"""

import os
import json
import time
import re
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

PEXELS_BASE = "https://api.pexels.com/videos/search"
FALLBACK_QUERIES = [
    "cinematic landscape aerial",
    "dark atmospheric abstract",
    "nature time lapse 4k",
    "city lights night aerial",
    "universe stars space",
]


class VisualsFetcher:
    def __init__(self, output_dir: str = None):
        self.api_key = os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY not set in .env")
        self.output_dir = Path(output_dir or os.getenv("OUTPUT_DIR", "output"))
        self.clips_dir = self.output_dir / "clips"
        os.makedirs(self.clips_dir, exist_ok=True)
        self.headers = {"Authorization": self.api_key}
        self._cache = {}  # avoid duplicate downloads

    def fetch_videos_for_script(self, script_data: dict) -> list:
        """
        Download one video clip per [VISUAL:] tag in the script.
        Returns list of local file paths in tag order.
        """
        visual_tags = script_data.get("visual_tags", [])

        if not visual_tags:
            print("  ⚠️  No visual tags found — using fallback clips")
            visual_tags = FALLBACK_QUERIES[:5]

        print(f"  📹  Fetching {len(visual_tags)} clips from Pexels...")
        clip_paths = []

        for i, tag in enumerate(visual_tags):
            path = self._fetch_one(tag, index=i)
            if path:
                clip_paths.append(path)
            else:
                # Try fallback query
                fallback = FALLBACK_QUERIES[i % len(FALLBACK_QUERIES)]
                print(f"  ⚠️  Fallback for '{tag}' → '{fallback}'")
                path = self._fetch_one(fallback, index=i, is_fallback=True)
                if path:
                    clip_paths.append(path)

            time.sleep(0.3)  # Respect rate limit (200 req/hour)

        print(f"  ✅  Downloaded {len(clip_paths)} clips")
        return clip_paths

    def _fetch_one(self, query: str, index: int, is_fallback: bool = False) -> Optional[str]:
        """Search Pexels and download the best matching HD clip."""
        # Check cache
        if query in self._cache:
            return self._cache[query]

        filename = f"clip_{index:03d}.mp4"
        output_path = self.clips_dir / filename

        # Skip re-download if file exists
        if output_path.exists() and output_path.stat().st_size > 50_000:
            self._cache[query] = str(output_path)
            return str(output_path)

        try:
            params = {
                "query": query,
                "per_page": 5,
                "min_width": 1280,
                "min_duration": 5,
                "max_duration": 30,
            }
            resp = requests.get(PEXELS_BASE, headers=self.headers,
                                params=params, timeout=15)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])

            if not videos:
                print(f"  ⚠️  No results for: '{query}'")
                return None

            # Pick the best HD file
            video = videos[0]
            video_file = self._best_file(video.get("video_files", []))
            if not video_file:
                return None

            # Download
            dl = requests.get(video_file["link"], stream=True, timeout=60)
            dl.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in dl.iter_content(chunk_size=65536):
                    f.write(chunk)

            size_mb = output_path.stat().st_size / 1_048_576
            label = "fallback" if is_fallback else "tag"
            print(f"  ✅  [{label}] '{query}' → {filename} ({size_mb:.1f} MB)")
            self._cache[query] = str(output_path)
            return str(output_path)

        except requests.RequestException as e:
            print(f"  ❌  Pexels error for '{query}': {e}")
            return None

    @staticmethod
    def _best_file(files: list) -> Optional[dict]:
        """Select the best quality file ≤1080p."""
        ranked = [f for f in files if f.get("file_type") == "video/mp4"]
        # Prefer HD (1080p), fallback to lower
        for target_h in [1080, 720, 480]:
            for f in ranked:
                if f.get("height") == target_h:
                    return f
        return ranked[0] if ranked else None


if __name__ == "__main__":
    # Quick test
    fetcher = VisualsFetcher()
    script_path = os.path.join(os.getenv("OUTPUT_DIR", "output"), "script.json")
    with open(script_path) as f:
        script_data = json.load(f)
    clips = fetcher.fetch_videos_for_script(script_data)
    print(f"\nClips: {clips}")
