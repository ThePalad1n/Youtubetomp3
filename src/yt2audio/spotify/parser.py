"""Parses a Spotify playlist export into SpotifyTrack objects.

Spotify's own API/exports don't hand out playable audio (licensing), so this
only extracts *metadata* (track/artist/album/duration) - yt2audio.spotify_flow
then searches YouTube for a matching upload of each track.

Two input shapes are auto-detected:
  1. Exportify-style CSV (the most common third-party Spotify-playlist-export
     tool) - header names have drifted across Exportify versions, so columns
     are matched via a case-insensitive alias map rather than one fixed set.
  2. Plain text, one track per line, formatted "Artist - Title" (optionally
     prefixed with a track number like "3. " or "3) ").
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from yt2audio.logging_setup import logger
from yt2audio.models import SpotifyTrack

_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "track_name": ("track name", "track name(s)", "name", "title", "song"),
    "artist_name": ("artist name(s)", "artist name", "artist", "artist(s)"),
    "album_name": ("album name", "album"),
    "duration_ms": ("track duration (ms)", "duration (ms)", "duration_ms"),
    "track_uri": ("track uri", "uri", "spotify id", "spotify uri"),
}

_LEADING_INDEX_RE = re.compile(r"^\s*\d+[.)]\s*")
_DASH_SPLIT_RE = re.compile(r"\s+[-–—]\s+")  # hyphen, en-dash, em-dash, spaced


def parse_spotify_export(source: str | Path) -> list[SpotifyTrack]:
    """Auto-detects Exportify CSV vs. plain "Artist - Title" text and parses it."""
    path = Path(source) if isinstance(source, (str, Path)) else None
    if path is not None and path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8-sig")
        looks_like_csv = path.suffix.lower() == ".csv" or _sniff_csv(text)
    else:
        text = str(source)
        looks_like_csv = _sniff_csv(text)

    if looks_like_csv:
        tracks = _parse_csv(text)
        if tracks:
            return tracks
        logger.warning("Input looked like CSV but no rows parsed; falling back to plain-text parsing")

    return _parse_plain_text(text)


def _sniff_csv(text: str) -> bool:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    if "," not in first_line:
        return False
    header_fields = {field.strip().lower() for field in first_line.split(",")}
    for aliases in _HEADER_ALIASES.values():
        if header_fields & set(aliases):
            return True
    return False


def _resolve_headers(fieldnames: list[str]) -> dict[str, str]:
    """Maps our canonical field names -> the actual header string present in this file."""
    lower_to_actual = {name.strip().lower(): name for name in fieldnames}
    resolved: dict[str, str] = {}
    for canonical, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in lower_to_actual:
                resolved[canonical] = lower_to_actual[alias]
                break
    return resolved


def _parse_csv(text: str) -> list[SpotifyTrack]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    headers = _resolve_headers(list(reader.fieldnames))
    if "track_name" not in headers or "artist_name" not in headers:
        logger.warning("CSV missing recognizable track/artist columns: %s", reader.fieldnames)
        return []

    tracks: list[SpotifyTrack] = []
    for row in reader:
        track_name = (row.get(headers["track_name"]) or "").strip()
        artist_name = (row.get(headers["artist_name"]) or "").strip()
        if not track_name:
            continue
        duration_ms: int | None = None
        if "duration_ms" in headers:
            raw_duration = (row.get(headers["duration_ms"]) or "").strip()
            if raw_duration.isdigit():
                duration_ms = int(raw_duration)
        tracks.append(
            SpotifyTrack(
                track_name=track_name,
                artist_name=artist_name,
                album_name=(row.get(headers.get("album_name", ""), "") or "").strip() or None,
                duration_ms=duration_ms,
                track_uri=(row.get(headers.get("track_uri", ""), "") or "").strip() or None,
                raw_line=",".join(row.values()),
            )
        )
    return tracks


def _parse_plain_text(text: str) -> list[SpotifyTrack]:
    tracks: list[SpotifyTrack] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = _LEADING_INDEX_RE.sub("", line)
        parts = _DASH_SPLIT_RE.split(line, maxsplit=1)
        if len(parts) == 2:
            artist_name, track_name = parts[0].strip(), parts[1].strip()
        else:
            logger.warning("Could not split artist/title from line, using raw text: %r", raw_line)
            artist_name, track_name = "", line
        tracks.append(SpotifyTrack(track_name=track_name, artist_name=artist_name, raw_line=raw_line))
    return tracks
