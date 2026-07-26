"""Batch processing over an explicit list of URLs or a pasted text blob of URLs.

Runs items concurrently (bounded by config.max_concurrent) using a thread
pool - yt-dlp/ffmpeg release the GIL during network I/O and subprocess work,
so threads are sufficient without asyncio/multiprocessing complexity.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from yt2audio.config import ExtractionConfig
from yt2audio.extractor import download_one
from yt2audio.models import (
    BatchResult,
    ExtractionResult,
    SourceKind,
    TrackSource,
)
from yt2audio.url_utils import parse_url_list
from yt2audio.ytdlp_client import YtdlpClient


def extract_from_url_list(
    urls: list[str], config: ExtractionConfig, client: YtdlpClient | None = None
) -> BatchResult:
    """Downloads each URL in `urls` independently; one failure doesn't stop the rest."""
    client = client or YtdlpClient(config)
    results: list[ExtractionResult] = []
    with ThreadPoolExecutor(max_workers=max(1, config.max_concurrent)) as pool:
        futures = [
            pool.submit(
                download_one,
                client,
                config,
                url,
                TrackSource(kind=SourceKind.DIRECT_URL, original_url=url),
            )
            for url in urls
        ]
        for future in futures:
            results.append(future.result())
    return BatchResult(results=results)


def extract_from_text(
    text_or_path: str | Path,
    config: ExtractionConfig,
    client: YtdlpClient | None = None,
) -> BatchResult:
    """Accepts either a raw text blob of URLs or a path to a file containing one,
    and processes every URL found in it as a batch.
    """
    path = Path(text_or_path)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = str(text_or_path)
    urls = parse_url_list(text)
    return extract_from_url_list(urls, config, client=client)
