#!/usr/bin/env python3
"""Serve the whytea-dielpea library to a local web browser."""
from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse

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
body{font-family:Arial,sans-serif;max-width:1200px;margin:28px auto;padding:0 18px;background:#111;color:#eee}
h1{font-size:24px;margin-bottom:4px}.sub{color:#999;margin-bottom:22px}
.toolbar{display:flex;gap:8px;margin-bottom:22px;flex-wrap:wrap}
button{background:#292929;color:#eee;border:1px solid #444;padding:7px 11px;cursor:pointer;border-radius:3px}
button:hover{background:#333}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:22px}.card{min-width:0}.card.watched{opacity:.58}
.thumb{display:block;width:100%;aspect-ratio:16/9;background:#222;object-fit:cover;border-radius:5px}.placeholder{display:flex;align-items:center;justify-content:center;color:#777}
a{color:inherit;text-decoration:none}.title{font-size:16px;font-weight:600;line-height:1.3;margin-top:9px}.channel{color:#aaa;font-size:14px;margin-top:5px}.date{color:#888;font-size:13px;margin-top:4px}.badge{font-size:11px;border:1px solid #555;padding:2px 5px;margin-left:6px;color:#aaa}.empty{color:#999;padding:30px 0}
.player{max-width:1000px;margin:auto}.player video{width:100%;max-height:75vh;background:#000}.back{display:inline-block;margin-bottom:14px;color:#aaa}.watch-title{font-size:21px;margin:12px 0 5px}.watch-meta{color:#999;margin-bottom:15px}.actions{display:flex;gap:8px;margin-bottom:25px}
@media(max-width:650px){body{margin-top:18px}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="app"></div>
<script>
let videos=[],filter='all';
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function videoUrl(v){return '/video/'+encodeURIComponent(v.path);}
function thumbUrl(v){return v.thumbnail?'/thumb/'+encodeURIComponent(v.thumbnail):null;}
function duration(s){if(!s)return '';s=Number(s);if(!Number.isFinite(s))return '';let h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=Math.floor(s%60);return h?`${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`:`${m}:${String(sec).padStart(2,'0')}`;}
function home(){history.pushState({},'', '/');render();}
function openVideo(id){history.pushState({},'', '/watch/'+encodeURIComponent(id));render();}
function render(){
 const app=document.getElementById('app'); const path=location.pathname;
 if(path.startsWith('/watch/')){let id=decodeURIComponent(path.slice(7)),v=videos.find(x=>x.id===id);if(!v){app.innerHTML='<div class="empty">Video not found.</div>';return;}
   app.innerHTML=`<div class="player"><a class="back" href="/" onclick="event.preventDefault();home()">← Back to library</a><video id="player" controls autoplay preload="metadata" src="${videoUrl(v)}" onended="mark('${esc(v.id)}',true)"></video><div class="watch-title">${esc(v.title)}</div><div class="watch-meta">${esc(v.channel)} · ${esc(v.upload_date||'Unknown upload date')}${duration(v.duration)?' · '+duration(v.duration):''}</div><div class="actions"><button onclick="mark('${esc(v.id)}',${!v.watched})">${v.watched?'Mark unwatched':'Mark watched'}</button></div></div>`;
   return;
 }
 let a=videos.filter(v=>filter==='all'||(filter==='watched'?v.watched:!v.watched));
 app.innerHTML=`<h1>whytea-dielpea</h1><div class="sub">Local YouTube library · ${videos.filter(v=>!v.watched).length} unwatched</div><div class="toolbar"><button onclick="filter='all';render()">All</button><button onclick="filter='unwatched';render()">Unwatched</button><button onclick="filter='watched';render()">Watched</button><button onclick="load()">Refresh</button></div><div class="grid">${a.length?a.map(v=>`<article class="card ${v.watched?'watched':''}"><a href="/watch/${encodeURIComponent(v.id)}" onclick="event.preventDefault();openVideo('${esc(v.id)}')">${v.thumbnail?`<img class="thumb" src="${thumbUrl(v)}" loading="lazy" alt="">`:'<div class="thumb placeholder">No thumbnail</div>'}<div class="title">${esc(v.title)}${v.watched?'<span class="badge">watched</span>':''}</div><div class="channel">${esc(v.channel)}</div><div class="date">${esc(v.upload_date||'Unknown upload date')}</div></a></article>`).join(''):'<div class="empty">No videos here.</div>'}</div>`;
}
async function load(){let r=await fetch('/api/videos');videos=await r.json();render();}
async function mark(id,watched){await fetch('/api/watch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,watched})});await load();if(location.pathname.startsWith('/watch/'))render();}
window.onpopstate=render;load();
</script>
</body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(fmt % args)
    def send_json(self, data, status=200):
        raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path in ('/','/watch') or parsed.path.startswith('/watch/'):
            raw=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if parsed.path=='/api/videos': self.send_json(scan_library_with_thumbnails());return
        if parsed.path.startswith('/video/'): self.serve_file(unquote(parsed.path[7:]),'video');return
        if parsed.path.startswith('/thumb/'): self.serve_file(unquote(parsed.path[7:]),'thumb');return
        self.send_error(404)
    def do_POST(self):
        if urlparse(self.path).path!='/api/watch':self.send_error(404);return
        try:
            length=int(self.headers.get('Content-Length','0'));data=json.loads(self.rfile.read(length));ok=set_watched(str(data['id']),bool(data.get('watched',True)));self.send_json({'ok':ok},200 if ok else 404)
        except (ValueError,KeyError,json.JSONDecodeError):self.send_error(400)
    def serve_file(self,relative,kind):
        cfg=load_config();root=(ROOT/str(cfg['download_dir'])).resolve();target=(root/relative).resolve()
        if not target.is_file() or root not in target.parents:self.send_error(404);return
        size=target.stat().st_size;start,end=0,size-1;range_header=self.headers.get('Range')
        if range_header and range_header.startswith('bytes='):
            try:
                spec=range_header[6:].split(',',1)[0];left,right=spec.split('-',1)
                if left:start=int(left);end=int(right) if right else size-1
                else:start=max(0,size-int(right))
                end=min(end,size-1)
                if start>end or start>=size:raise ValueError
            except ValueError:self.send_error(416);return
            status=HTTPStatus.PARTIAL_CONTENT
        else:status=HTTPStatus.OK
        length=end-start+1;mime=mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(length))
        if status==HTTPStatus.PARTIAL_CONTENT:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        with target.open('rb') as f:
            f.seek(start);remaining=length
            while remaining:
                chunk=f.read(min(1024*1024,remaining))
                if not chunk:break
                self.wfile.write(chunk);remaining-=len(chunk)

def scan_library_with_thumbnails():
    items=scan_library();cfg=load_config();root=(ROOT/str(cfg['download_dir'])).resolve()
    for item in items:
        video=(root/item['path']).resolve();thumb=None
        for suffix in ('.jpg','.jpeg','.png','.webp'):
            candidate=video.with_suffix(suffix)
            if candidate.is_file():thumb=str(candidate.relative_to(root)).replace('\\','/');break
        item['thumbnail']=thumb
    return items

def main():
    server=ThreadingHTTPServer((HOST,PORT),Handler);print(f'whytea-dielpea library: http://{HOST}:{PORT}');print('Press Ctrl+C to stop.')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
