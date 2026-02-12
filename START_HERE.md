# Start Here (No Coding Needed)

You only need to do this once, then it becomes mostly one command per song.

## 1) Install 2 things

1. **Python 3.11+**
2. **FFmpeg**

Check they work:

```bash
python --version
ffmpeg -version
```

---

## 2) Put these files in this folder

- `client_secret.json` (from Google Cloud OAuth for YouTube)
- your song file, for example: `inputs/song.wav`
- your lyrics text: `inputs/lyrics.txt`
- your style text: `inputs/style.txt`
- stock visuals in: `inputs/stock_media/`

---

## 3) Install Python packages (one time)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you are on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 4) Add your API keys

Copy example env file:

```bash
cp .env.example .env
```

Edit `.env` and set:

- `OPENAI_API_KEY=...`
- `YOUTUBE_CLIENT_SECRETS_FILE=client_secret.json`
- `CHANNEL_NAME=Your Channel Name`

---

## 5) First safe test (no upload)

```bash
python automate_pipeline.py \
  --audio inputs/song.wav \
  --lyrics inputs/lyrics.txt \
  --style inputs/style.txt \
  --stock-dir inputs/stock_media \
  --output outputs/song.mp4 \
  --dry-run
```

This creates:

- `outputs/song.mp4`
- `outputs/song.metadata.json`

---

## 6) Real upload

```bash
python automate_pipeline.py \
  --audio inputs/song.wav \
  --lyrics inputs/lyrics.txt \
  --style inputs/style.txt \
  --stock-dir inputs/stock_media \
  --output outputs/song.mp4 \
  --privacy private
```

On first run, Google opens a browser login so you can authorize YouTube upload.

---

## If you want this even easier

I can simplify this one more step for you next:

- a tiny desktop app with fields + one **Upload** button
- or a drag-and-drop script where you only drop the WAV and click run
