#!/usr/bin/env python3
"""Serve the whytea-dielpea library to a local web browser."""
from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from library import ROOT, load_config, scan_library, set_watched

HOST = "127.0.0.1"
PORT = 8765

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>whytea-dielpea</title>
<style>
body{font-family:Arial,sans-serif;max-width:1100px;margin:30px auto;padding:0 18px;background:#111;color:#eee}
h1{font-size:24px;margin-bottom:4px}.sub{color:#999;margin-bottom:22px}
.toolbar{display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap}
button{background:#292929;color:#eee;border:1px solid #444;padding:7px 11px;cursor:pointer;border-radius:3px}
button:hover{background:#333}.video{display:grid;grid-template-columns:240px 1fr;gap:15px;padding:12px 0;border-bottom:1px solid #292929}
.video.watched{opacity:.55}.thumb{width:240px;height:135px;background:#222;display:flex;align-items:center;justify-content:center;color:#777}
video{width:240px;height:135px;background:#000}.title{font-size:17px;margin-bottom:8px}.channel{color:#aaa}.date{color:#888;font-size:13px;margin-top:7px}.badge{font-size:12px;border:1px solid #555;padding:2px 5px;margin-left:8px;color:#aaa}
.empty{color:#999;padding:30px 0}@media(max-width:650px){.video{grid-template-columns:1fr}.thumb,video{width:100%;height:auto}}
</style>
</head>
<body>
<h1>whytea-dielpea</h1>
<div class="sub">Local YouTube library</div>
<div class="toolbar"><button onclick="filter='all';render()">All</button><button onclick="filter='unwatched';render()">Unwatched</button><button onclick="filter='watched';render()">Watched</button><button onclick="load()">Refresh</button></div>
<div id="list"></div>
<script>
let videos=[],filter='all';
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function render(){
 const list=document.getElementById('list'); let a=videos.filter(v=>filter==='all'||(filter==='watched'?v.watched:!v.watched));
 if(!a.length){list.innerHTML='<div class="empty">No videos here.</div>';return;}
 list.innerHTML=a.map(v=>`<div class="video ${v.watched?'watched':''}" id="v-${esc(v.id)}">
 <div><video controls preload="metadata" src="/video/${encodeURIComponent(v.path)}" onended="mark('${esc(v.id)}',true)"></video></div>
 <div><div class="title">${esc(v.title)} ${v.watched?'<span class="badge">watched</span>':''}</div><div class="channel">${esc(v.channel)}</div><div class="date">${esc(v.upload_date||'Unknown upload date')}</div><br><button onclick="mark('${esc(v.id)}',${!v.watched})">${v.watched?'Mark unwatched':'Mark watched'}</button></div>
 </div>`).join('');
}
async function load(){let r=await fetch('/api/videos');videos=await r.json();render();}
async function mark(id,watched){await fetch('/api/watch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,watched})});await load();}
load();
</script>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def send_json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            raw = HTML.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if parsed.path == "/api/videos":
            self.send_json(scan_library()); return
        if parsed.path.startswith("/video/"):
            self.serve_video(unquote(parsed.path[len("/video/"):]))
            return
        self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/watch":
            self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            ok = set_watched(str(data["id"]), bool(data.get("watched", True)))
            self.send_json({"ok": ok}, 200 if ok else 404)
        except (ValueError, KeyError, json.JSONDecodeError):
            self.send_error(400)

    def serve_video(self, relative):
        cfg = load_config(); root = (ROOT / str(cfg["download_dir"])).resolve()
        target = (root / relative).resolve()
        if not target.is_file() or root not in target.parents:
            self.send_error(404); return
        size = target.stat().st_size
        start, end = 0, size - 1
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                spec = range_header[6:].split(",", 1)[0]
                left, right = spec.split("-", 1)
                if left:
                    start = int(left)
                    end = int(right) if right else size - 1
                else:
                    length = int(right); start = max(0, size - length)
                end = min(end, size - 1)
                if start > end or start >= size: raise ValueError
            except ValueError:
                self.send_error(416); return
            status = HTTPStatus.PARTIAL_CONTENT
        else:
            status = HTTPStatus.OK
        length = end - start + 1
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with target.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk: break
                self.wfile.write(chunk); remaining -= len(chunk)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"whytea-dielpea library: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__":
    main()
