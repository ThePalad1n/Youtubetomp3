from yt2audio.models import SpotifyTrack
from yt2audio.spotify.matcher import (
    SearchCandidate,
    build_search_query,
    score_candidate,
    select_best_match,
)


def test_build_search_query_includes_artist_title_and_audio_hint():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead")
    assert build_search_query(track) == "Radiohead - Karma Police audio"


def test_build_search_query_no_artist():
    track = SpotifyTrack(track_name="Some Track", artist_name="")
    assert build_search_query(track) == "Some Track audio"


def test_strong_title_and_duration_match_scores_high():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead", duration_ms=264000)
    candidate = SearchCandidate(
        video_id="abc", title="Radiohead - Karma Police", duration_seconds=264.0
    )
    assert score_candidate(track, candidate) > 0.85


def test_live_version_is_downranked_vs_studio_match():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead", duration_ms=264000)
    studio = SearchCandidate(video_id="s", title="Radiohead - Karma Police", duration_seconds=264.0)
    live = SearchCandidate(
        video_id="l", title="Radiohead - Karma Police (Live at Glastonbury)", duration_seconds=290.0
    )
    assert score_candidate(track, studio) > score_candidate(track, live)


def test_legitimately_live_track_not_penalized_for_live_keyword():
    track = SpotifyTrack(track_name="Karma Police - Live", artist_name="Radiohead")
    candidate = SearchCandidate(video_id="l", title="Radiohead - Karma Police - Live")
    # "live" appears in the track's own name, so it should not be penalized
    assert score_candidate(track, candidate) > 0.7


def test_large_duration_mismatch_tanks_score():
    track = SpotifyTrack(track_name="Short Song", artist_name="Some Band", duration_ms=120000)
    full_album_upload = SearchCandidate(
        video_id="x", title="Some Band - Short Song", duration_seconds=3600.0
    )
    assert score_candidate(track, full_album_upload) < 0.75


def test_unknown_duration_does_not_penalize():
    track = SpotifyTrack(track_name="Some Song", artist_name="Some Band", duration_ms=None)
    candidate = SearchCandidate(video_id="x", title="Some Band - Some Song", duration_seconds=None)
    assert score_candidate(track, candidate) > 0.85


def test_select_best_match_returns_highest_scoring_above_threshold():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead", duration_ms=264000)
    weak = SearchCandidate(video_id="w", title="Totally Unrelated Video", duration_seconds=50.0)
    strong = SearchCandidate(video_id="s", title="Radiohead - Karma Police", duration_seconds=264.0)
    best, score = select_best_match(track, [weak, strong], min_confidence=0.55)
    assert best is strong
    assert score > 0.55


def test_select_best_match_returns_none_below_threshold():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead", duration_ms=264000)
    weak = SearchCandidate(video_id="w", title="Totally Unrelated Video", duration_seconds=50.0)
    best, _score = select_best_match(track, [weak], min_confidence=0.55)
    assert best is None


def test_select_best_match_empty_candidates():
    track = SpotifyTrack(track_name="Karma Police", artist_name="Radiohead")
    best, score = select_best_match(track, [], min_confidence=0.55)
    assert best is None
    assert score == 0.0
