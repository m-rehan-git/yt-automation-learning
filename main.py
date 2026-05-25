#!/usr/bin/env python3
"""
YouTube Automation Agent — Master Pipeline Orchestrator
Phases: Research → Script → TTS → Footage → Compose → SEO → Upload
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from researcher import NicheResearcher
from script_generator import ScriptGenerator
from visuals import VisualsFetcher
from thumbnails import ThumbnailGenerator
from compose import VideoComposer
from seo import SEOGenerator


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         YouTube Automation Agent  •  Powered by Gemini       ║
║         Phase 1: Research  →  Phase 2: Script  →  Phase 3: SEO ║
╚══════════════════════════════════════════════════════════════╝
"""


class Pipeline:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def run(
        self,
        topic: str = None,
        skip_research: bool = False,
        upload: bool = True,
    ) -> dict:
        print(BANNER)
        print(f"  ⏰  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        results = {"success": False, "stages": {}, "timestamp": datetime.now().isoformat()}

        try:
            # ── PHASE 1: Competitive Research ────────────────────────────
            self._header("PHASE 1", "COMPETITIVE RESEARCH & NICHE BLUEPRINT")
            concept = {}

            if skip_research or topic:
                # If topic given directly, skip research or do quick research
                niche = topic or os.getenv("CHANNEL_NICHE", "Mystery and History")
                print(f"  📌  Topic override: {niche}")
                if not skip_research:
                    researcher = NicheResearcher(output_dir=self.output_dir)
                    blueprint = researcher.research(niche)
                    concept = researcher.pick_top_concept(blueprint)
                    topic = concept.get("concept_title", niche)
                    self._save(blueprint, "blueprint.json")
                    results["stages"]["research"] = {
                        "success": True,
                        "concepts_generated": len(blueprint.get("niche_blueprint", [])),
                        "chosen_concept": topic,
                    }
                else:
                    results["stages"]["research"] = {"success": True, "skipped": True}
            else:
                niche = os.getenv("CHANNEL_NICHE", "Mystery and Ancient History")
                researcher = NicheResearcher(output_dir=self.output_dir)
                blueprint = researcher.research(niche)
                concept = researcher.pick_top_concept(blueprint)
                topic = concept.get("concept_title", niche)
                self._save(blueprint, "blueprint.json")
                print(f"  🎯  Top concept: {topic}")
                results["stages"]["research"] = {
                    "success": True,
                    "concepts_generated": len(blueprint.get("niche_blueprint", [])),
                    "chosen_concept": topic,
                }

            # ── PHASE 2: Script Generation ────────────────────────────────
            self._header("PHASE 2", "RETENTION-DRIVEN SCRIPTWRITING")
            script_gen = ScriptGenerator(output_dir=self.output_dir)
            script_data = script_gen.generate_script(topic, concept=concept)
            results["stages"]["script"] = {
                "success": True,
                "title": script_data.get("title"),
                "word_count": script_data.get("word_count"),
"visual_tags": len(script_data.get("visual_tags", [])),
            }

            # ── PHASE 2b: TTS Voiceover ───────────────────────────────────
            self._header("PHASE 2b", "TEXT-TO-SPEECH VOICEOVER")
            from voiceover import generate_voiceover_sync
            audio_path = generate_voiceover_sync(output_dir=self.output_dir)
            results["stages"]["voiceover"] = {"success": True, "audio_path": audio_path}

            # ── PHASE 2c: Stock Footage ───────────────────────────────────
            self._header("PHASE 2c", "STOCK FOOTAGE DOWNLOAD (PEXELS)")
            fetcher = VisualsFetcher(output_dir=self.output_dir)
            clips = fetcher.fetch_videos_for_script(script_data)
            results["stages"]["visuals"] = {"success": True, "clips": len(clips)}

            # ── PHASE 3a: SEO Metadata ────────────────────────────────────
            self._header("PHASE 3a", "SEO METADATA GENERATION")
            seo_gen = SEOGenerator(output_dir=self.output_dir)
            metadata = seo_gen.generate_metadata(script_data)
            results["stages"]["seo"] = {
                "success": True,
                "titles": metadata.get("titles", []),
            }

            # ── PHASE 3b: Thumbnail ───────────────────────────────────────
            self._header("PHASE 3b", "THUMBNAIL GENERATION")
            thumb_gen = ThumbnailGenerator(output_dir=self.output_dir)
            thumb_path = thumb_gen.create_from_script(script_data)
            results["stages"]["thumbnail"] = {"success": True, "path": thumb_path}

            # ── PHASE 3c: Video Composition ───────────────────────────────
            self._header("PHASE 3c", "VIDEO COMPOSITION (FFMPEG)")
            composer = VideoComposer(output_dir=self.output_dir)
            video_path = composer.create_from_pipeline_output()
            results["stages"]["compose"] = {"success": True, "video_path": video_path}

            # ── PHASE 3d: Upload (optional) ───────────────────────────────
            if upload:
                self._header("PHASE 3d", "YOUTUBE UPLOAD")
                try:
                    from upload import YouTubeUploader
                    uploader = YouTubeUploader(output_dir=self.output_dir)
                    upload_result = uploader.upload_from_pipeline_output()
                    results["stages"]["upload"] = {
                        "success": True,
                        "url": upload_result["url"],
                    }
                except FileNotFoundError as e:
                    print(f"  ⚠️  Upload skipped: {e}")
                    results["stages"]["upload"] = {"success": False, "skipped": True, "reason": str(e)}
                except Exception as e:
                    print(f"  ⚠️  Upload failed: {e}")
                    results["stages"]["upload"] = {"success": False, "error": str(e)}
            else:
                print("\n  ⏭️   Upload skipped (--no-upload flag)")
                results["stages"]["upload"] = {"success": True, "skipped": True}

            # ── SUMMARY ───────────────────────────────────────────────────
            results["success"] = True
            self._summary(results, video_path, metadata)

        except KeyboardInterrupt:
            print("\n\n  ⚠️  Interrupted by user")
            results["error"] = "Interrupted"
        except Exception as e:
            print(f"\n  ❌  Pipeline failed: {e}")
            results["error"] = str(e)
            import traceback; traceback.print_exc()

        # Save run results
        self._save(results, "pipeline_results.json")
        return results

    # ------------------------------------------------------------------
    def _header(self, phase: str, title: str):
        print(f"\n{'─'*62}")
        print(f"  🚀  {phase}: {title}")
        print(f"{'─'*62}")

    def _save(self, data: dict, filename: str):
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _summary(self, results: dict, video_path: str, metadata: dict):
        titles = metadata.get("titles", [])
        rec = metadata.get("recommended_title_index", 0)
        best_title = titles[rec] if titles else "Unknown"
        upload_url = results.get("stages", {}).get("upload", {}).get("url", "Not uploaded")

        print(f"\n{'═'*62}")
        print("  🎉  PIPELINE COMPLETE!")
        print(f"{'═'*62}")
        print(f"  📹  Video  : {video_path}")
        print(f"  🏷️  Title  : {best_title}")
        print(f"  🌐  URL    : {upload_url}")
        print(f"  ⏰  Done   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'═'*62}\n")
        print("  📄  Check output/ folder:")
        print("      • final_video.mp4          — ready to upload")
        print("      • thumbnail.jpg            — custom thumbnail")
        print("      • publication_package.md   — titles/description/tags")
        print("      • metadata.json            — SEO data")
        print("      • script.json              — full script with visuals")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Automation Agent — Full AI Pipeline"
    )
    parser.add_argument(
        "--topic", type=str,
        help="Video topic (skips niche research if provided)"
    )
    parser.add_argument(
        "--no-upload", action="store_true",
        help="Skip YouTube upload — generate video only"
    )
    parser.add_argument(
        "--skip-research", action="store_true",
        help="Skip Phase 1 research (use --topic directly)"
    )
    args = parser.parse_args()

    pipeline = Pipeline()
    results = pipeline.run(
        topic=args.topic,
        skip_research=args.skip_research,
        upload=not args.no_upload,
    )
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
