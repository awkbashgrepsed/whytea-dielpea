# whytea-dielpea

An offline YouTube downloader built around the **system-installed `yt-dlp`** command.

The idea is simple: put the YouTube channels you care about in `sources.txt`, run the program while the connection is available, and it keeps a local copy of their newest videos. You can then watch the downloaded files without YouTube, a VPN, or an internet connection.

## How it works

```text
sources.txt
    |
    v
whytea.py
    |
    v
system yt-dlp
    |
    +--> latest videos from Channel A
    +--> latest videos from Channel B
    +--> latest videos from Channel C
    |
    v
videos/<channel>/
```

Each source is checked independently. yt-dlp's download archive (`archive.txt`) records videos that have already been downloaded, so running the program again does **not** redownload the same videos.

Downloads are resumable and yt-dlp is configured with retries and fragment retries so temporary connection failures are much less painful.

## Requirements

- Python 3.9+
- `yt-dlp` installed system-wide and available as `yt-dlp` in `PATH`
- `ffmpeg` recommended/required for merging separate video and audio streams

Verify:

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

You can use channel URLs, including the `/videos` page. One source per line.

Then run:

```bash
python whytea.py
```

The default is the newest **5 videos per source**. Change `latest_per_source` in `config.json` if you want more or fewer.

## Browser authentication

For channels/videos that require your logged-in YouTube session, `yt-dlp` can import cookies directly from a supported browser. Set this in `config.json`, for example:

```json
"cookies_from_browser": "firefox"
```

Other supported browser names can be used according to your yt-dlp installation.

Do not put a `cookies.txt` containing your account session into this public repository.

## Continuous mode

To keep checking periodically:

```bash
python whytea.py --watch
```

The default interval is 30 minutes. For example, check every 10 minutes:

```bash
python whytea.py --watch --interval 600
```

## Check installation

```bash
python whytea.py --check
```

## Configuration

`config.json` controls the downloader:

- `download_dir`: local video library directory
- `quality`: yt-dlp format selector; default is up to 1080p
- `latest_per_source`: number of newest playlist entries examined per channel
- `sleep_between_sources`: delay between channels
- `retries`: network retries
- `fragment_retries`: retries for individual media fragments
- `no_shorts`: skip very short videos and live streams
- `cookies_from_browser`: optional browser name for authenticated downloads
- `extra_args`: additional yt-dlp arguments

## Offline-first behavior

The downloader is intentionally designed to survive unreliable connectivity:

- downloads resume when possible
- failed sources do not stop the whole run
- yt-dlp's archive prevents duplicate downloads
- individual media fragments are retried
- the program can be run repeatedly without needing to track downloaded videos manually

The downloaded files are organized as:

```text
videos/
└── Channel Name/
    ├── 20260825 - Video title [videoid].mp4
    └── ...
```
