from tests.conftest import FIXTURES_DIR
from yt2audio.spotify.parser import parse_spotify_export


def test_parse_exportify_csv():
    tracks = parse_spotify_export(FIXTURES_DIR / "exportify_sample.csv")
    assert len(tracks) == 2  # the blank-track-name row is dropped
    assert tracks[0].track_name == "Blurryface Anthem"
    assert tracks[0].artist_name == "Twenty One Pilots"
    assert tracks[0].album_name == "Blurryface"
    assert tracks[0].duration_ms == 214000
    assert tracks[0].track_uri == "spotify:track:1abcXYZ"
    assert tracks[1].track_name == "Simple Song"


def test_parse_plain_text_tracklist():
    tracks = parse_spotify_export(FIXTURES_DIR / "plain_tracklist.txt")
    assert len(tracks) == 4
    assert tracks[0].artist_name == "Twenty One Pilots"
    assert tracks[0].track_name == "Blurryface Anthem"
    assert tracks[1].artist_name == "The Simple Band"
    assert tracks[1].track_name == "Simple Song"


def test_plain_text_splits_only_on_first_dash():
    tracks = parse_spotify_export(FIXTURES_DIR / "plain_tracklist.txt")
    hyphen_track = tracks[2]
    assert hyphen_track.artist_name == "Artist With"
    assert hyphen_track.track_name == "A Hyphen - The Actual Title"


def test_plain_text_line_with_no_delimiter_falls_back_to_raw():
    tracks = parse_spotify_export(FIXTURES_DIR / "plain_tracklist.txt")
    fallback_track = tracks[3]
    assert fallback_track.artist_name == ""
    assert fallback_track.track_name == "no delimiter here at all"


def test_parse_inline_csv_string():
    csv_text = "Track Name,Artist Name(s)\nHello,World\n"
    tracks = parse_spotify_export(csv_text)
    assert len(tracks) == 1
    assert tracks[0].track_name == "Hello"
    assert tracks[0].artist_name == "World"


def test_parse_inline_plain_text_string():
    tracks = parse_spotify_export("Radiohead - Karma Police")
    assert len(tracks) == 1
    assert tracks[0].artist_name == "Radiohead"
    assert tracks[0].track_name == "Karma Police"
