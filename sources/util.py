"""Shared helpers for normalizing per-source date fields to ISO 8601 strings."""
import datetime


def epoch_to_iso(value, unit="s"):
    """Convert a Unix timestamp (seconds or milliseconds) to an ISO 8601 string.
    Returns "" if value is missing/unparseable."""
    if value in (None, ""):
        return ""
    try:
        seconds = float(value) / (1000 if unit == "ms" else 1)
        return datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""
