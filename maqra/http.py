"""Small HTTP layer on urllib: retries, timeouts, HEAD, and resumable downloads.

No third-party dependency, so the mirror runs on a bare Python install. The
upstream CDN (BunnyCDN) answers HEAD, returns exact Content-Length, and honours
Range, which is what makes resume possible.
"""

from __future__ import annotations

import os
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import USER_AGENT

DEFAULT_TIMEOUT = 60
RETRIES = 6


class DownloadError(RuntimeError):
    pass


@dataclass
class HeadInfo:
    status: int
    length: Optional[int]
    content_type: Optional[str]
    accept_ranges: bool
    last_modified: Optional[str]


def quote_path(path: str) -> str:
    """Percent-encode a slash-separated path without touching the slashes."""
    return "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))


def _request(url: str, method: str = "GET", headers: Optional[dict] = None) -> urllib.request.Request:
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        h.update(headers)
    return urllib.request.Request(url, method=method, headers=h)


def _backoff(attempt: int) -> float:
    return min(60.0, (2 ** attempt) + random.uniform(0, 1))


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (408, 425, 429, 500, 502, 503, 504)
    return isinstance(exc, (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError))


def get_bytes(url: str, timeout: int = DEFAULT_TIMEOUT, retries: int = RETRIES) -> bytes:
    last: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(_request(url), timeout=timeout) as resp:
                return resp.read()
        except BaseException as exc:  # noqa: BLE001 - we re-raise below
            last = exc
            if not _retryable(exc) or attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
    raise DownloadError(f"GET {url} failed: {last}") from last


def get_text(url: str, encoding: str = "utf-8", **kw) -> str:
    return get_bytes(url, **kw).decode(encoding, errors="replace")


def head(url: str, timeout: int = DEFAULT_TIMEOUT, retries: int = RETRIES) -> HeadInfo:
    last: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(_request(url, "HEAD"), timeout=timeout) as resp:
                length = resp.headers.get("Content-Length")
                return HeadInfo(
                    status=resp.status,
                    length=int(length) if length is not None else None,
                    content_type=resp.headers.get("Content-Type"),
                    accept_ranges=(resp.headers.get("Accept-Ranges", "").lower() == "bytes"),
                    last_modified=resp.headers.get("Last-Modified"),
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return HeadInfo(404, None, None, False, None)
            last = exc
            if not _retryable(exc) or attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
        except BaseException as exc:  # noqa: BLE001
            last = exc
            if not _retryable(exc) or attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
    raise DownloadError(f"HEAD {url} failed: {last}") from last


def download(
    url: str,
    dest: Path,
    expected_size: Optional[int] = None,
    resume: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = RETRIES,
    chunk: int = 1 << 20,
    progress: Optional[Callable[[int, Optional[int]], None]] = None,
) -> int:
    """Download url to dest atomically (via dest.part), resuming when possible.

    Returns the final size in bytes. Raises DownloadError when the size does not
    match expected_size after all retries.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last: Optional[BaseException] = None

    for attempt in range(retries):
        have = part.stat().st_size if (resume and part.exists()) else 0
        if expected_size is not None and have > expected_size:
            part.unlink()
            have = 0
        headers = {"Range": f"bytes={have}-"} if have > 0 else {}
        try:
            req = _request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if have > 0 and resp.status != 206:
                    # Server ignored the range; start over.
                    have = 0
                    mode = "wb"
                else:
                    mode = "ab" if have > 0 else "wb"
                total: Optional[int] = None
                cl = resp.headers.get("Content-Length")
                if cl is not None:
                    total = int(cl) + have
                with open(part, mode) as fh:
                    while True:
                        buf = resp.read(chunk)
                        if not buf:
                            break
                        fh.write(buf)
                        have += len(buf)
                        if progress:
                            progress(have, total)
            size = part.stat().st_size
            if expected_size is not None and size != expected_size:
                raise DownloadError(f"size mismatch for {url}: got {size}, expected {expected_size}")
            os.replace(part, dest)
            return size
        except DownloadError as exc:
            last = exc
            # A wrong size is not a transient error unless the transfer was cut short,
            # in which case the next attempt resumes. Only retry when we are short.
            size = part.stat().st_size if part.exists() else 0
            if expected_size is None or size >= expected_size:
                part.unlink(missing_ok=True)
                break
            if attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 416 and part.exists():
                # Range not satisfiable: the part file is already complete or corrupt.
                part.unlink()
                continue
            if exc.code == 404:
                part.unlink(missing_ok=True)
                raise DownloadError(f"GET {url} failed: 404") from exc
            if not _retryable(exc) or attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
        except BaseException as exc:  # noqa: BLE001
            last = exc
            if not _retryable(exc) or attempt == retries - 1:
                break
            time.sleep(_backoff(attempt))
    raise DownloadError(f"GET {url} failed after {retries} attempts: {last}") from last
