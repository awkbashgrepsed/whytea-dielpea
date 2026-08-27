#!/usr/bin/env python3
"""Prepare local videos for the whytea-dielpea web library."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


def find_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} was not found in PATH. Install it and try again.")
    return path


def probe_video(ffprobe: str, video: Path) -> dict:
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:format_tags=title,upload_date",
        "-of", "json",
        str(video),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}

    fmt = data.get("format", {})
    tags = fmt.get("tags", {}) or {}
    info: dict = {}
    if fmt.get("duration") is not None:
        try:
            info["duration"] = float(fmt["duration"])
        except (TypeError, ValueError):
            pass
    if tags.get("title"):
        info["title"] = str(tags["title"])
    if tags.get("upload_date"):
        info["upload_date"] = str(tags["upload_date"])
    return info


def make_thumbnail(ffmpeg: str, video: Path, thumbnail: Path, force: bool) -> bool:
    if thumbnail.exists() and not force:
        return False
    cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error",
        "-ss", "00:00:01",
        "-i", str(video),
        "-frames:v", "1",
        "-vf", "scale=640:-2",
        "-q:v", "3",
        "-y", str(thumbnail),
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        # Some very short videos have no frame at one second; retry from the start.
        retry = cmd[:]
        retry[retry.index("-ss") + 1] = "00:00:00"
        try:
            subprocess.run(retry, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


def prepare(folder: Path, force: bool) -> int:
    folder = folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    ffmpeg = find_tool("ffmpeg")
    ffprobe = find_tool("ffprobe")
    videos = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    if not videos:
        print(f"No supported videos found in {folder}")
        return 0

    created_thumbnails = 0
    created_info = 0
    failed = 0
    import_date = date.today().strftime("%Y%m%d")

    for video in sorted(videos):
        thumbnail = video.with_suffix(".jpg")
        info_path = video.with_suffix(".info.json")

        if make_thumbnail(ffmpeg, video, thumbnail, force):
            created_thumbnails += 1

        if not info_path.exists() or force:
            info = probe_video(ffprobe, video)
            info.update({
                "id": video.stem,
                "title": info.get("title") or video.stem,
                "upload_date": import_date,
            })
            info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
            created_info += 1

        if not thumbnail.exists():
            failed += 1
            print(f"Could not create thumbnail: {video}")
        else:
            print(f"Prepared: {video.name} (date: {import_date})")

    print(f"\nDone. Videos: {len(videos)}, thumbnails created: {created_thumbnails}, metadata created: {created_info}, thumbnail failures: {failed}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate thumbnails and metadata for local videos used by web.py.")
    parser.add_argument("folder", help="Folder containing local videos, e.g. videos/hellokitty")
    parser.add_argument("--force", action="store_true", help="Regenerate existing thumbnails and metadata")
    args = parser.parse_args()
    return prepare(Path(args.folder), args.force)


if __name__ == "__main__":
    sys.exit(main())
