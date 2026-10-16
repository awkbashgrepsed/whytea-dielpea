# whytea-dielpea

An offline YouTube downloader and simple local video library built around the **system-installed `yt-dlp`**.

Put the YouTube channels you care about in `sources.txt`, download while the connection is available, then open the local library in Firefox and watch without YouTube or an internet connection.

## How it works

```text
sources.txt -> whytea.py -> system yt-dlp -> videos/<channel>/
                                      |
                                      v
                                  web.py
                                      |
                                      v
                         Firefox -> 127.0.0.1:8765
```

`archive.txt` prevents already-downloaded videos from being downloaded again. `watch_state.json` records which local videos you have watched.

## Requirements

- Python 3.9+
- system-installed `yt-dlp` available as `yt-dlp` in `PATH`
- `ffmpeg` recommended/required for merging separate video/audio streams

```bash
yt-dlp --version
ffmpeg -version
```

## Setup

Edit `sources.txt`:

```text
https://www.youtube.com/@SomeChannel/videos
https://www.youtube.com/@AnotherChannel/videos
```

Then download the latest configured videos:

```bash
python whytea.py
```

The default is the newest **5 videos per source**. Change `latest_per_source` in `config.json` for more or fewer.

## Download commands

There are now four simple download modes. **Every mode stores videos under the uploader/channel folder**, so a single video does not create a folder named after the video.

### Sync subscribed channels

Uses `sources.txt` and downloads the configured number of newest videos from each source:

```bash
python whytea.py
```

The explicit equivalent is:

```bash
python whytea.py sync
```

### Download a complete channel

Give it a channel URL. There is no `latest_per_source` limit:

```bash
python whytea.py channel https://www.youtube.com/@SomeChannel/videos
```

Files go to:

```text
videos/SomeChannel/
```

### Download a complete playlist

Give it a playlist URL:

```bash
python whytea.py playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

Playlist videos are still placed according to their uploader, for example:

```text
videos/SomeChannel/video.mp4
```

This also handles playlists containing videos from different channels without creating a playlist-named folder.

### Download one video

Give it a normal YouTube video URL:

```bash
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID"
```

If that video belongs to `SomeChannel`, it goes directly into:

```text
videos/SomeChannel/
```

No `videos/Video Title/` folder is created.

The same `archive.txt`, quality, cookies, retry settings, thumbnails, metadata, and other configuration are used for all four download modes.

### List available formats

If yt-dlp reports `Requested format is not available`, list what YouTube actually offers for that video. This does not download the video:

```bash
python whytea.py formats "https://www.youtube.com/watch?v=VIDEO_ID"
```

You can also use the video command:

```bash
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID" --list-formats
```

The output includes format IDs, resolutions, codecs, and file sizes where yt-dlp can determine them.

### Force a format

Use `-f` or `--format` to override whytea's automatic selector with a format ID or any yt-dlp format expression:

```bash
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID" -f 18
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID" --format "bv[height<=360]+ba/b[height<=360]/b"
```

The same option works with `channel`, `playlist`, and `sync`. For example:

```bash
python whytea.py sync --format "bv[height<=480]+ba/b[height<=480]/b"
```

**Safety prompt for numeric format IDs:** if you pass a bare ID such as `-f 247`, whytea pauses because that format may contain video only. Choose to continue with that ID, add best audio using `247+bestaudio/247`, or cancel. You can still enter a complete format expression yourself to skip this prompt.

Without `-f/--format`, whytea keeps its original default selector `398+bestaudio/398`. If that selector is unavailable for a particular video, list the available formats and choose an override with `-f/--format`.

## Local Firefox library

Start the local web server:

```bash
python web.py
```

Open Firefox at:

```text
http://127.0.0.1:8765
```

The simple page shows the downloaded videos, channel, upload date, and watched status. Videos play directly from the local disk using Firefox's normal HTML5 video player.

A video is automatically marked watched when playback reaches the end. You can also manually mark videos watched/unwatched. The state is saved in `watch_state.json`, so it survives restarting the server and does not depend on browser history.

The server binds to `127.0.0.1`, so it is only accessible from this computer by default.

## Browser authentication

For downloads requiring your logged-in YouTube session, configure yt-dlp browser cookies in `config.json`, for example:

```json
"cookies_from_browser": "firefox"
```

Do not put account cookies into this public repository.

## Proxy

Use a SOCKS5 proxy for downloads. If you pass `--proxy` without an address, it uses `127.0.0.1:10808`:

```bash
python whytea.py --proxy
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID" --proxy
```

To use a different proxy, provide `HOST:PORT`:

```bash
python whytea.py --proxy 192.168.1.100:9050
python whytea.py sync --proxy 192.168.1.100:9050
python whytea.py video "https://www.youtube.com/watch?v=VIDEO_ID" --proxy 192.168.1.100:9050
```

A bare `HOST:PORT` is interpreted as a SOCKS5 proxy. You can also pass a complete proxy URL, such as `socks5://192.168.1.100:9050`.

## Continuous downloading

```bash
python whytea.py --watch
```

Check every 10 minutes:

```bash
python whytea.py --watch --interval 600
```

The downloader and browser library can run independently: the downloader updates `videos/`, while Firefox reads the same directory through `web.py`.

## Offline-first behavior

- downloads resume when possible
- failed sources do not stop the whole run
- yt-dlp's archive prevents duplicates
- media fragments are retried
- yt-dlp metadata is stored so the library can display title/channel/date
- watched state persists locally
- the browser library works entirely from local files
