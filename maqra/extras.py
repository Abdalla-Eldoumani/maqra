"""Everything on everyayah.com that is not per-ayah audio and is worth keeping.

- timings_files/: 30 zips, one text file per surah, one millisecond offset per
  line (the split points used to cut the full-surah recordings into ayahs).
  Each zip is kept verbatim and also converted to one JSON file per reciter set
  under timings/ in the repository.
- Ayah images: four renderings of every ayah (GIF, JPG, PNG, high-resolution
  PNG), about 250 MB together.
- recitations.js, the site's own reciter table, and the small text notes.
- tools/: the legacy Windows splitting tools. Source zips are kept; the
  unsigned .exe is not mirrored by default.
- The XML text set is deliberately not mirrored: its own 00_warning.txt says
  the files carry many mistakes and points to the Tanzil project instead.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import config
from .http import DownloadError, download, get_bytes
from .listing import file_url, files_only, list_folder
from .mirror import _download_many, _fmt_bytes, _now

Log = Callable[[str], None]

IMAGE_SETS = {
    "QuranText": "images/gif",
    "QuranText_jpg": "images/jpg",
    "images_png": "images/png",
    "quranpngs": "images/png-hires",
}
SITE_FILES = ["recitations.js", "audhubillah.mp3", "bismillah.mp3"]
TOOL_SKIP_SUFFIXES = (".exe",)
TIMING_LINE = re.compile(r"^\s*(\d+)\s*$")


def mirror_folder_flat(folder: str, dest: Path, workers: int, log: Log, skip: Callable[[str], Optional[str]] = lambda n: None) -> dict:
    """Mirror every file in one upstream folder into dest. Returns a summary dict."""
    dest.mkdir(parents=True, exist_ok=True)
    entries = files_only(list_folder(folder))
    jobs = []
    skipped = []
    for e in entries:
        why = skip(e.name)
        if why:
            skipped.append({"name": e.name, "bytes": e.size, "reason": why})
            continue
        target = dest / e.name
        if target.is_file() and (e.size is None or target.stat().st_size == e.size):
            continue
        jobs.append((file_url(folder, e.name), target, e.size))
    log(f"[{folder}] {len(entries)} files listed, {len(jobs)} to fetch, {len(skipped)} skipped")
    failures = _download_many(jobs, workers, log, folder)
    return {
        "folder": folder,
        "listed": len(entries),
        "bytes": sum(e.size or 0 for e in entries),
        "fetched": len(jobs) - len(failures),
        "failures": [{"name": n, "error": err} for n, err in failures],
        "skipped": skipped,
    }


def mirror_site_files(root: Path, log: Log) -> dict:
    dest = root / "upstream"
    dest.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in SITE_FILES:
        try:
            download(config.upstream_base() + name, dest / name)
            results[name] = "ok"
        except DownloadError as exc:
            results[name] = str(exc)
    for page in ("index.html", "recitations_ayat.html", "recitations_pages.html", "old_index.html", "src/getfile.html"):
        try:
            data = get_bytes(config.site_base() + page)
            target = dest / "site" / page
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            results[page] = "ok"
        except DownloadError as exc:
            results[page] = str(exc)
    log(f"[site] {results}")
    return results


def mirror_timings(root: Path, workers: int, log: Log, timings_out: Path) -> dict:
    summary = mirror_folder_flat("timings_files", root / "timings" / "_upstream", workers, log)
    converted = convert_timings(root / "timings" / "_upstream", timings_out, log)
    summary["converted"] = converted
    return summary


TIMING_NAME = re.compile(r"^(?:chapter)?(\d{1,3})([a-z])?(?:(\d{1,3})-(\d{1,3}))?\.txt$", re.I)
NOTE_FILES = re.compile(r"^(details|source|_readme|000_readme|readme|000_disclaimer)\.txt$", re.I)
NOTE_LIMIT = 4096


def parse_timing_zip(path: Path) -> Tuple[Dict[int, List[int]], Dict[int, List[dict]], Dict[str, str], List[str]]:
    """Parse one upstream timing zip.

    Returns (whole, parts, notes, warnings):
      whole: {surah: [offset, ...]} for files that cover a whole surah (001.txt, Chapter001.txt, 054.TXT)
      parts: {surah: [{"part": "a", "ayah_range": [1, 117] or None, "segments": [...]}, ...]}
             for recordings split into several files (002a.txt, 002a001-117.txt)
      notes: {filename: text} for the small text files shipped beside the timings
      warnings: entries that were neither
    """
    whole: Dict[int, List[int]] = {}
    parts: Dict[int, List[dict]] = {}
    notes: Dict[str, str] = {}
    warnings: List[str] = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            base = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
            if NOTE_FILES.match(base):
                notes[base] = zf.read(info).decode("utf-8", errors="replace")[:NOTE_LIMIT]
                continue
            m = TIMING_NAME.match(base)
            if not m:
                warnings.append(f"ignored entry {info.filename}")
                continue
            surah = int(m.group(1))
            part = m.group(2).lower() if m.group(2) else None
            rng = [int(m.group(3)), int(m.group(4))] if m.group(3) else None
            text = zf.read(info).decode("utf-8", errors="replace")
            values: List[int] = []
            for line in text.splitlines():
                if not line.strip():
                    continue
                mm = TIMING_LINE.match(line)
                if not mm:
                    warnings.append(f"{base}: non-numeric line {line.strip()!r}")
                    continue
                values.append(int(mm.group(1)))
            if part is None:
                if surah in whole:
                    warnings.append(f"{base}: duplicate whole-surah file for surah {surah}; kept the first")
                    continue
                whole[surah] = values
            else:
                parts.setdefault(surah, []).append({"part": part, "ayah_range": rng, "segments": values})
    for lst in parts.values():
        lst.sort(key=lambda d: d["part"])
    return whole, parts, notes, warnings


TIMING_MEANING = (
    "Offsets in milliseconds into the full-surah recording. Each value is where one segment ends, in order. "
    "Most files carry one more segment than the surah has ayahs: the first segment is the isti'adhah and basmala "
    "that opens the recording. everyayah.com's own readme for the Ash-Shatri set says so: the mp3 files include "
    "the basmala, so delete the first line (about 8000 milliseconds) to make the numbering line up with the ayahs. "
    "Compare segments against ayahs per surah before relying on any file: extra_segments is that difference, +1 for an opening basmala segment, 0 for none, about one extra per ayah in the sets that interleave a spoken translation, negative where the upstream file stops early. Where a recording was split into parts "
    "(002a, 002b, with or without an ayah range in the name), offsets are relative to that part's audio file. "
    "everyayah.com's disclaimer: many mp3s were fixed by hand after splitting, so these will not reproduce the "
    "published ayah files exactly."
)


def convert_timings(src_dir: Path, out_dir: Path, log: Log, counts: Optional[Dict[int, int]] = None) -> List[dict]:
    """Convert every timing zip into one JSON file. Returns the index written."""
    from .registry import ayah_counts
    counts = counts or ayah_counts()
    out_dir.mkdir(parents=True, exist_ok=True)
    index: List[dict] = []
    for zp in sorted(src_dir.glob("*.zip")):
        try:
            whole, parts, notes, warnings = parse_timing_zip(zp)
        except zipfile.BadZipFile as exc:
            log(f"[timings] {zp.name}: unreadable ({exc})")
            continue
        if not whole and not parts:
            log(f"[timings] {zp.name}: no timing files inside; skipped ({len(warnings)} entries ignored)")
            index.append({"source_zip": zp.name, "skipped": True, "reason": "no timing files inside"})
            continue
        stem = re.sub(r"[^A-Za-z0-9]+", "-", zp.stem).strip("-").lower()
        surahs = {
            str(k): {"ayahs": counts.get(k), "segments": v, "extra_segments": (len(v) - counts[k]) if k in counts else None}
            for k, v in sorted(whole.items())
        }
        doc = {
            "schema_version": 2,
            "source_zip": zp.name,
            "source_url": file_url("timings_files", zp.name),
            "unit": "milliseconds",
            "meaning": TIMING_MEANING,
            "license_note": "(C) VerseByVerseQuran.com. Upstream requires a link back to everyayah.com from any product or web site that uses these timings.",
            "converted_at": _now(),
            "surahs_covered": sorted(set(whole) | set(parts)),
            "surahs": surahs,
            "parts": {str(k): v for k, v in sorted(parts.items())},
            "upstream_notes": notes,
            "warnings": warnings,
        }
        target = out_dir / f"{stem}.json"
        target.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        covered = len(doc["surahs_covered"])
        index.append({"file": target.name, "source_zip": zp.name, "surahs": covered, "split_surahs": len(parts), "warnings": len(warnings)})
        log(f"[timings] {zp.name} -> {target.name}: {covered} surahs ({len(parts)} split into parts), {len(warnings)} warnings")
    return index


def mirror_images(root: Path, workers: int, log: Log, sets: Optional[List[str]] = None) -> List[dict]:
    results = []
    for folder, rel in IMAGE_SETS.items():
        if sets and folder not in sets and rel not in sets:
            continue
        results.append(mirror_folder_flat(folder, root / rel, workers, log,
                                          skip=lambda n: "bulk archive" if n.lower().endswith(".zip") else None))
    return results


def mirror_tools(root: Path, workers: int, log: Log, include_exe: bool = False) -> dict:
    def skip(name: str) -> Optional[str]:
        if not include_exe and name.lower().endswith(TOOL_SKIP_SUFFIXES):
            return "unsigned executable; mp3splt is available from its own project"
        return None
    return mirror_folder_flat("tools", root / "tools", workers, log, skip=skip)


def mirror_offline_zip(root: Path, log: Log) -> dict:
    """The one folder that only ships an offline zip (Shaatree with Ibrahim Walk)."""
    folder = "MultiLanguage/Shaatree_Walk_64kbps"
    entries = files_only(list_folder(folder))
    dest = root / "extras" / "shaatree-walk-64kbps-offline"
    dest.mkdir(parents=True, exist_ok=True)
    out = {"folder": folder, "files": []}
    for e in entries:
        if e.name.startswith("."):
            continue
        target = dest / e.name
        if target.is_file() and target.stat().st_size == e.size:
            out["files"].append({"name": e.name, "bytes": e.size, "status": "present"})
            continue
        try:
            download(file_url(folder, e.name), target, expected_size=e.size)
            out["files"].append({"name": e.name, "bytes": e.size, "status": "fetched"})
        except DownloadError as exc:
            out["files"].append({"name": e.name, "bytes": e.size, "status": f"failed: {exc}"})
    log(f"[extras] {out}")
    return out
