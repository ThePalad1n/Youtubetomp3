# Youtubetomp3 / `yt2audio`

A reusable Python core library for extracting audio (or video) from
[yt-dlp](https://github.com/yt-dlp/yt-dlp)-supported sites - YouTube,
SoundCloud, Vimeo, and 1000+ others - including single URLs, playlists, plain
text lists of URLs, and Spotify playlist exports (matched against YouTube,
since Spotify's own audio can't be downloaded).

It's designed to be imported into another project (a web backend, a
standalone service on a Raspberry Pi, etc.) rather than used as a
CLI-first/web-first tool - the CLI included here is a thin wrapper for local
testing.

## Requirements

- Python >= 3.10
- [ffmpeg](https://ffmpeg.org/) on your `PATH`, used by yt-dlp to extract/remux
  audio and video. Windows: `winget install --id Gyan.FFmpeg`. Debian/Ubuntu:
  `apt-get install ffmpeg`. macOS: `brew install ffmpeg`.

## Install

```bash
pip install -e .            # core library only
pip install -e ".[cli]"     # + the `yt2audio` CLI
pip install -e ".[dev]"     # + test/lint tooling
```

## Local use on Windows

For running this on a Windows PC as a CLI, there are two scripts so you don't
have to touch a virtual environment by hand:

1. `setup.bat`, run once. It finds Python, creates a `.venv`, installs the CLI
   into it, and tells you whether ffmpeg is on your `PATH`. If ffmpeg is
   missing it prints the `winget install --id Gyan.FFmpeg` line; run that,
   open a new terminal so `PATH` refreshes, then re-run `setup.bat`.
2. `run.bat`, for every download. It calls the CLI out of the `.venv`, so the
   arguments are the same ones documented below:

```bat
run.bat single "https://www.youtube.com/watch?v=..." --format mp3
run.bat single "https://www.youtube.com/watch?v=..." --video
run.bat batch urls.txt --no-cache
```

Turn the VPN on before you download. A whole-machine VPN routes yt-dlp's fetch
without any flag, so the request to Google's CDN leaves the VPN's egress IP
instead of your home connection's. If you'd rather route one download through
a proxy instead of the whole machine, pass `--proxy socks5://127.0.0.1:1080`
(or whatever your proxy is). Add `--no-cache` to stop yt-dlp writing its
extractor cache under `%APPDATA%\yt-dlp`, so a run leaves nothing on disk once
the file is moved out of `downloads`.

## Library usage

```python
from yt2audio import ExtractionConfig, extract_single, extract_playlist
from yt2audio import extract_from_url_list, extract_from_text, extract_from_spotify_export

config = ExtractionConfig(output_dir="./downloads", audio_format="mp3")

# Single URL (YouTube, SoundCloud, Vimeo, ...)
result = extract_single("https://www.youtube.com/watch?v=...", config)

# Full playlist
results = extract_playlist("https://www.youtube.com/playlist?list=...", config)

# Arbitrary list/text blob of URLs
batch = extract_from_url_list(["https://...", "https://..."], config)
batch = extract_from_text("path/to/urls.txt", config)  # or a raw text blob

# Video instead of audio
video_config = ExtractionConfig(output_dir="./downloads", download_kind="video")
extract_single("https://www.youtube.com/watch?v=...", video_config)

# Spotify playlist export -> matched & downloaded from YouTube (always audio)
spotify_batch = extract_from_spotify_export("playlist_export.csv", config)
```

Every call returns `ExtractionResult` (single item) or `BatchResult`
(collections) dataclasses - never raises for per-item failures. Check
`result.status` (`SUCCESS` / `FAILED` / `SKIPPED` / `NO_MATCH`) and
`result.output_path` / `result.error_message` as needed. `BatchResult` also
exposes `.succeeded` / `.failed` / `.skipped` / `.no_match` counts and
`.output_paths` for building a zip or a direct-download response.

### Spotify export format

Since Spotify's own audio can't be extracted (licensing), only playlist
*metadata* is read, and each track is searched for and matched on YouTube.
Two input shapes are auto-detected:

- **Exportify-style CSV** (the common third-party Spotify-playlist-export
  tool) with `Track Name` / `Artist Name(s)` / `Album Name` / `Track Duration
  (ms)` columns (header names are matched loosely, since they've drifted
  across Exportify versions).
- **Plain text**, one track per line: `Artist - Title` (optionally prefixed
  with a track number, e.g. `3. Artist - Title`).

Matching uses fuzzy title similarity + duration closeness + a penalty for
"live"/"cover"/"nightcore"/etc. in the candidate title when that word isn't
in the original track name. A track with no confident match
(`ExtractionConfig.match_min_confidence`, default `0.55`) comes back as
`NO_MATCH` rather than downloading something potentially wrong.

## CLI (for local testing)

```bash
yt2audio single <URL> [--format mp3] [--video] [--output-dir DIR]
yt2audio playlist <PLAYLIST_URL> [--concurrency 3]
yt2audio batch <FILE_OF_URLS_OR_RAW_TEXT>
yt2audio spotify <EXPORT_FILE> [--min-confidence 0.55]
```

Flags on every command:

- `--proxy socks5://host:port` routes the fetch through a proxy. Leave it off
  when a whole-machine VPN is already up.
- `--cookies path\to\cookies.txt` passes a Netscape-format cookies file for
  videos that refuse to serve a stream without sign-in.
- `--no-cache` disables yt-dlp's on-disk cache for that run.

Add `--json` to any command to print the full structured results instead of
a summary, which is useful for scripting against this as if it were already
the API of an integrating service.

## Testing

```bash
pytest        # unit tests only (default) - no network access required
mypy src
ruff check src tests
```

Unit tests exercise URL parsing, Spotify export parsing, match scoring, and
all orchestration logic (single/playlist/batch/Spotify flows) against a fake
`YtdlpClient` test double, so they run without touching the network or
yt-dlp. Tests marked `@pytest.mark.integration` (excluded by default) hit
real sites and are meant to be run manually when verifying against a live
yt-dlp version.

## Design notes

- `yt2audio.ytdlp_client` is the only module that imports `yt_dlp` or shells
  out to ffmpeg; every other module depends on its narrow interface
  (`probe` / `download_single` / `expand_playlist` / `search`), which is
  injected so it can be swapped for a test double.
- Filenames include the source's video ID, and `ExtractionConfig.skip_existing`
  (default on) avoids re-downloading files that already exist - so a batch or
  playlist job that gets interrupted can simply be re-run to resume.
- Per-item failures (private videos, geo-blocking, no Spotify match, etc.)
  never raise - they come back as `ExtractionResult(status=FAILED/NO_MATCH, ...)`
  so one bad item never aborts a larger batch.
