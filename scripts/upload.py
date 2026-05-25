"""
YouTube Uploader — YouTube Data API v3 (OAuth 2.0)
Uploads the final video with full metadata from the SEO package.
"""

import os
import json
import pickle
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_OK = True
except ImportError:
    GOOGLE_OK = False


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), "..", "config", "client_secrets.json")
TOKEN_PICKLE = os.path.join(os.path.dirname(__file__), "..", "config", "token.pickle")


class YouTubeUploader:
    def __init__(self, output_dir: str = None):
        if not GOOGLE_OK:
            raise ImportError(
                "Google API libraries not installed.\n"
                "Run: pip install google-api-python-client google-auth-oauthlib"
            )
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
        self.youtube = self._authenticate()

    def _authenticate(self):
        """OAuth 2.0 authentication — opens browser on first run."""
        creds = None
        if os.path.exists(TOKEN_PICKLE):
            with open(TOKEN_PICKLE, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS):
                    raise FileNotFoundError(
                        f"Missing OAuth credentials: {CLIENT_SECRETS}\n"
                        "Download from Google Cloud Console → APIs & Services → "
                        "Credentials → OAuth 2.0 Client IDs → Desktop App"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PICKLE, "wb") as f:
                pickle.dump(creds, f)

        return build("youtube", "v3", credentials=creds)

    def upload_from_pipeline_output(self) -> dict:
        """Upload final_video.mp4 with metadata from metadata.json."""
        video_path = os.path.join(self.output_dir, "final_video.mp4")
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        thumbnail_path = os.path.join(self.output_dir, "thumbnail.jpg")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Load metadata
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

        # Pick best title
        titles = metadata.get("titles", ["Untitled Video"])
        rec_idx = metadata.get("recommended_title_index", 0)
        title = titles[rec_idx] if titles else "Untitled Video"

        description = metadata.get("description", "")
        tags = metadata.get("tags", [])
        privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")

        print(f"  📤  Uploading: {title}")
        print(f"  🔒  Privacy: {privacy}")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",  # People & Blogs (change as needed)
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        print("  ⏳  Uploading", end="", flush=True)
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"\r  ⏳  Uploading... {pct}%", end="", flush=True)
        print()

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"  ✅  Uploaded! {video_url}")

        # Upload thumbnail
        if os.path.exists(thumbnail_path):
            try:
                self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
                ).execute()
                print("  ✅  Thumbnail uploaded")
            except Exception as e:
                print(f"  ⚠️  Thumbnail upload failed: {e}")

        return {"id": video_id, "url": video_url}


if __name__ == "__main__":
    uploader = YouTubeUploader()
    result = uploader.upload_from_pipeline_output()
    print(result)
