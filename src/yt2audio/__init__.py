"""yt2audio: reusable core for extracting audio/video from yt-dlp-supported
sites, including playlist batches and Spotify-export-to-YouTube matching.
"""
from yt2audio.batch import extract_from_text, extract_from_url_list
from yt2audio.config import ExtractionConfig
from yt2audio.errors import (
    ConfigError,
    ExtractionFailedError,
    UnsupportedURLError,
    Yt2AudioError,
)
from yt2audio.extractor import extract_playlist, extract_single
from yt2audio.models import (
    BatchResult,
    ExtractionResult,
    ExtractionStatus,
    SourceKind,
    SpotifyTrack,
    TrackSource,
)
from yt2audio.spotify.parser import parse_spotify_export
from yt2audio.spotify_flow import extract_from_spotify_export
from yt2audio.ytdlp_client import check_ffmpeg_available

__all__ = [
    "BatchResult",
    "ConfigError",
    "ExtractionConfig",
    "ExtractionFailedError",
    "ExtractionResult",
    "ExtractionStatus",
    "SourceKind",
    "SpotifyTrack",
    "TrackSource",
    "UnsupportedURLError",
    "Yt2AudioError",
    "check_ffmpeg_available",
    "extract_from_spotify_export",
    "extract_from_text",
    "extract_from_url_list",
    "extract_playlist",
    "extract_single",
    "parse_spotify_export",
]
