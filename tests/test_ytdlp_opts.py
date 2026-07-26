"""Covers YtdlpClient._build_opts, the one place config turns into yt-dlp
options. Importing yt_dlp is fine here: _build_opts touches no network.
"""
from __future__ import annotations

from pathlib import Path

from yt2audio.config import ExtractionConfig
from yt2audio.ytdlp_client import YtdlpClient


def _opts(**kwargs) -> dict:
    return YtdlpClient(ExtractionConfig(**kwargs))._build_opts()


def test_audio_opts_set_extract_audio_postprocessor() -> None:
    opts = _opts(download_kind="audio", audio_format="mp3", audio_bitrate_kbps=192)
    assert opts["format"] == "bestaudio/best"
    pp = opts["postprocessors"][0]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "192"


def test_video_opts_merge_to_mp4() -> None:
    opts = _opts(download_kind="video", video_format="mp4")
    assert opts["format"] == "bestvideo+bestaudio/best"
    assert opts["merge_output_format"] == "mp4"
    assert "postprocessors" not in opts


def test_proxy_and_cookies_only_present_when_set() -> None:
    bare = _opts()
    assert "proxy" not in bare
    assert "cookiefile" not in bare

    wired = _opts(proxy="socks5://127.0.0.1:1080", cookies_file=Path("cookies.txt"))
    assert wired["proxy"] == "socks5://127.0.0.1:1080"
    assert wired["cookiefile"] == "cookies.txt"


def test_no_cache_disables_cachedir() -> None:
    assert "cachedir" not in _opts(no_cache=False)
    assert _opts(no_cache=True)["cachedir"] is False
