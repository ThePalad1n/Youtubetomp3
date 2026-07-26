"""Thin wrapper around yt_dlp.YoutubeDL.

This is the ONLY module in the package that imports yt_dlp or shells out to
ffmpeg. Every other module depends on the `YtdlpClient` interface (4 methods
below) rather than on yt_dlp directly, so tests can substitute a fake and run
without any network access.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yt_dlp

from yt2audio.config import ExtractionConfig
from yt2audio.logging_setup import logger


def check_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class _YtdlpLoggerAdapter:
    """Routes yt-dlp's own logging into the yt2audio logger instead of stdout."""

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            logger.debug(msg)
        else:
            logger.info(msg)

    def info(self, msg: str) -> None:
        logger.info(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)


class YtdlpClient:
    """Thin, injectable wrapper. See module docstring for why this exists."""

    def __init__(self, config: ExtractionConfig):
        self._config = config

    def _build_opts(self, extra_opts: dict | None = None) -> dict:
        config = self._config
        opts: dict[str, Any] = {
            "outtmpl": str(config.output_dir / config.filename_template),
            "noplaylist": True,
            "quiet": config.quiet,
            "no_warnings": config.quiet,
            "retries": config.retries,
            "ratelimit": _parse_rate_limit(config.rate_limit),
            "ignoreerrors": False,
            "overwrites": not config.skip_existing,
            "restrictfilenames": config.restrict_filenames,
            "logger": _YtdlpLoggerAdapter(),
        }
        if config.download_kind == "video":
            opts["format"] = "bestvideo+bestaudio/best"
            opts["merge_output_format"] = config.video_format
        else:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": config.audio_format,
                    "preferredquality": str(config.audio_bitrate_kbps),
                }
            ]
        if config.cookies_file is not None:
            opts["cookiefile"] = str(config.cookies_file)
        if config.proxy is not None:
            opts["proxy"] = config.proxy
        if config.no_cache:
            opts["cachedir"] = False
        if extra_opts:
            opts.update(extra_opts)
        return opts

    def probe(self, url: str) -> dict:
        """Metadata-only lookup (no download)."""
        opts = self._build_opts({"noplaylist": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download_single(self, url: str) -> dict:
        """Downloads (+ postprocesses) a single item and returns its info_dict,
        with the resolved final filepath available via `resolved_filepath`.
        """
        opts = self._build_opts({"noplaylist": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            info["_resolved_filepath"] = self._resolve_filepath(ydl, info)
            return info

    def expand_playlist(self, playlist_url: str) -> list[dict]:
        """Cheaply enumerates a playlist's entries (id/url/title) without
        resolving each video's full metadata - used to fan out into
        individual `download_single` calls with per-item error isolation.
        """
        opts = self._build_opts({"extract_flat": "in_playlist", "noplaylist": False})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        return list(info.get("entries") or [])

    def search(self, query: str, n: int) -> list[dict]:
        """Returns up to n candidate info_dicts (title/duration/id/uploader)
        for the given free-text search query, via yt-dlp's ytsearch pseudo-URL.
        Used only by the Spotify-matching flow.
        """
        opts = self._build_opts({"noplaylist": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
        return list(info.get("entries") or [])

    @staticmethod
    def _resolve_filepath(ydl: yt_dlp.YoutubeDL, info: dict) -> Path | None:
        requested = info.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            return Path(requested[0]["filepath"])
        # Fallback for older yt-dlp versions / shapes where requested_downloads
        # isn't populated: derive from the template and swap in the
        # postprocessor's final extension when audio extraction changed it.
        prepared = Path(ydl.prepare_filename(info))
        pp_ext = (info.get("requested_downloads") or [{}])[0].get("ext") if requested else None
        final_ext = pp_ext or info.get("ext")
        if final_ext and prepared.suffix.lstrip(".") != final_ext:
            prepared = prepared.with_suffix(f".{final_ext}")
        return prepared


def _parse_rate_limit(rate_limit: str | None) -> int | None:
    """Converts a human string like '1M' / '500K' / '2048' into bytes/sec for
    yt-dlp's `ratelimit` option (which expects a plain int).
    """
    if not rate_limit:
        return None
    rate_limit = rate_limit.strip().upper()
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3}
    if rate_limit[-1] in multipliers:
        return int(float(rate_limit[:-1]) * multipliers[rate_limit[-1]])
    return int(rate_limit)
