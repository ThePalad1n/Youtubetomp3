from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from yt2audio.config import ExtractionConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeYtdlpClient:
    """Test double for YtdlpClient - implements the same 4 methods, returns
    canned data instead of touching the network, so orchestration logic
    (extractor/batch/spotify_flow) is testable without yt-dlp or network access.
    """

    def __init__(
        self,
        config: ExtractionConfig,
        *,
        download_results: dict[str, dict] | None = None,
        download_errors: dict[str, Exception] | None = None,
        playlist_entries: list[dict] | None = None,
        search_results: dict[str, list[dict]] | None = None,
        write_files: bool = True,
    ):
        self._config = config
        self.download_results = download_results or {}
        self.download_errors = download_errors or {}
        self.playlist_entries = playlist_entries or []
        self.search_results = search_results or {}
        self.write_files = write_files
        self.download_calls: list[str] = []
        self.search_calls: list[tuple[str, int]] = []

    def probe(self, url: str) -> dict:
        return self.download_results.get(url, {"id": "unknown", "title": "unknown"})

    def download_single(self, url: str) -> dict:
        self.download_calls.append(url)
        if url in self.download_errors:
            raise self.download_errors[url]
        info = dict(self.download_results.get(url, {"id": url, "title": url, "duration": 100}))
        info.setdefault("ext", self._config.audio_format if self._config.download_kind == "audio" else self._config.video_format)
        filename = f"{info.get('title', 'track')} [{info.get('id', 'x')}].{info['ext']}"
        output_path = self._config.output_dir / filename
        if self.write_files:
            self._config.output_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake-media-bytes")
        info["_resolved_filepath"] = output_path
        return info

    def expand_playlist(self, playlist_url: str) -> list[dict]:
        return self.playlist_entries

    def search(self, query: str, n: int) -> list[dict]:
        self.search_calls.append((query, n))
        return self.search_results.get(query, [])


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "downloads"


@pytest.fixture
def sample_config(tmp_output_dir: Path) -> ExtractionConfig:
    return ExtractionConfig(output_dir=tmp_output_dir, max_concurrent=2)


@pytest.fixture
def fake_client_factory(sample_config: ExtractionConfig) -> Callable[..., FakeYtdlpClient]:
    def _make(**kwargs) -> FakeYtdlpClient:
        return FakeYtdlpClient(sample_config, **kwargs)

    return _make
