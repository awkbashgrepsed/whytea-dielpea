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

Then download:

```bash
python whytea.py
```

The default is the newest **5 videos per source**. Change `latest_per_source` in `config.json` for more or fewer.

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
