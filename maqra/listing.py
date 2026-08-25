"""Parse everyayah.com directory listings.

The CDN renders each folder as an HTML table. Every file row carries the exact
byte count in a data-order attribute on the size cell, and directories carry
data-order="-1". The parser reads that attribute rather than the rounded
human-readable size, so sizes are exact.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, List, Optional

from . import config
from .http import get_text, quote_path


@dataclass(frozen=True)
class Entry:
    name: str
    href: str
    is_dir: bool
    size: Optional[int]  # exact bytes for files, None for directories
    modified: Optional[str]  # ISO-8601 from the <time datetime> attribute


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[dict] = []
        self._row: Optional[dict] = None
        self._in_name = False
        self._in_size = False
        self._cell_index = -1

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag == "tr":
            self._row = {"href": None, "name": "", "order": None, "size_text": "", "time": None}
            self._cell_index = -1
        elif self._row is None:
            return
        elif tag == "td":
            self._cell_index += 1
            if "data-order" in a:
                self._row["order"] = a["data-order"]
                self._in_size = True
        elif tag == "a" and self._row["href"] is None and a.get("href"):
            self._row["href"] = a["href"]
        elif tag == "span" and a.get("class") in ("name", "goup"):
            self._in_name = True
        elif tag == "time" and a.get("datetime"):
            self._row["time"] = a["datetime"]

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._in_name = False
        elif tag == "td":
            self._in_size = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._row is None:
            return
        if self._in_name:
            self._row["name"] += data
        elif self._in_size:
            self._row["size_text"] += data


_SIZE_RE = re.compile(r"^\s*([\d.]+)\s*(bytes?|B|KB|MB|GB|TB)\s*$", re.I)
_UNITS = {"byte": 1, "bytes": 1, "b": 1, "kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4}


def parse_size_text(text: str) -> Optional[int]:
    """Fallback for listings without data-order. Approximate by construction."""
    m = _SIZE_RE.match(text or "")
    if not m:
        return None
    return int(float(m.group(1)) * _UNITS[m.group(2).lower()])


def parse_listing(page: str) -> List[Entry]:
    parser = _TableParser()
    parser.feed(page)
    out: List[Entry] = []
    for row in parser.rows:
        href = row["href"]
        name = html.unescape(row["name"]).strip()
        if not href or not name or name == "..":
            continue
        order = row["order"]
        is_dir = href.endswith("/") or order == "-1"
        size: Optional[int]
        if is_dir:
            size = None
        elif order is not None and order.lstrip("-").isdigit():
            size = int(order)
        else:
            size = parse_size_text(row["size_text"])
        out.append(Entry(name=name, href=href, is_dir=is_dir, size=size, modified=row["time"]))
    return out


def folder_url(folder: str) -> str:
    folder = folder.strip("/")
    return config.upstream_base() + quote_path(folder) + "/"


def file_url(folder: str, name: str) -> str:
    return folder_url(folder) + quote_path(name)


def list_folder(folder: str) -> List[Entry]:
    """Fetch and parse the listing for a folder path relative to /data/."""
    return parse_listing(get_text(folder_url(folder)))


def files_only(entries: Iterable[Entry]) -> List[Entry]:
    return [e for e in entries if not e.is_dir]


def dirs_only(entries: Iterable[Entry]) -> List[Entry]:
    return [e for e in entries if e.is_dir]
