#!/usr/bin/env python3
"""Automate a music-to-YouTube pipeline.

Pipeline steps:
1) Build an MP4 from audio + stock media with FFmpeg.
2) Generate metadata (title, description, tags) using OpenAI.
3) Upload to YouTube using YouTube Data API v3.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv
import os

from openai import OpenAI

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


@dataclass
class Metadata:
    title: str
    description: str
    tags: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate music video render + metadata + upload")
    parser.add_argument("--audio", type=Path, required=True, help="Path to input WAV/audio file")
    parser.add_argument("--lyrics", type=Path, required=True, help="Path to lyrics text file")
    parser.add_argument("--style", type=Path, required=True, help="Path to style/mood text file")
    parser.add_argument("--stock-dir", type=Path, required=True, help="Folder with stock media (images/videos)")
    parser.add_argument("--output", type=Path, required=True, help="Output MP4 path")
    parser.add_argument("--privacy", choices=["private", "public", "unlisted"], default=None)
    parser.add_argument("--title-prefix", default="", help="Optional prefix prepended to title")
    parser.add_argument("--max-tags", type=int, default=15)
    parser.add_argument("--dry-run", action="store_true", help="Skip YouTube upload")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def collect_stock_media(stock_dir: Path) -> List[Path]:
    if not stock_dir.exists() or not stock_dir.is_dir():
        raise FileNotFoundError(f"Stock media directory not found: {stock_dir}")

    files = []
    for p in stock_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS.union(VIDEO_EXTS):
            files.append(p)

    if not files:
        raise ValueError(f"No supported media files found in {stock_dir}")

    random.shuffle(files)
    return files


def ffprobe_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def render_video(audio: Path, stock_dir: Path, output: Path) -> None:
    media_files = collect_stock_media(stock_dir)
    chosen = media_files[0]

    duration = ffprobe_duration_seconds(audio)
    output.parent.mkdir(parents=True, exist_ok=True)

    if chosen.suffix.lower() in IMAGE_EXTS:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(chosen),
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-t",
            f"{duration}",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-shortest",
            str(output),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(chosen),
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-t",
            f"{duration}",
            "-shortest",
            str(output),
        ]

    subprocess.run(cmd, check=True)


def generate_metadata(lyrics: str, style: str, title_prefix: str, max_tags: int) -> Metadata:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    channel_name = os.getenv("CHANNEL_NAME", "My Music Channel")

    client = OpenAI(api_key=api_key)
    prompt = f"""
You are helping with YouTube metadata for an original music channel.
Return ONLY valid JSON with keys: title, description, tags.
- title: catchy but honest, max 100 chars.
- description: 2 short paragraphs + 5 hashtags at the end.
- tags: array of up to {max_tags} short tag strings.

Channel: {channel_name}
Style notes: {style}
Lyrics:\n{lyrics}
""".strip()

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.8,
    )

    text = response.output_text.strip()
    data = json.loads(text)

    title = str(data.get("title", "Untitled Track")).strip()
    if title_prefix:
        title = f"{title_prefix.strip()} {title}".strip()

    description = str(data.get("description", "")).strip()
    tags = [str(t).strip() for t in data.get("tags", []) if str(t).strip()]
    tags = tags[:max_tags]

    return Metadata(title=title[:100], description=description, tags=tags)


def save_metadata(metadata: Metadata, output_video: Path) -> Path:
    metadata_path = output_video.with_suffix(".metadata.json")
    payload = {
        "title": metadata.title,
        "description": metadata.description,
        "tags": metadata.tags,
    }
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return metadata_path


def youtube_service():
    secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json")
    token_file = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")

    creds = None
    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_file).write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: Path, metadata: Metadata, privacy_status: str) -> str:
    youtube = youtube_service()
    category_id = os.getenv("YOUTUBE_CATEGORY_ID", "10")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": category_id,
            },
            "status": {"privacyStatus": privacy_status},
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    return response["id"]


def main() -> None:
    load_dotenv()
    args = parse_args()

    require_file(args.audio, "Audio file")
    require_file(args.lyrics, "Lyrics file")
    require_file(args.style, "Style file")

    lyrics = args.lyrics.read_text(encoding="utf-8")
    style = args.style.read_text(encoding="utf-8")

    render_video(args.audio, args.stock_dir, args.output)
    metadata = generate_metadata(lyrics, style, args.title_prefix, args.max_tags)
    metadata_path = save_metadata(metadata, args.output)

    print(f"Rendered video: {args.output}")
    print(f"Saved metadata: {metadata_path}")
    print(f"Title: {metadata.title}")

    if args.dry_run:
        print("Dry-run enabled: skipped YouTube upload.")
        return

    privacy = args.privacy or os.getenv("YOUTUBE_DEFAULT_PRIVACY", "private")
    video_id = upload_video(args.output, metadata, privacy)
    print(f"Uploaded video ID: {video_id}")
    print(f"Watch URL: https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
