"""Glues together: Spotify export parsing -> YouTube search -> match scoring
-> audio download. Always downloads audio (config.download_kind is forced to
"audio" here, regardless of the caller's setting) since this flow exists to
resolve a *music track*, not a video.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from yt2audio.config import ExtractionConfig
from yt2audio.extractor import download_one
from yt2audio.logging_setup import logger
from yt2audio.models import (
    BatchResult,
    ExtractionResult,
    ExtractionStatus,
    SourceKind,
    SpotifyTrack,
    TrackSource,
)
from yt2audio.spotify.matcher import (
    SearchCandidate,
    build_search_query,
    select_best_match,
)
from yt2audio.spotify.parser import parse_spotify_export
from yt2audio.ytdlp_client import YtdlpClient


def extract_from_spotify_export(
    export_source: str | Path,
    config: ExtractionConfig,
    client: YtdlpClient | None = None,
) -> BatchResult:
    tracks = parse_spotify_export(export_source)
    audio_config = replace(config, download_kind="audio")
    client = client or YtdlpClient(audio_config)

    results: list[ExtractionResult] = [None] * len(tracks)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=max(1, audio_config.max_concurrent)) as pool:
        futures = {
            pool.submit(_match_and_download, client, audio_config, track): position
            for position, track in enumerate(tracks)
        }
        for future, position in futures.items():
            results[position] = future.result()
    return BatchResult(results=results)


def _match_and_download(
    client: YtdlpClient, config: ExtractionConfig, track: SpotifyTrack
) -> ExtractionResult:
    source = TrackSource(kind=SourceKind.SPOTIFY_TRACK, spotify_track=track)
    query = build_search_query(track)
    try:
        raw_candidates = client.search(query, config.search_results_to_consider)
    except Exception as exc:
        logger.warning("Search failed for Spotify track %r: %s", track.track_name, exc)
        return ExtractionResult(
            source=source,
            status=ExtractionStatus.FAILED,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    candidates = [
        SearchCandidate(
            video_id=entry.get("id", ""),
            title=entry.get("title") or "",
            duration_seconds=entry.get("duration"),
            uploader=entry.get("uploader"),
            webpage_url=entry.get("webpage_url") or entry.get("url"),
        )
        for entry in raw_candidates
        if entry.get("id")
    ]

    best, score = select_best_match(track, candidates, config.match_min_confidence)
    if best is None:
        return ExtractionResult(
            source=source,
            status=ExtractionStatus.NO_MATCH,
            match_confidence=score,
            error_message=f"No candidate cleared confidence threshold {config.match_min_confidence}",
        )

    download_url = best.webpage_url or f"https://www.youtube.com/watch?v={best.video_id}"
    result = download_one(client, config, download_url, source)
    result.match_confidence = score
    if result.resolved_artist is None:
        result.resolved_artist = track.artist_name or result.resolved_artist
    return result
