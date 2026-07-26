from yt2audio.extractor import extract_playlist, extract_single
from yt2audio.models import ExtractionStatus, SourceKind


def test_extract_single_success(sample_config, fake_client_factory):
    client = fake_client_factory(
        download_results={"https://example.com/a": {"id": "a1", "title": "Song A", "duration": 120}}
    )
    result = extract_single("https://example.com/a", sample_config, client=client)
    assert result.status == ExtractionStatus.SUCCESS
    assert result.resolved_title == "Song A"
    assert result.duration_seconds == 120
    assert result.output_path is not None and result.output_path.exists()
    assert result.source.kind == SourceKind.DIRECT_URL


def test_extract_single_failure_is_captured_not_raised(sample_config, fake_client_factory):
    client = fake_client_factory(download_errors={"https://example.com/bad": RuntimeError("boom")})
    result = extract_single("https://example.com/bad", sample_config, client=client)
    assert result.status == ExtractionStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert "boom" in result.error_message


def test_extract_single_skipped_when_yt_dlp_reused_existing_file(sample_config, fake_client_factory):
    client = fake_client_factory(
        download_results={
            "https://example.com/a": {"id": "a1", "title": "Song A", "__real_download": False}
        }
    )
    result = extract_single("https://example.com/a", sample_config, client=client)
    assert result.status == ExtractionStatus.SKIPPED


def test_extract_playlist_isolates_per_item_failures(sample_config, fake_client_factory):
    entries = [
        {"url": "https://example.com/1", "id": "1"},
        {"url": "https://example.com/2", "id": "2"},
        {"url": "https://example.com/3", "id": "3"},
    ]
    client = fake_client_factory(
        playlist_entries=entries,
        download_results={
            "https://example.com/1": {"id": "1", "title": "Track One"},
            "https://example.com/3": {"id": "3", "title": "Track Three"},
        },
        download_errors={"https://example.com/2": RuntimeError("video unavailable")},
    )
    results = extract_playlist("https://example.com/playlist", sample_config, client=client)
    assert len(results) == 3
    assert results[0].status == ExtractionStatus.SUCCESS
    assert results[1].status == ExtractionStatus.FAILED
    assert results[2].status == ExtractionStatus.SUCCESS
    assert all(r.source.kind == SourceKind.PLAYLIST_ENTRY for r in results)
    assert results[1].source.playlist_index == 1


def test_extract_playlist_entry_missing_url(sample_config, fake_client_factory):
    client = fake_client_factory(playlist_entries=[{"id": None, "url": None}])
    results = extract_playlist("https://example.com/playlist", sample_config, client=client)
    assert len(results) == 1
    assert results[0].status == ExtractionStatus.FAILED
    assert results[0].error_type == "MissingEntryURL"


def test_extract_playlist_expand_failure_is_structural(sample_config, fake_client_factory):
    client = fake_client_factory()

    def boom(_url):
        raise RuntimeError("playlist gone")

    client.expand_playlist = boom
    results = extract_playlist("https://example.com/playlist", sample_config, client=client)
    assert len(results) == 1
    assert results[0].status == ExtractionStatus.FAILED
    assert "playlist gone" in results[0].error_message


def test_video_download_kind_uses_video_format(sample_config, fake_client_factory):
    sample_config.download_kind = "video"
    client = fake_client_factory(download_results={"https://example.com/v": {"id": "v1", "title": "Vid"}})
    result = extract_single("https://example.com/v", sample_config, client=client)
    assert result.media_format == sample_config.video_format
