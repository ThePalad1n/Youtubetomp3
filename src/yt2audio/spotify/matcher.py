"""Scores YouTube search candidates against a Spotify track. Pure logic, no
I/O - fully unit-testable with hand-built SearchCandidate fixtures.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from yt2audio.models import SpotifyTrack

# Words that suggest a candidate isn't a plain studio version of the track.
# Only penalized when the word does NOT also appear in the Spotify track's own
# name (some real tracks are legitimately titled "... - Live" or "... Cover").
_NOISE_WORDS = (
    "live",
    "cover",
    "reaction",
    "8d audio",
    "sped up",
    "nightcore",
    "karaoke",
    "instrumental",
    "remix",
    "slowed",
)

_DURATION_TOLERANT_SECONDS = 10.0
_DURATION_HARSH_SECONDS = 30.0


@dataclass(frozen=True)
class SearchCandidate:
    video_id: str
    title: str
    duration_seconds: float | None = None
    uploader: str | None = None
    webpage_url: str | None = None


def build_search_query(track: SpotifyTrack) -> str:
    """'audio' biases results toward studio uploads over music videos with
    spoken intros, and away from live/reaction content ranking on title alone.
    """
    artist = track.artist_name.strip()
    title = track.track_name.strip()
    query = f"{artist} - {title}" if artist else title
    return f"{query} audio".strip()


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)  # drop parenthetical/bracketed noise
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def _title_similarity(track: SpotifyTrack, candidate: SearchCandidate) -> float:
    expected = _normalize(f"{track.artist_name} {track.track_name}")
    actual = _normalize(candidate.title)
    return fuzz.token_sort_ratio(expected, actual) / 100.0


def _duration_score(track: SpotifyTrack, candidate: SearchCandidate) -> float:
    if track.duration_ms is None or candidate.duration_seconds is None:
        return 1.0  # unknown - don't penalize, we have no basis for comparison
    expected_seconds = track.duration_ms / 1000.0
    delta = abs(expected_seconds - candidate.duration_seconds)
    if delta <= _DURATION_TOLERANT_SECONDS:
        return 1.0
    if delta >= _DURATION_HARSH_SECONDS:
        return 0.0
    span = _DURATION_HARSH_SECONDS - _DURATION_TOLERANT_SECONDS
    return 1.0 - (delta - _DURATION_TOLERANT_SECONDS) / span


def _noise_penalty(track: SpotifyTrack, candidate: SearchCandidate) -> float:
    track_title_lower = track.track_name.lower()
    candidate_title_lower = candidate.title.lower()
    penalty = 0.0
    for word in _NOISE_WORDS:
        if word in candidate_title_lower and word not in track_title_lower:
            penalty += 0.15
    return min(penalty, 0.6)


def score_candidate(track: SpotifyTrack, candidate: SearchCandidate) -> float:
    """Returns a 0.0-1.0 confidence that `candidate` is the right YouTube
    upload for `track`, combining title similarity, duration closeness, and a
    penalty for noise words (live/cover/nightcore/...) not present in the
    original track title.
    """
    title_score = _title_similarity(track, candidate)
    duration_score = _duration_score(track, candidate)
    combined = (title_score * 0.7) + (duration_score * 0.3)
    combined -= _noise_penalty(track, candidate)
    return max(0.0, min(1.0, combined))


def select_best_match(
    track: SpotifyTrack, candidates: list[SearchCandidate], min_confidence: float
) -> tuple[SearchCandidate | None, float]:
    """Returns (best candidate, its score) if it clears min_confidence, else (None, best_score_seen)."""
    best_candidate: SearchCandidate | None = None
    best_score = 0.0
    for candidate in candidates:
        score = score_candidate(track, candidate)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    if best_candidate is not None and best_score >= min_confidence:
        return best_candidate, best_score
    return None, best_score
