"""Result and data models shared across yt2audio's extraction flows."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NO_MATCH = "no_match"


class SourceKind(str, Enum):
    DIRECT_URL = "direct_url"
    PLAYLIST_ENTRY = "playlist_entry"
    SPOTIFY_TRACK = "spotify_track"


@dataclass(frozen=True)
class SpotifyTrack:
    track_name: str
    artist_name: str
    album_name: str | None = None
    duration_ms: int | None = None
    track_uri: str | None = None
    raw_line: str | None = None


@dataclass(frozen=True)
class TrackSource:
    """Describes where a job item came from, for traceability in results."""

    kind: SourceKind
    original_url: str | None = None
    playlist_url: str | None = None
    playlist_index: int | None = None
    spotify_track: SpotifyTrack | None = None


@dataclass
class ExtractionResult:
    source: TrackSource
    status: ExtractionStatus
    resolved_title: str | None = None
    resolved_artist: str | None = None
    output_path: Path | None = None
    duration_seconds: float | None = None
    media_format: str | None = None
    file_size_bytes: int | None = None
    match_confidence: float | None = None
    error_message: str | None = None
    error_type: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class BatchResult:
    """Aggregate wrapper a caller can hand straight to a 'build zip / list files' step."""

    results: list[ExtractionResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.status == ExtractionStatus.SUCCESS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == ExtractionStatus.FAILED)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == ExtractionStatus.SKIPPED)

    @property
    def no_match(self) -> int:
        return sum(1 for r in self.results if r.status == ExtractionStatus.NO_MATCH)

    @property
    def output_paths(self) -> list[Path]:
        return [r.output_path for r in self.results if r.output_path is not None]
