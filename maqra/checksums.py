"""MD5 list parsing and file hashing.

Upstream checksum files come in several shapes:

    8b2ad7066151af325f8f9b60722fafb1 *Alafasy_64kbps/001001.mp3
    8b2ad7066151af325f8f9b60722fafb1  Alafasy_64kbps/001001.mp3
    8b2ad7066151af325f8f9b60722fafb1 *001001.mp3
    8b2ad7066151af325f8f9b60722fafb1  ./001001.mp3

Only the basename is kept, so any prefix works. Lines that do not look like a
32-hex digest followed by a name are ignored and counted.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Tuple

_LINE = re.compile(r"^\s*([0-9a-fA-F]{32})\s+\*?\s*(.+?)\s*$")


def parse_md5_list(text: str) -> Tuple[Dict[str, str], int]:
    """Return ({basename: md5_lower}, ignored_line_count)."""
    out: Dict[str, str] = {}
    ignored = 0
    for raw in text.lstrip("\ufeff").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _LINE.match(line)
        if not m:
            ignored += 1
            continue
        digest, name = m.group(1).lower(), m.group(2)
        name = name.replace("\\", "/").rsplit("/", 1)[-1]
        out[name] = digest
    return out, ignored


def hash_file(path: Path, chunk: int = 1 << 20) -> Tuple[str, str]:
    """Return (md5, sha256) hex digests computed in one pass."""
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            md5.update(buf)
            sha.update(buf)
    return md5.hexdigest(), sha.hexdigest()


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            sha.update(buf)
    return sha.hexdigest()
