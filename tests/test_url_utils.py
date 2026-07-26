from yt2audio.url_utils import is_playlist_url, normalize_url, parse_url_list


def test_is_playlist_url_playlist_path():
    assert is_playlist_url("https://www.youtube.com/playlist?list=PL123") is True


def test_is_playlist_url_watch_with_list_param():
    assert is_playlist_url("https://www.youtube.com/watch?v=abc123&list=PL123") is True


def test_is_playlist_url_plain_video():
    assert is_playlist_url("https://www.youtube.com/watch?v=abc123") is False


def test_is_playlist_url_non_youtube_single():
    assert is_playlist_url("https://soundcloud.com/artist/track") is False


def test_normalize_url_strips_whitespace():
    assert normalize_url("  https://example.com/x  \n") == "https://example.com/x"


def test_parse_url_list_drops_blanks_comments_and_dupes():
    text = """
    https://example.com/a
    # a comment
    https://example.com/b

    https://example.com/a
    """
    assert parse_url_list(text) == ["https://example.com/a", "https://example.com/b"]


def test_parse_url_list_empty_text():
    assert parse_url_list("") == []
