"""Checks whether a newer version has been pushed to GitHub than the one installed locally.

Compares the local VERSION file against the same file fetched from the repo's main branch —
works identically whether the install came from `git clone` or a downloaded ZIP, since it
doesn't depend on git metadata at all. Bump VERSION and commit it whenever you push a change
worth notifying users about.
"""
import os

import requests

VERSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/izak004/jobbuddy/main/VERSION"
REPO_URL = "https://github.com/izak004/jobbuddy"


def _parse_version(text):
    """'1.2.0' -> (1, 2, 0), for numeric comparison. Falls back to the raw string if it
    doesn't look like a dotted version number, so comparison still works (just as a string)."""
    text = (text or "").strip()
    try:
        return tuple(int(p) for p in text.split("."))
    except ValueError:
        return text


def get_local_version():
    try:
        with open(VERSION_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def check_for_update():
    local = get_local_version()
    try:
        resp = requests.get(REMOTE_VERSION_URL, timeout=4)
        resp.raise_for_status()
        remote = resp.text.strip()
    except Exception as e:
        return {"current": local, "latest": None, "update_available": False, "checked": False, "error": str(e), "repo_url": REPO_URL}

    update_available = _parse_version(remote) > _parse_version(local)
    return {
        "current": local,
        "latest": remote,
        "update_available": update_available,
        "checked": True,
        "repo_url": REPO_URL,
    }
