"""Exception hierarchy for structural failures.

Per-item failures during batch/playlist/spotify flows are caught internally
and surfaced as ExtractionResult(status=FAILED, ...) instead of raising —
these exceptions are reserved for configuration/setup problems that make it
impossible to even attempt the work.
"""


class Yt2AudioError(Exception):
    pass


class UnsupportedURLError(Yt2AudioError):
    pass


class ExtractionFailedError(Yt2AudioError):
    pass


class ConfigError(Yt2AudioError):
    pass
