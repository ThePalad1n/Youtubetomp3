"""Library-friendly logging: a NullHandler by default, per Python conventions.

The integrating application is expected to configure handlers/levels on the
"yt2audio" logger (or root) itself; this module just guarantees "no handlers
found" warnings never leak to a caller that hasn't configured logging.
"""
import logging

logger = logging.getLogger("yt2audio")
logger.addHandler(logging.NullHandler())
