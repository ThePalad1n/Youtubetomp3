"""High-level single-URL and playlist extraction orchestration.

Depends only on the YtdlpClient *interface* (probe/download_single/
expand_playlist/search), injected by the caller - never imports yt_dlp
itself, so tests can substitute a fake client and run without network access.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from yt2audio.config import ExtractionConfig
from yt2audio.logging_setup import logger
from yt2audio.models import ExtractionResult, ExtractionStatus, SourceKind, TrackSource
from yt2audio.ytdlp_client import YtdlpClient


def extract_single(
    url: str, config: ExtractionConfig, client: YtdlpClient | None = None
) -> ExtractionResult:
    """Extracts audio (or video, per config.download_kind) from a single URL."""
    client = client or YtdlpClient(config)
    source = TrackSource(kind=SourceKind.DIRECT_URL, original_url=url)
    return download_one(client, config, url, source)


def extract_playlist(
    playlist_url: str, config: ExtractionConfig, client: YtdlpClient | None = None
) -> list[ExtractionResult]:
    """Extracts audio/video for every entry in a playlist.

    Entries are enumerated cheaply first (no per-video resolution), then each
    is downloaded through the same isolated single-item path so one bad video
    can't abort the rest of the playlist.
    """
    client = client or YtdlpClient(config)
    try:
        entries = client.expand_playlist(playlist_url)
    except Exception as exc:  # structural failure enumerating the playlist itself
        logger.error("Failed to expand playlist %s: %s", playlist_url, exc)
        source = TrackSource(kind=SourceKind.PLAYLIST_ENTRY, playlist_url=playlist_url)
        return [
            ExtractionResult(
                source=source,
                status=ExtractionStatus.FAILED,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        ]

    jobs: list[tuple[TrackSource, str | None]] = []
    for index, entry in enumerate(entries):
        entry_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
        source = TrackSource(
            kind=SourceKind.PLAYLIST_ENTRY,
            original_url=entry_url,
            playlist_url=playlist_url,
            playlist_index=index,
        )
        jobs.append((source, entry_url))

    results: list[ExtractionResult] = [None] * len(jobs)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=max(1, config.max_concurrent)) as pool:
        futures = {}
        for position, (source, entry_url) in enumerate(jobs):
            if not entry_url:
                results[position] = ExtractionResult(
                    source=source,
                    status=ExtractionStatus.FAILED,
                    error_type="MissingEntryURL",
                    error_message=f"Playlist entry {source.playlist_index} had no resolvable URL/id",
                )
                continue
            futures[pool.submit(download_one, client, config, entry_url, source)] = position
        for future, position in futures.items():
            results[position] = future.result()
    return results


def download_one(
    client: YtdlpClient, config: ExtractionConfig, url: str, source: TrackSource
) -> ExtractionResult:
    try:
        info = client.download_single(url)
    except Exception as exc:
        logger.warning("Extraction failed for %s: %s", url, exc)
        return ExtractionResult(
            source=source,
            status=ExtractionStatus.FAILED,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
    return _result_from_info(source, config, info)


def _result_from_info(
    source: TrackSource, config: ExtractionConfig, info: dict
) -> ExtractionResult:
    output_path = info.get("_resolved_filepath")
    if output_path is not None:
        output_path = Path(output_path)
    file_size = None
    if output_path is not None and output_path.exists():
        file_size = output_path.stat().st_size

    media_format = config.video_format if config.download_kind == "video" else config.audio_format

    # yt-dlp sets __real_download=False when it found the output file already
    # on disk and skipped re-downloading it (our skip_existing/overwrites=False
    # config) - surface that distinction rather than reporting it as a fresh
    # SUCCESS, so callers can tell resumed runs apart from new work.
    status = (
        ExtractionStatus.SKIPPED
        if info.get("__real_download") is False
        else ExtractionStatus.SUCCESS
    )

    return ExtractionResult(
        source=source,
        status=status,
        resolved_title=info.get("title"),
        resolved_artist=info.get("artist") or info.get("uploader"),
        output_path=output_path,
        duration_seconds=info.get("duration"),
        media_format=media_format,
        file_size_bytes=file_size,
        extra={"id": info.get("id"), "webpage_url": info.get("webpage_url")},
    )
