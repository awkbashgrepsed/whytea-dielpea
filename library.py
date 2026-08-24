#!/usr/bin/env python3
"""Local browser library for whytea-dielpea."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "watch_state.json"


def load_config() -> dict:
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"download_dir": "videos", **data}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def video_id_from_name(path: Path) -> str:
    match = re.search(r"\[([^\[\]]+)\]", path.stem)
    if match:
        return match.group(1)
    return path.stem


def read_info(path: Path) -> dict:
    info_path = path.with_suffix(".info.json")
    if info_path.exists():
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass

    # Compatibility with videos downloaded before .info.json was enabled.
    return {}


def scan_library() -> list[dict]:
    cfg = load_config()
    root = ROOT / str(cfg["download_dir"])
    if not root.exists():
        return []

    state = load_state()
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".mp4", ".mkv", ".webm", ".mov"}:
            continue
        info = read_info(path)
        vid = str(info.get("id") or video_id_from_name(path))
        uploader = str(info.get("uploader") or info.get("channel") or path.parent.name)
        title = str(info.get("title") or path.stem)
        upload_date = str(info.get("upload_date") or "")
        timestamp = info.get("timestamp")
        if not upload_date and timestamp:
            try:
                upload_date = time.strftime("%Y-%m-%d", time.localtime(float(timestamp)))
            except (ValueError, TypeError, OverflowError):
                pass
        result.append({
            "id": vid,
            "title": title,
            "channel": uploader,
            "upload_date": upload_date,
            "duration": info.get("duration"),
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "watched": bool(state.get(vid, {}).get("watched", False)),
            "watched_at": state.get(vid, {}).get("watched_at"),
        })

    result.sort(key=lambda x: (x.get("upload_date", ""), x.get("title", "")), reverse=True)
    return result


def set_watched(video_id: str, watched: bool) -> bool:
    videos = {item["id"]: item for item in scan_library()}
    if video_id not in videos:
        return False
    state = load_state()
    state[video_id] = {"watched": bool(watched), "watched_at": int(time.time()) if watched else None}
    save_state(state)
    return True
