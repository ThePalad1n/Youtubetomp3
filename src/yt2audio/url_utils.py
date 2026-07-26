"""URL classification/normalization and text-list parsing. Pure functions, no network I/O."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

_PLAYLIST_PATH_HINTS = ("/playlist",)


def is_playlist_url(url: str) -> bool:
    """Heuristic: does this URL look like it points at a playlist (as opposed
    to a single item)? Based purely on URL shape - no network call.
    """
    parsed = urlparse(url)
    if any(hint in parsed.path for hint in _PLAYLIST_PATH_HINTS):
        return True
    query = parse_qs(parsed.query)
    return "list" in query


def normalize_url(url: str) -> str:
    """Strip surrounding whitespace. Left intentionally minimal - callers that
    need tracking-param stripping for a specific site can extend this later.
    """
    return url.strip()


def parse_url_list(text: str) -> list[str]:
    """Split a pasted text blob into URLs: one per line, blank lines and
    '#'-prefixed comment lines dropped, duplicates removed while preserving
    first-seen order.
    """
    seen: set[str] = set()
    urls: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_url(raw_line)
        if not line or line.startswith("#"):
            continue
        if line not in seen:
            seen.add(line)
            urls.append(line)
    return urls
