# Content Factory Bot

Local, mostly-free pipeline that turns a **topic** into a faceless **YouTube Short / Instagram Reel**:

1. Write a structured script (Ollama, with built-in fallback)
2. Synthesize **humane** narration (**Kokoro** → **edge-tts** → **macOS say**)
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

# Smoke test (script only / skip heavy render)
content-factory produce --topic "Deep work tips" --dry-run-script
content-factory produce --topic "Deep work tips" --skip-render

# Publish (after credentials below)
content-factory publish --job <job_id> --channels drive,youtube,instagram
```

Job files land in `output/<job_id>/` (`script.json`, voice/mixed audio, `props.json`, `final.mp4`, `job.json`).

## CLI

| Command | What it does |
|---------|----------------|
| `content-factory produce --topic "..."` | Script → voice → video |
| `content-factory produce --topic "..." --dry-run-script` | Script only |
| `content-factory produce --topic "..." --skip-render` | Stop after audio |
| `content-factory publish --job ID --channels drive,youtube` | Upload |
| `content-factory publish --job ID --privacy public` | YouTube visibility |
| `content-factory publish --job ID --channels instagram --instagram-video-url URL` | IG with public URL |
| `content-factory status --job ID` | Show job state |

Config: [`config/default.yaml`](config/default.yaml). Secrets: copy [`.env.example`](.env.example) → `.env`.

## Voice (genuine AI male — free + local)

Default is **Piper Ryan** (high-quality neural male), not classic robotic TTS.

| Provider | Cost | Notes |
|----------|------|--------|
| **Piper Ryan** (default) | Free, local | `en_US-ryan-high` neural male — `pip install piper-tts` |
| **Kokoro `am_adam`** | Free, local | Optional; needs Python 3.10–3.12 + `./scripts/setup_male_voice.sh` |
| **edge-tts AndrewNeural** | Free cloud | Microsoft neural male fallback |
| **macOS Daniel** | Free | Last resort |

Config: `voice.provider: piper` and `piper_model: en_US-ryan-high` in `config/default.yaml`.  
Override with `VOICE_PROVIDER=piper` in `.env` if needed.

Optional bed music: drop CC0 `.mp3`/`.wav` into `assets/music/` (ducked ~−22 dB).

## Video

- **Remotion** composition: [`video/src/compositions/Short.tsx`](video/src/compositions/Short.tsx) — kinetic captions, soft orbs, teal/amber brand (not purple-template).
- If Remotion is missing/fails, the bridge renders a clean FFmpeg vertical video automatically.

Preview Remotion studio:

```bash
cd video && npx remotion studio
```

## Google Drive + YouTube (OAuth)

**Active target:** YouTube channel **MotivateUrSelf** (`@MotivateUrSelf-y9h`) Shorts. Instagram is paused for now.

### Recommended: device login (approve on your phone)

Best when this Mac cannot open personal Gmail in a browser.

1. Create a [Google Cloud](https://console.cloud.google.com/) project (personal Gmail is fine).
2. Enable **Google Drive API** and **YouTube Data API v3**.
3. Configure OAuth consent (External / testing OK). Add your **personal Gmail** as a **Test user**.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **TVs and Limited Input devices** (required for device flow)
   - Name: e.g. `content-factory-tv`
5. Download JSON → save as `credentials/client_secrets.json` (replace any old Desktop client file).
6. On this Mac:

```bash
source .venv/bin/activate
content-factory google-login
# prints a URL + code — open on your phone with personal Gmail → Allow
```

Token is saved at `credentials/token.json`. Then:

```bash
content-factory publish --job <id> --channels youtube --privacy private
```

Set `GOOGLE_OAUTH_FLOW=browser` only if you use a **Desktop** OAuth client and local browser login.

**If phone shows “Service unavailable / isn’t available for your account”:**  
Google is blocking that Google account for device login (very common on **org/Workspace** Gmail, or when YouTube is disabled for the account). Device flow will not work with that login. Use a **personal** Gmail that owns **MotivateUrSelf**, on a machine where personal Gmail works:

1. Recreate/download a **Desktop** OAuth client → `credentials/client_secrets.json`
2. On that machine: `GOOGLE_OAUTH_FLOW=browser content-factory google-login --force --flow browser`
3. Copy `credentials/token.json` back to this Mac (same Desktop `client_secrets.json` here)

Do **not** approve with org Gmail if IT has YouTube / third‑party apps restricted.

### Other computer: auth only (no full bot install)

You do **not** need Remotion, Piper, Ollama, or `pip install -e .` there. Only Python + 3 small packages:

```bash
git clone https://github.com/ManikandanP47/Content-factory-bot.git
cd Content-factory-bot
# Desktop OAuth JSON → credentials/client_secrets.json
chmod +x scripts/google_login_minimal.sh
./scripts/google_login_minimal.sh
```

Copy these two files back to the work Mac:

- `credentials/token.json`
- `credentials/client_secrets.json` (same Desktop client)

YouTube default privacy is **private** (`YOUTUBE_PRIVACY` / `--privacy`). Flip to `public` after a successful test. `#Shorts` is added automatically.

