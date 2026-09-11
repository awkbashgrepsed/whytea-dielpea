#!/usr/bin/env python3
"""whytea-dielpea: keep a local offline copy of videos from YouTube sources."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SOURCES_PATH = ROOT / "sources.txt"
ARCHIVE_PATH = ROOT / "archive.txt"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Missing config.json: {CONFIG_PATH}")
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid config.json: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("config.json must contain a JSON object")
    return data


def load_sources() -> list[str]:
    if not SOURCES_PATH.exists():
        SOURCES_PATH.write_text(
            "# Put one YouTube channel URL per line.\n"
            "# https://www.youtube.com/@Example/videos\n",
            encoding="utf-8",
        )
        return []
    return [
        x.strip()
        for x in SOURCES_PATH.read_text(encoding="utf-8").splitlines()
        if x.strip() and not x.strip().startswith("#")
    ]


def find_ytdlp() -> str:
    exe = shutil.which("yt-dlp")
    if exe:
        return exe
    raise SystemExit(
        "yt-dlp was not found in PATH. Install system yt-dlp and make sure `yt-dlp --version` works."
    )


def validate_extra_args(cfg: dict) -> list[str]:
    extra_args = cfg.get("extra_args", [])
    if not isinstance(extra_args, list) or not all(isinstance(x, str) for x in extra_args):
        raise SystemExit("config.json: extra_args must be a JSON array of strings")
    return extra_args


def build_command(
    ytdlp: str,
    source: str,
    cfg: dict,
    source_type: str = "auto",
) -> list[str]:
    """Build a yt-dlp command while keeping every download in its channel folder.

    source_type controls playlist handling:
      auto     - normal subscription/source behavior (limited by latest_per_source)
      channel  - download the complete channel
      playlist - download the complete playlist
      video    - download exactly one video
    """
    download_dir = ROOT / str(cfg["download_dir"])
    download_dir.mkdir(parents=True, exist_ok=True)

    # %(uploader)s is deliberately the first directory component. This means a
    # one-video download goes into the existing channel folder instead of getting
    # a folder named after the video or playlist.
    output = str(
        download_dir
        / "%(uploader)s"
        / "%(upload_date)s - %(title)s [%(id)s].%(ext)s"
    )

    cmd = [
        ytdlp,
        "--ignore-errors",
        "--no-abort-on-error",
        "--retries",
        str(cfg["retries"]),
        "--fragment-retries",
        str(cfg["fragment_retries"]),
        "--continue",
        "--no-overwrites",
        "--download-archive",
        str(ARCHIVE_PATH),
        "--format",
        str(cfg["quality"]),
        "--merge-output-format",
        "mp4",
        "--output",
        output,
        "--windows-filenames",
        "--restrict-filenames",
        "--write-info-json",
        "--no-clean-infojson",
        "--write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--remote-components",
        "ejs:npm",
    ]

    # Subscription downloads keep the existing "latest N" behavior. Explicit
    # channel/playlist downloads intentionally have no playlist-end limit.
    if source_type == "video":
        cmd.append("--no-playlist")
    else:
        cmd.append("--yes-playlist")
        if source_type in {"auto", "channel"} and source_type != "channel":
            cmd += ["--playlist-end", str(cfg["latest_per_source"])]
        elif source_type == "auto":
            cmd += ["--playlist-end", str(cfg["latest_per_source"])]

    browser = str(cfg.get("cookies_from_browser", "")).strip()
    if browser:
        cmd += ["--cookies-from-browser", browser]

    if cfg.get("no_shorts", True):
        cmd += ["--match-filter", "!is_live"]

    cmd += validate_extra_args(cfg)
    cmd.append(source)
    return cmd


def run_source(ytdlp: str, source: str, cfg: dict, source_type: str = "auto") -> int:
    print(f"\n=== {source} ===")
    cmd = build_command(ytdlp, source, cfg, source_type)
    print(f"Running yt-dlp with quality: {cfg['quality']}")
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 130


def download_explicit(ytdlp: str, source: str, cfg: dict, source_type: str) -> int:
    if source_type == "channel":
        print("Downloading the full channel into videos/<channel>/")
    elif source_type == "playlist":
        print("Downloading the full playlist into videos/<channel>/")
    else:
        print("Downloading one video into videos/<channel>/")
    return run_source(ytdlp, source, cfg, source_type)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download subscribed channels, full channels, playlists, or individual videos."
    )
    subparsers = parser.add_subparsers(dest="command")

    sync = subparsers.add_parser(
        "sync",
        help="download the configured subscribed channels (latest_per_source each)",
    )
    sync.add_argument("--watch", action="store_true", help="repeat the subscription sync")
    sync.add_argument("--interval", type=int, default=1800, help="seconds between watch checks")

    channel = subparsers.add_parser("channel", help="download a complete YouTube channel")
    channel.add_argument("url", help="YouTube channel URL")

    playlist = subparsers.add_parser("playlist", help="download a complete YouTube playlist")
    playlist.add_argument("url", help="YouTube playlist URL")

    video = subparsers.add_parser("video", help="download one YouTube video")
    video.add_argument("url", help="YouTube video URL")

    # Keep the old interface working: `python whytea.py` means subscription sync.
    parser.add_argument("--once", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--watch", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--interval", type=int, default=1800, help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="check yt-dlp and configuration")

    args = parser.parse_args()
    cfg = load_config()
    ytdlp = find_ytdlp()

    if args.check:
        sources = load_sources()
        print(f"yt-dlp: {subprocess.check_output([ytdlp, '--version'], text=True).strip()}")
        print(f"sources: {len(sources)}")
        print(f"archive: {ARCHIVE_PATH}")
        print(f"quality: {cfg['quality']}")
        return 0

    if args.command in {"channel", "playlist", "video"}:
        return download_explicit(ytdlp, args.url, cfg, args.command)

    # No subcommand means the original subscription downloader.
    sources = load_sources()
    watch = getattr(args, "watch", False)
    interval = getattr(args, "interval", 1800)

    if not sources:
        print(f"No sources configured. Add YouTube channel URLs to {SOURCES_PATH}.")
        return 1

    while True:
        print(
            f"\nwhytea-dielpea | {len(sources)} sources | "
            f"latest {cfg['latest_per_source']} each"
        )
        for index, source in enumerate(sources, 1):
            code = run_source(ytdlp, source, cfg, "auto")
            if code not in (0, 1):
                print(f"yt-dlp exited with code {code}; continuing.")
            if index != len(sources):
                time.sleep(max(0, int(cfg["sleep_between_sources"])))
        if not watch:
            break
        try:
            print(f"\nNext check in {max(1, interval)} seconds. Press Ctrl+C to stop.")
            time.sleep(max(1, interval))
        except KeyboardInterrupt:
            print("\nStopped.")
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
