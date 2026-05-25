# 🎬 YouTube Automation Agent

**100% free** end-to-end faceless YouTube channel automation.  
Powered by Gemini 2.0 Flash · Edge-TTS · Pexels · FFmpeg

---

## ✨ What This Does

| Phase | What Happens |
|-------|-------------|
| **Phase 1** | Gemini researches your niche → produces 5 viral video concepts |
| **Phase 2** | Writes a retention-driven script with hook mechanics + `[VISUAL:]` tags |
| **Phase 2b** | Microsoft Edge-TTS converts script to professional voiceover |
| **Phase 2c** | Downloads matching HD stock footage from Pexels (one clip per visual cue) |
| **Phase 3a** | Generates 3 title options, SEO description, 15 tags, 5 hashtags |
| **Phase 3b** | Creates a bold custom thumbnail |
| **Phase 3c** | FFmpeg stitches clips + voiceover + burned-in subtitles → 1080p MP4 |
| **Phase 3d** | Auto-uploads to YouTube with full metadata (optional) |

---

## 🚀 Quick Start (5 minutes)

### Step 1 — Clone & install
```bash
git clone <your-repo-url>
cd youtube-automation-agent
pip install -r requirements.txt
```

### Step 2 — Install FFmpeg
```bash
# Windows (run as Administrator)
winget install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Add to PATH after installing
```

### Step 3 — Get your free API keys
- **Gemini**: https://aistudio.google.com → "Get API Key" (free, no credit card)
- **Pexels**: https://www.pexels.com/api/ → "Get Started" (free)

### Step 4 — Configure
```bash
cp .env.example .env
# Open .env and add your two API keys
```

### Step 5 — Run!
```bash
# Let AI choose the topic (recommended)
python main.py --no-upload

# Specify your own topic
python main.py --topic "The Lost City of Atlantis" --no-upload

# Full run WITH YouTube upload
python main.py --topic "Ancient Mysteries Explained"
```

---

## 📁 Output Files

After running, check the `output/` folder:

| File | Description |
|------|-------------|
| `final_video.mp4` | Ready-to-upload 1080p video with subtitles |
| `thumbnail.jpg` | Custom 1280×720 thumbnail |
| `publication_package.md` | Titles, description, tags — copy-paste ready |
| `metadata.json` | Full SEO data in JSON |
| `script.json` | Full script with visual cue tags |
| `blueprint.json` | 5 niche video concepts from Phase 1 |

---

## 🤖 Daily Automation (GitHub Actions — Free)

### Setup
1. Push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:

| Secret | Where to get it |
|--------|----------------|
| `GEMINI_API_KEY` | https://aistudio.google.com |
| `PEXELS_API_KEY` | https://www.pexels.com/api/ |
| `CHANNEL_NICHE` | e.g. `Mystery and Ancient History` |
| `YOUTUBE_CLIENT_SECRETS` | Content of `config/client_secrets.json` |
| `YOUTUBE_TOKEN_PICKLE` | `base64 config/token.pickle` (after first auth) |

### Schedule
Edit `.github/workflows/auto-video.yml`:
```yaml
- cron: '0 9 * * *'   # Every day 9AM UTC
- cron: '0 9 * * 1'   # Every Monday
- cron: '0 9 * * 1,4' # Mon + Thu
```

### Manual trigger
Go to **Actions → YouTube Automation Pipeline → Run workflow**

---

## 📺 YouTube Upload Setup (Optional)

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable **YouTube Data API v3**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop app** → Download JSON
6. Save as `config/client_secrets.json`
7. Run once locally: `python scripts/upload.py` — browser opens for auth
8. Token saved to `config/token.pickle` — reused forever

---

## 💰 Cost Breakdown

| Component | Tool | Cost |
|-----------|------|------|
| AI Research + Script + SEO | Gemini 2.0 Flash | **$0** (free tier) |
| Text-to-Speech | Microsoft Edge-TTS | **$0** |
| Stock Footage | Pexels API | **$0** |
| Video Rendering | FFmpeg | **$0** |
| Thumbnail | Pillow | **$0** |
| YouTube Upload | YouTube Data API | **$0** |
| Daily Automation | GitHub Actions | **$0** (2000 min/month) |
| **Total** | | **$0/month** |

---

## ⚙️ Customisation

### Change niche
Edit `.env`:
```
CHANNEL_NICHE=Finance and Investing
```

### Change TTS voice
```
TTS_VOICE=en-GB-RyanNeural     # British male
TTS_VOICE=en-US-JennyNeural    # US female
TTS_VOICE=en-AU-WilliamNeural  # Australian male
```

### Change upload privacy
```
YOUTUBE_PRIVACY_STATUS=private    # Review before going public
YOUTUBE_PRIVACY_STATUS=unlisted   # Share link only
YOUTUBE_PRIVACY_STATUS=public     # Full public upload
```

---

## 🛠️ Troubleshooting

**`GEMINI_API_KEY not set`** → Check your `.env` file has no quotes around the key  
**`FFmpeg not found`** → Install FFmpeg and ensure it's in your PATH  
**`No clips downloaded`** → Check your Pexels API key in `.env`  
**`ModuleNotFoundError`** → Run `pip install -r requirements.txt`  
**`YouTube auth failed`** → Delete `config/token.pickle` and re-run upload.py  

---

## 📋 YouTube Community Guidelines Compliance

This tool creates **100% original content**:
- ✅ AI-generated scripts (not copied)
- ✅ Licensed stock footage (Pexels free license)
- ✅ Original TTS voiceover
- ✅ Original thumbnail
- ✅ No re-uploading of existing videos
- ✅ No artificially inflated metrics

> Always review generated content before uploading to ensure it meets  
> YouTube's policies for your specific niche.
