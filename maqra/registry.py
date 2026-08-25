"""Load the reciter registry and surah table shipped in manifests/."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = REPO_ROOT / "manifests"

AYAH_FILE = re.compile(r"^(\d{3})(\d{3})\.mp3$")


@dataclass(frozen=True)
class Reciter:
    slug: str
    name: str
    reciter_key: str
    style: str
    riwayah: str
    language: str
    kind: str
    bitrate_kbps: Optional[int]
    source_folder: str
    source_url: str
    upstream_checksum_files: List[str]
    upstream_zip: Optional[str]
    status: str
    notes: str
    github_release_tag: str
    huggingface_repo: str

    @classmethod
    def from_dict(cls, d: dict) -> "Reciter":
        return cls(
            slug=d["slug"], name=d["name"], reciter_key=d["reciter_key"], style=d["style"],
            riwayah=d["riwayah"], language=d["language"], kind=d["kind"],
            bitrate_kbps=d.get("bitrate_kbps"), source_folder=d["source_folder"],
            source_url=d["source_url"], upstream_checksum_files=list(d.get("upstream_checksum_files", [])),
            upstream_zip=d.get("upstream_zip"), status=d.get("status", "unknown"), notes=d.get("notes", ""),
            github_release_tag=d.get("github_release_tag", d["slug"]),
            huggingface_repo=d.get("huggingface_repo", f"maqra-project/{d['slug']}"),
        )


def load_reciters(path: Path = MANIFESTS / "reciters.json") -> List[Reciter]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [Reciter.from_dict(r) for r in doc["reciters"]]


def reciter_map(path: Path = MANIFESTS / "reciters.json") -> Dict[str, Reciter]:
    return {r.slug: r for r in load_reciters(path)}


def load_surahs(path: Path = MANIFESTS / "surahs.json") -> List[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["surahs"]


def ayah_counts(path: Path = MANIFESTS / "surahs.json") -> Dict[int, int]:
    return {s["number"]: s["ayah_count"] for s in load_surahs(path)}


def expected_ayah_files(counts: Dict[int, int]) -> List[str]:
    """All 6236 SSSAAA.mp3 names, excluding the optional SSS000 intro files."""
    out: List[str] = []
    for s in sorted(counts):
        for a in range(1, counts[s] + 1):
            out.append(f"{s:03d}{a:03d}.mp3")
    return out


def split_ayah_name(name: str) -> Optional[tuple]:
    m = AYAH_FILE.match(name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def select(reciters: List[Reciter], only: Optional[List[str]] = None, skip: Optional[List[str]] = None) -> List[Reciter]:
    chosen = reciters
    if only:
        wanted = set(only)
        chosen = [r for r in chosen if r.slug in wanted or r.reciter_key in wanted]
        missing = wanted - {r.slug for r in chosen} - {r.reciter_key for r in chosen}
        if missing:
            raise SystemExit(f"unknown reciter selector(s): {sorted(missing)}")
    if skip:
        drop = set(skip)
        chosen = [r for r in chosen if r.slug not in drop and r.reciter_key not in drop]
    return chosen
