"""Thin CLI wrapping the public library API - a secondary artifact for local
testing/dev-verification, not the primary interface (see README).
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import click

from yt2audio.batch import extract_from_text
from yt2audio.config import ExtractionConfig
from yt2audio.extractor import extract_playlist, extract_single
from yt2audio.models import BatchResult, ExtractionResult
from yt2audio.spotify_flow import extract_from_spotify_export
from yt2audio.ytdlp_client import check_ffmpeg_available


def _result_to_dict(result: ExtractionResult) -> dict:
    data = dataclasses.asdict(result)
    if data.get("output_path") is not None:
        data["output_path"] = str(data["output_path"])
    return data


def _print_summary(results: list[ExtractionResult], as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps([_result_to_dict(r) for r in results], indent=2, default=str))
        return
    succeeded = sum(1 for r in results if r.status.value == "success")
    failed = [r for r in results if r.status.value == "failed"]
    skipped = sum(1 for r in results if r.status.value == "skipped")
    no_match = sum(1 for r in results if r.status.value == "no_match")
    click.echo(
        f"Total: {len(results)}  Succeeded: {succeeded}  Skipped: {skipped}  "
        f"No match: {no_match}  Failed: {len(failed)}"
    )
    for r in failed:
        label = r.resolved_title or r.source.original_url or "(unknown)"
        click.echo(f"  FAILED: {label} - {r.error_type}: {r.error_message}")


def _common_options(func):
    func = click.option("--output-dir", default="./downloads", help="Directory to write files to.")(func)
    func = click.option("--format", "audio_format", default="mp3", help="Audio format (mp3, m4a, opus, ...).")(func)
    func = click.option("--bitrate", default=192, type=int, help="Audio bitrate in kbps.")(func)
    func = click.option("--video", is_flag=True, default=False, help="Download mp4 video instead of audio.")(func)
    func = click.option("--concurrency", default=3, type=int, help="Max concurrent downloads for batch/playlist.")(func)
    func = click.option("--json", "as_json", is_flag=True, default=False, help="Print results as JSON.")(func)
    return func


def _build_config(output_dir: str, audio_format: str, bitrate: int, video: bool, concurrency: int, **extra) -> ExtractionConfig:
    return ExtractionConfig(
        output_dir=Path(output_dir),
        download_kind="video" if video else "audio",
        audio_format=audio_format,
        audio_bitrate_kbps=bitrate,
        max_concurrent=concurrency,
        **extra,
    )


@click.group()
def main() -> None:
    """yt2audio: extract audio/video from yt-dlp-supported sites."""
    if not check_ffmpeg_available():
        click.echo("Warning: ffmpeg was not found on PATH. Install it before downloading.", err=True)


@main.command()
@click.argument("url")
@_common_options
def single(url: str, output_dir: str, audio_format: str, bitrate: int, video: bool, concurrency: int, as_json: bool) -> None:
    """Extract audio/video from a single URL."""
    config = _build_config(output_dir, audio_format, bitrate, video, concurrency)
    result = extract_single(url, config)
    _print_summary([result], as_json)
    sys.exit(0 if result.status.value in ("success", "skipped") else 1)


@main.command()
@click.argument("playlist_url")
@_common_options
def playlist(playlist_url: str, output_dir: str, audio_format: str, bitrate: int, video: bool, concurrency: int, as_json: bool) -> None:
    """Extract audio/video for every item in a playlist URL."""
    config = _build_config(output_dir, audio_format, bitrate, video, concurrency)
    results = extract_playlist(playlist_url, config)
    _print_summary(results, as_json)


@main.command()
@click.argument("source")
@_common_options
def batch(source: str, output_dir: str, audio_format: str, bitrate: int, video: bool, concurrency: int, as_json: bool) -> None:
    """Extract audio/video for a text file (or blob) of URLs, one per line."""
    config = _build_config(output_dir, audio_format, bitrate, video, concurrency)
    result: BatchResult = extract_from_text(source, config)
    _print_summary(result.results, as_json)


@main.command()
@click.argument("export_file")
@click.option("--output-dir", default="./downloads")
@click.option("--format", "audio_format", default="mp3")
@click.option("--bitrate", default=192, type=int)
@click.option("--concurrency", default=3, type=int)
@click.option("--min-confidence", default=0.55, type=float, help="Minimum match confidence to accept a download.")
@click.option("--json", "as_json", is_flag=True, default=False)
def spotify(
    export_file: str,
    output_dir: str,
    audio_format: str,
    bitrate: int,
    concurrency: int,
    min_confidence: float,
    as_json: bool,
) -> None:
    """Match tracks from a Spotify playlist export (CSV or text) on YouTube and download audio."""
    config = _build_config(
        output_dir, audio_format, bitrate, False, concurrency, match_min_confidence=min_confidence
    )
    result = extract_from_spotify_export(export_file, config)
    _print_summary(result.results, as_json)


if __name__ == "__main__":
    main()
