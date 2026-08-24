#!/usr/bin/env python3
"""whytea-dielpea: keep a local offline copy of videos from selected YouTube channels."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SOURCES_PATH = ROOT / "sources.txt"
ARCHIVE_PATH = ROOT / "archive.txt"
DEFAULT_CONFIG = {
    "download_dir": "videos",
    "quality": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "latest_per_source": 5,
    "sleep_between_sources": 2,
    "retries": 10,
    "fragment_retries": 10,
    "continue_downloads": True,
    "no_shorts": True,
    "cookies_from_browser": "",
    "extra_args": [],
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=4) + "\n", encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid config.json: {exc}")
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    return cfg


def load_sources() -> list[str]:
    if not SOURCES_PATH.exists():
        SOURCES_PATH.write_text(
            "# Put one YouTube channel URL per line.\n"
            "# Examples:\n"
            "# https://www.youtube.com/@Example/videos\n"
            "# https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx/videos\n",
            encoding="utf-8",
        )
        return []

    sources = []
    for line in SOURCES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            sources.append(line)
    return sources


def find_ytdlp() -> str:
    exe = shutil.which("yt-dlp")
    if exe:
        return exe
    raise SystemExit(
        "yt-dlp was not found in PATH. Install yt-dlp through your system/package manager "
        "and make sure `yt-dlp --version` works in a terminal."
    )


def build_command(ytdlp: str, source: str, cfg: dict) -> list[str]:
    download_dir = ROOT / str(cfg["download_dir"])
    download_dir.mkdir(parents=True, exist_ok=True)

    # %(uploader)s and %(title)s keep the local library organized without
    # putting channel-specific paths into the source list.
    output = str(download_dir / "%(uploader)s" / "%(upload_date)s - %(title)s [%(id)s].%(ext)s")

    cmd = [
        ytdlp,
        "--ignore-errors",
        "--no-abort-on-error",
        "--retries", str(cfg["retries"]),
        "--fragment-retries", str(cfg["fragment_retries"]),
        "--continue",
        "--no-overwrites",
        "--download-archive", str(ARCHIVE_PATH),
        "--format", str(cfg["quality"]),
        "--merge-output-format", "mp4",
        "--output", output,
        "--windows-filenames",
        "--restrict-filenames",
        "--yes-playlist",
        "--playlist-end", str(cfg["latest_per_source"]),
    ]

    browser = str(cfg.get("cookies_from_browser", "")).strip()
    if browser:
        # Accepted by yt-dlp as e.g. firefox, chrome, chromium, edge.
        cmd += ["--cookies-from-browser", browser]

    if cfg.get("no_shorts", True):
        cmd += ["--match-filter", "!is_live & !duration < 60"]

    extra_args = cfg.get("extra_args", [])
    if not isinstance(extra_args, list) or not all(isinstance(x, str) for x in extra_args):
        raise SystemExit("config.json: extra_args must be a JSON array of strings")
    cmd += extra_args
    cmd.append(source)
    return cmd


def run_source(ytdlp: str, source: str, cfg: dict) -> int:
    print(f"\n=== {source} ===")
    cmd = build_command(ytdlp, source, cfg)
    print("Running yt-dlp...")
    print(" ".join(subprocess.list2cmdline([x]) for x in cmd))
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 130


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the latest videos from your selected YouTube sources.")
    parser.add_argument("--once", action="store_true", help="Check sources once and exit (default).")
    parser.add_argument("--watch", action="store_true", help="Keep checking sources periodically.")
    parser.add_argument("--interval", type=int, default=1800, help="Seconds between --watch checks (default: 1800).")
    parser.add_argument("--check", action="store_true", help="Only verify yt-dlp and show configured sources.")
    args = parser.parse_args()

    cfg = load_config()
    sources = load_sources()
    ytdlp = find_ytdlp()

    if args.check:
        version = subprocess.check_output([ytdlp, "--version"], text=True).strip()
        print(f"yt-dlp: {version}")
        print(f"sources: {len(sources)}")
        print(f"archive: {ARCHIVE_PATH}")
        print(f"download directory: {ROOT / str(cfg['download_dir'])}")
        return 0

    if not sources:
        print(f"No sources configured. Add YouTube channel URLs to {SOURCES_PATH}.")
        return 1

    while True:
        print("\nwhytea-dielpea")
        print("Offline YouTube downloader")
        print("===========================")
        print(f"Sources: {len(sources)} | Latest per source: {cfg['latest_per_source']}")

        for index, source in enumerate(sources, 1):
            code = run_source(ytdlp, source, cfg)
            if code not in (0, 1):
                print(f"yt-dlp exited with code {code}; continuing to the next source.")
            if index != len(sources):
                time.sleep(max(0, int(cfg["sleep_between_sources"])))

        if not args.watch:
            break

        wait = max(1, args.interval)
        print(f"\nNext check in {wait} seconds. Press Ctrl+C to stop.")
        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            print("\nStopped.")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
