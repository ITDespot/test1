# YouTube Music Upload Automation

This repository includes a practical automation pipeline for your current workflow:

1. Start from a `.wav` song exported from Suno.
2. Build an `.mp4` video by combining your audio and stock media assets (images/videos).
3. Generate YouTube metadata (title, description, tags) using OpenAI.
4. Upload to YouTube through the official YouTube Data API.

## What this automates

- ✅ Video rendering with FFmpeg (instead of manual Filmora timeline work).
- ✅ AI metadata generation from your lyrics + style notes.
- ✅ YouTube upload (title, description, tags, privacy state).

## What remains manual (first-time only)

- One-time setup for API credentials:
  - OpenAI API key.
  - Google OAuth client credentials for YouTube upload.
- Curating your local stock media folder.


## Not technical? Do this first

If you are not a coder, start with **START_HERE.md** for a simple checklist:

- Install Python + FFmpeg
- Add your keys once
- Run a safe dry-run
- Run upload

## Quick start

### 1) Install system dependency

- FFmpeg must be installed and available in PATH.

### 2) Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure environment

Copy and fill values:

```bash
cp .env.example .env
```

### 4) Prepare inputs

- `inputs/song.wav`
- `inputs/lyrics.txt`
- `inputs/style.txt`
- `inputs/stock_media/` (images/videos)

### 5) Run pipeline

```bash
python automate_pipeline.py \
  --audio inputs/song.wav \
  --lyrics inputs/lyrics.txt \
  --style inputs/style.txt \
  --stock-dir inputs/stock_media \
  --output outputs/song.mp4 \
  --privacy private
```

The script will:

- Render `outputs/song.mp4`
- Save metadata draft to `outputs/song.metadata.json`
- Upload to YouTube (unless `--dry-run` is provided)

## Usage options

```bash
python automate_pipeline.py --help
```

Notable flags:

- `--dry-run`: Render + metadata only, skip upload.
- `--title-prefix`: Add a channel-specific prefix.
- `--max-tags`: Limit tags count (default 15).

## Notes

- Ensure you have rights to all media used.
- Keep metadata truthful and non-spammy for YouTube policy compliance.
- If you still want Filmora-specific effects, you can keep using Filmora for editing and only automate metadata + upload.
