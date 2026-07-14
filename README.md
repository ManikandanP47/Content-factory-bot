# Content Factory Bot

Local, mostly-free pipeline that turns a **topic** into a faceless **YouTube Short / Instagram Reel**:

1. Write a structured script (Ollama, with built-in fallback)
2. Synthesize **humane** narration (**Kokoro** when available, else free **edge-tts** neural voice)
3. Render a clean **9:16** motion video (**Remotion**, FFmpeg fallback)
4. Save artifacts to **Google Drive**
5. Upload to **YouTube Shorts** and **Instagram Reels**

## Quick start

```bash
cd ~/content-factory

# Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# System deps (macOS)
brew install ffmpeg espeak-ng

# Optional: local LLM for better scripts
brew install ollama
ollama pull llama3.2

# Optional: best free long-term voice (needs Python 3.10–3.12 + espeak-ng)
pip install 'kokoro>=0.9.4' torch

# Remotion (for polished video)
cd video && npm install && cd ..

# Produce one short
content-factory produce --topic "Why founders should protect deep work"

# Publish (after credentials below)
content-factory publish --job <job_id> --channels drive,youtube,instagram
```

Job files land in `output/<job_id>/` (`script.json`, voice/mixed audio, `props.json`, `final.mp4`, `job.json`).

## CLI

| Command | What it does |
|---------|----------------|
| `content-factory produce --topic "..."` | Script → voice → video |
| `content-factory produce --topic "..." --dry-run` | Script only |
| `content-factory produce --topic "..." --skip-video` | Stop after audio |
| `content-factory publish --job ID --channels drive,youtube` | Upload |
| `content-factory publish --job ID --privacy public` | YouTube visibility |
| `content-factory publish --job ID --channels instagram --instagram-video-url URL` | IG with public URL |
| `content-factory status --job ID` | Show job state |

Config: [`config/default.yaml`](config/default.yaml). Secrets: copy [`.env.example`](.env.example) → `.env`.

## Voice (free + long-term)

| Provider | Cost | Notes |
|----------|------|--------|
| **Kokoro-82M** (preferred) | Free, Apache-2.0, local | Natural neural speech; set `voice.provider: kokoro` or `auto` |
| **edge-tts** (default fallback) | Free | Microsoft neural voices; no API key |

`VOICE_PROVIDER=auto|kokoro|edge` in `.env` overrides config.

Optional bed music: drop CC0 `.mp3`/`.wav` into `assets/music/` (ducked ~−22 dB).

## Video

- **Remotion** composition: [`video/src/compositions/Short.tsx`](video/src/compositions/Short.tsx) — kinetic captions, soft orbs, teal/amber brand (not purple-template).
- If Remotion is missing/fails, the bridge renders a clean FFmpeg vertical video automatically.

Preview Remotion studio:

```bash
cd video && npx remotion studio
```

## Google Drive + YouTube (OAuth)

1. Create a [Google Cloud](https://console.cloud.google.com/) project.
2. Enable **Google Drive API** and **YouTube Data API v3**.
3. Configure OAuth consent (External / testing OK for personal use).
4. Create **OAuth client ID** → Application type **Desktop**.
5. Download JSON → save as `credentials/client_secrets.json`.
6. First publish opens a browser for consent; token is cached at `credentials/token.json`.

```bash
content-factory publish --job <id> --channels drive,youtube
```

YouTube default privacy is **private** (`YOUTUBE_PRIVACY` / `--privacy`). Add `#Shorts` is handled automatically.

## Instagram Reels (Graph API)

1. Instagram **Professional** (Business/Creator) account linked to a **Facebook Page**.
2. Meta app with **Instagram Graph API** + `instagram_content_publish`, `pages_show_list`, etc.
3. Long-lived Page token → `.env`:

```env
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_USER_ID=...   # IG business user id
```

Reels creation needs a **public HTTPS `video_url`**. Typical flow:

```bash
# 1) Upload to Drive
content-factory publish --job <id> --channels drive

# 2) Publish IG using Drive file (auto) or an explicit URL
content-factory publish --job <id> --channels instagram
# or
content-factory publish --job <id> --channels instagram \
  --instagram-video-url "https://example.com/final.mp4"
```

Drive `uc?export=download` links only work if the file is shared so Instagram’s crawler can fetch it (anyone-with-link, or host elsewhere).

## Layout

```
content-factory/
  config/default.yaml
  src/content_factory/   # CLI + pipeline
  video/                 # Remotion Short composition
  output/                # job artifacts (gitignored)
  assets/music/          # optional beds
  credentials/           # client_secrets.json, token.json
```

## Notes

- Without Ollama, scripts use a solid structured fallback so produce never blocks.
- Without Kokoro, edge-tts still sounds far more humane than classic robotic TTS.
- Keep uploads private until you review `output/<job>/final.mp4`.
