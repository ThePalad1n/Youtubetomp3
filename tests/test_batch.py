from yt2audio.batch import extract_from_text, extract_from_url_list
from yt2audio.models import ExtractionStatus


def test_extract_from_url_list_aggregates_batch_result(sample_config, fake_client_factory):
    urls = ["https://example.com/1", "https://example.com/2"]
    client = fake_client_factory(
        download_results={
            "https://example.com/1": {"id": "1", "title": "One"},
            "https://example.com/2": {"id": "2", "title": "Two"},
        }
    )
    batch_result = extract_from_url_list(urls, sample_config, client=client)
    assert batch_result.total == 2
    assert batch_result.succeeded == 2
    assert batch_result.failed == 0
    assert len(batch_result.output_paths) == 2


def test_extract_from_url_list_mixed_success_and_failure(sample_config, fake_client_factory):
    urls = ["https://example.com/ok", "https://example.com/bad"]
    client = fake_client_factory(
        download_results={"https://example.com/ok": {"id": "ok", "title": "OK"}},
        download_errors={"https://example.com/bad": RuntimeError("nope")},
    )
    batch_result = extract_from_url_list(urls, sample_config, client=client)
    assert batch_result.succeeded == 1
    assert batch_result.failed == 1


def test_extract_from_text_parses_and_downloads(sample_config, fake_client_factory, tmp_path):
    text_file = tmp_path / "urls.txt"
    text_file.write_text("https://example.com/1\n# comment\nhttps://example.com/2\n")
    client = fake_client_factory(
        download_results={
            "https://example.com/1": {"id": "1", "title": "One"},
            "https://example.com/2": {"id": "2", "title": "Two"},
        }
    )
    batch_result = extract_from_text(text_file, sample_config, client=client)
    assert batch_result.total == 2
    assert set(client.download_calls) == {"https://example.com/1", "https://example.com/2"}


def test_extract_from_text_accepts_raw_string_blob(sample_config, fake_client_factory):
    client = fake_client_factory(
        download_results={"https://example.com/1": {"id": "1", "title": "One"}}
    )
    batch_result = extract_from_text("https://example.com/1", sample_config, client=client)
    assert batch_result.total == 1
    assert batch_result.results[0].status == ExtractionStatus.SUCCESS
