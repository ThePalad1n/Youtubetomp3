from yt2audio.models import ExtractionStatus, SourceKind
from yt2audio.spotify_flow import extract_from_spotify_export


def test_spotify_export_matches_and_downloads(sample_config, fake_client_factory, tmp_path):
    export_file = tmp_path / "export.csv"
    export_file.write_text(
        "Track Name,Artist Name(s),Track Duration (ms)\nKarma Police,Radiohead,264000\n"
    )
    query = "Radiohead - Karma Police audio"
    client = fake_client_factory(
        search_results={
            query: [
                {
                    "id": "abc123",
                    "title": "Radiohead - Karma Police",
                    "duration": 264,
                    "webpage_url": "https://www.youtube.com/watch?v=abc123",
                }
            ]
        },
        download_results={
            "https://www.youtube.com/watch?v=abc123": {
                "id": "abc123",
                "title": "Radiohead - Karma Police",
                "duration": 264,
            }
        },
    )
    result = extract_from_spotify_export(export_file, sample_config, client=client)
    assert result.total == 1
    item = result.results[0]
    assert item.status == ExtractionStatus.SUCCESS
    assert item.source.kind == SourceKind.SPOTIFY_TRACK
    assert item.match_confidence is not None and item.match_confidence > 0.55


def test_spotify_export_no_match_does_not_download(sample_config, fake_client_factory, tmp_path):
    export_file = tmp_path / "export.csv"
    export_file.write_text("Track Name,Artist Name(s)\nObscure Track,Obscure Artist\n")
    client = fake_client_factory(search_results={})  # no candidates returned for any query
    result = extract_from_spotify_export(export_file, sample_config, client=client)
    assert result.total == 1
    assert result.results[0].status == ExtractionStatus.NO_MATCH
    assert client.download_calls == []


def test_spotify_export_search_failure_is_captured(sample_config, fake_client_factory, tmp_path):
    export_file = tmp_path / "export.csv"
    export_file.write_text("Track Name,Artist Name(s)\nSome Track,Some Artist\n")
    client = fake_client_factory()

    def boom(_query, _n):
        raise RuntimeError("search down")

    client.search = boom
    result = extract_from_spotify_export(export_file, sample_config, client=client)
    assert result.results[0].status == ExtractionStatus.FAILED
    assert "search down" in result.results[0].error_message
