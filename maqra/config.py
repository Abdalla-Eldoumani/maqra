"""Runtime configuration. Environment variables override the defaults so the
same code runs against the live site and against a local test server."""

from __future__ import annotations

import os

from . import UPSTREAM_BASE


def upstream_base() -> str:
    """Base URL of the /data/ tree, always ending with a slash."""
    base = os.environ.get("MAQRA_UPSTREAM_BASE", UPSTREAM_BASE)
    return base if base.endswith("/") else base + "/"


def site_base() -> str:
    """Base URL of the site root (for index.html and friends)."""
    base = os.environ.get("MAQRA_SITE_BASE", "https://everyayah.com/")
    return base if base.endswith("/") else base + "/"
