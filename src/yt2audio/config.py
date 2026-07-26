"""Caller-supplied configuration for extraction/batch/spotify flows."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DownloadKind = Literal["audio", "video"]


@dataclass
class ExtractionConfig:
    output_dir: Path = Path("./downloads")

    download_kind: DownloadKind = "audio"

    # Used only when download_kind == "audio"
    audio_format: str = "mp3"
    audio_bitrate_kbps: int = 192

    # Used only when download_kind == "video"
    video_format: str = "mp4"

    max_concurrent: int = 3
    skip_existing: bool = True
    filename_template: str = "%(title)s [%(id)s].%(ext)s"
    rate_limit: str | None = None
    retries: int = 3
    cookies_file: Path | None = None
    proxy: str | None = None
    quiet: bool = True
    restrict_filenames: bool = False

    # Spotify-matching only
    match_min_confidence: float = 0.55
    search_results_to_consider: int = 5

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if self.cookies_file is not None:
            self.cookies_file = Path(self.cookies_file)