## Instagram Reels (Graph API) — paused

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

## How to run (manual)

```bash
cd ~/content-factory
source .venv/bin/activate

# One Short / Reel (complete ending with CTA hold)
content-factory produce --topic "Your topic here"

# Review
open output/<job_id>/final.mp4

# Optional publish later
content-factory publish --job <job_id> --channels drive,youtube
```

List jobs: `content-factory list-jobs` (or look in `output/`).

## Local automation (your laptop, 09:00–22:00 IST weekdays)

**Mon–Fri only** (Sat/Sun skipped). **5 public Shorts/day** in evening / night scroll windows:

| Time (IST) | Audience moment |
|---|---|
| **17:00** | Leaving work / college |
| **18:00** | Commute → unwind scroll |
| **19:00** | Dinner break |
| **20:00** | Prime evening Shorts |
| **21:00** | Late-night wind-down |

Each run: new random topic → fresh B-roll → produce → auto-upload (~**25 Shorts/week**).

**Requirements:** Mac awake **~17:00–22:00** on weekdays (plugged in; prevent sleep during that window). Missed slots are skipped — no Monday catch-up burst.

Weekends off by default (`POST_ON_WEEKENDS=0` in `.env`).

### Keep the Mac awake (no admin required)

**Without admin**, macOS cannot be woken from sleep automatically. Use this instead:

```bash
./scripts/setup_wake_schedule.sh install-no-admin
```

| What | Does |
|---|---|
| **Stay awake** | `caffeinate` Mon–Fri ~16:58–22:00 while you're logged in |
| **Catch-up** | When you **open/login** between 17:00–22:00, posts **1 Short** if today's quota isn't met (max ~1/hour) |
| **Scheduled slots** | Still fire at 17/18/19/20/21:00 **if laptop is already on** |

**Your part (no IT needed):**
- Open laptop **Mon–Fri ~17:00–22:00** (logged in, lid open, plugged in if possible)
- Don't fully shut down before evening — sleep is OK if you open it by 17:00

If IT forces sleep and `caffeinate` is blocked, the only fixes are: **personal Mac**, **home PC**, or **cloud runner** (we can set that up later).

Admin-only option (needs sudo): `./scripts/setup_wake_schedule.sh wake-only`

1. Topics: [`config/topics.txt`](config/topics.txt) — random unused line each day (`config/.topics_done`).
2. Visuals: unique B-roll per job (`assets/broll/.usage.json` rotation).
3. Copy `.env.example` → `.env` with `AUTO_PUBLISH=1` and `credentials/token.json` in place.
4. Install:

```bash
chmod +x scripts/*.sh
./scripts/install_automation.sh install
```

5. Test once (skips if already ran today):

```bash
./scripts/daily_run.sh
```

6. Logs: `output/logs/`. Uninstall: `./scripts/install_automation.sh uninstall`.

`.env` defaults (also set in launchd):

```bash
AUTO_PUBLISH=1
PUBLISH_CHANNELS=youtube
YOUTUBE_PRIVACY=public
```

Laptop must be **awake** at those times (not fully shut down). Sleep that allows background work is usually fine.

## Notes

- Without Ollama, scripts use a solid structured fallback so produce never blocks.
- Without Kokoro, edge-tts still sounds far more humane than classic robotic TTS.
- Shorts now pad ~2.4s after narration so the CTA finishes (no mid-close cut).
- Keep uploads private until you review `output/<job>/final.mp4`.
