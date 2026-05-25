"""
PHASE 3 — SEO Metadata Generator
Generates 3 title options, keyword-dense description, 15 tags, and hashtags.
"""

import os
import json
from dotenv import load_dotenv
from ai_client import get_client

load_dotenv()

SEO_SYSTEM_PROMPT = """
You are an elite YouTube SEO strategist.
Your goal is to maximise Click-Through Rate (CTR) and search discoverability
for faceless YouTube channel videos.

Output ONLY raw JSON. No markdown fences. No preamble. Exact structure:
{
  "titles": [
    "Title option 1 (under 60 chars)",
    "Title option 2 (under 60 chars)",
    "Title option 3 (under 60 chars)"
  ],
  "description": "Full 3-paragraph description. First 2 lines must work as standalone hooks for mobile search previews. Paragraph 1: curiosity hook + video summary. Paragraph 2: key points covered + search keywords. Paragraph 3: CTA + related topic keywords.",
  "tags": [
    "tag1", "tag2", "tag3", "tag4", "tag5",
    "tag6", "tag7", "tag8", "tag9", "tag10",
    "tag11", "tag12", "tag13", "tag14", "tag15"
  ],
  "hashtags": ["#Hashtag1", "#Hashtag2", "#Hashtag3", "#Hashtag4", "#Hashtag5"],
  "recommended_title_index": 0
}

Title rules:
- Option 1: Question format (curiosity gap)
- Option 2: Number/list or "The Truth About..." format
- Option 3: Shock statement or "You Won't Believe..." format
- All under 60 characters
- Include primary keyword naturally

Tags: mix of exact keywords, broad niche terms, and long-tail phrases.
Hashtags: 3–5, all relevant and not too niche.
"""


class SEOGenerator:
    def __init__(self):
        self.ai = get_client()
        self.output_dir = os.getenv("OUTPUT_DIR", "output")

    def generate_metadata(self, script_data: dict) -> dict:
        """Generate full SEO metadata package from script data."""
        title = script_data.get("title", "Unknown Topic")
        script_text = script_data.get("script", "")
        hook = script_data.get("hook", "")
        niche = os.getenv("CHANNEL_NICHE", "")

        print(f"  🔍  Generating SEO metadata for: {title}")

        prompt = f"""
Generate a complete YouTube SEO metadata package for this video:

TITLE: {title}
HOOK: {hook}
NICHE: {niche}
SCRIPT EXCERPT: {script_text[:600]}...

Requirements:
- 3 high-CTR title variations (under 60 chars each)
- 3-paragraph keyword-dense description (first 2 lines = mobile hook)
- 15 targeted tags mixing exact, broad, and long-tail keywords
- 3–5 relevant viral hashtags
"""

        try:
            raw = self.ai.generate(SEO_SYSTEM_PROMPT, prompt)
            metadata = json.loads(raw.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"  ⚠️  AI error: {e}")
            metadata = self._fallback_metadata(title, niche)

        # Save metadata
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save human-readable publication package
        self._save_publication_package(metadata, script_data)

        print(f"  ✅  SEO metadata saved → metadata.json")
        return metadata

    def _save_publication_package(self, metadata: dict, script_data: dict):
        """Save a clean markdown file with everything needed to publish."""
        rec_idx = metadata.get("recommended_title_index", 0)
        titles = metadata.get("titles", [])
        best_title = titles[rec_idx] if titles else "Untitled"

        package_path = os.path.join(self.output_dir, "publication_package.md")
        with open(package_path, "w", encoding="utf-8") as f:
            f.write("# YouTube Publication Package\n\n")
            f.write(f"## ✅ Recommended Title\n{best_title}\n\n")
            f.write("## 📝 All Title Options\n")
            for i, t in enumerate(titles):
                marker = "⭐ " if i == rec_idx else "   "
                f.write(f"{marker}{i+1}. {t}\n")
            f.write("\n## 📄 Description\n")
            f.write(metadata.get("description", "") + "\n\n")
            f.write("## 🏷️ Tags\n")
            f.write(", ".join(metadata.get("tags", [])) + "\n\n")
            f.write("## # Hashtags\n")
            f.write(" ".join(metadata.get("hashtags", [])) + "\n\n")
            f.write("## 🎬 Script\n")
            f.write("```\n" + script_data.get("script", "") + "\n```\n")

        print(f"  📄  Publication package → publication_package.md")

    def _fallback_metadata(self, title: str, niche: str) -> dict:
        return {
            "titles": [
                f"The Shocking Truth About {title[:35]}",
                f"What They Never Told You: {title[:33]}",
                f"{title[:55]}",
            ],
            "description": (
                f"The truth about {title} will shock you. "
                f"In this video we reveal facts most people never discover.\n\n"
                f"We cover {title} in detail — including hidden history, "
                f"surprising evidence, and what experts really think about {niche}.\n\n"
                f"If you found this interesting, subscribe for more {niche} content "
                f"every week. Drop a comment with your thoughts below."
            ),
            "tags": [
                title.lower(), niche.lower(), "mystery", "history", "facts",
                "unknown history", "shocking facts", "hidden truth",
                "documentary", "educational", "top facts", "conspiracy",
                "ancient history", "unsolved mysteries", "mind blowing facts",
            ],
            "hashtags": ["#Mystery", "#History", "#Facts", "#Documentary", "#Shorts"],
            "recommended_title_index": 0,
        }


if __name__ == "__main__":
    gen = SEOGenerator()
    script_path = os.path.join(os.getenv("OUTPUT_DIR", "output"), "script.json")
    with open(script_path, encoding="utf-8") as f:
        script_data = json.load(f)
    metadata = gen.generate_metadata(script_data)
    print(json.dumps(metadata, indent=2))