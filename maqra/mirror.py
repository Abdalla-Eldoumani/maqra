"""Mirror one reciter folder from everyayah.com into the local data root.

Per reciter the engine:

1. reads the live folder listing (exact byte sizes),
2. saves every small upstream metadata file verbatim under _upstream/,
3. parses the upstream MD5 list(s) when present,
4. pulls 000_versebyverse.zip once and extracts the ayah files it carries,
5. downloads loose files for anything still missing or wrong-sized,
6. hashes every file (MD5 and SHA-256), compares with upstream MD5s,
7. re-downloads a file once on MD5 mismatch, then records what remains,
8. writes manifests/audio/<slug>.json and updates the state file.

Every step is idempotent; re-running resumes where it stopped.
"""

from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .checksums import hash_file, parse_md5_list
from .http import DownloadError, download, get_bytes
from .listing import Entry, file_url, files_only, dirs_only, list_folder
from .registry import AYAH_FILE, MANIFESTS, Reciter, ayah_counts, expected_ayah_files

INTRO_FILES = {"audhubillah.mp3", "bismillah.mp3", "audhubillah_bismillah.mp3"}
CHECKSUM_PRIORITY = [
    "000_checksum.md5", "checksums.md5", "000_unverified_checksum.md5", "md5.sum",
    "Shuray_md5.sum", "md5sum.txt", "000_oldchecksum.md5", "000_checksum_old.md5",
]
SMALL_FILE_LIMIT = 5 * 1024 * 1024  # anything larger than this (and not the ayah zip) is recorded, not mirrored
ZIP_NAME = "000_versebyverse.zip"
MANIFEST_SCHEMA = 1

Log = Callable[[str], None]


@dataclass
class Plan:
    ayah: Dict[str, Entry] = field(default_factory=dict)      # SSSAAA.mp3 -> entry
    intro: Dict[str, Entry] = field(default_factory=dict)     # bismillah etc.
    meta: Dict[str, Entry] = field(default_factory=dict)      # checksum lists, readmes, notes
    stray: Dict[str, Entry] = field(default_factory=dict)     # odd mp3s and leftovers, small
    skipped: List[Tuple[str, int, str]] = field(default_factory=list)  # (name, bytes, reason)
    subfolders: List[str] = field(default_factory=list)
    zip_entry: Optional[Entry] = None


def classify(entries: List[Entry]) -> Plan:
    plan = Plan()
    plan.subfolders = sorted(e.name for e in dirs_only(entries))
    for e in files_only(entries):
        name = e.name
        low = name.lower()
        size = e.size or 0
        if AYAH_FILE.match(name):
            plan.ayah[name] = e
        elif name == ZIP_NAME:
            plan.zip_entry = e
        elif low in INTRO_FILES:
            plan.intro[name] = e
        elif low.endswith((".md5", ".sum", ".txt", ".sh", ".ini")) or low in ("error_log", "md5sum.txt") or low.startswith("."):
            if size <= SMALL_FILE_LIMIT:
                plan.meta[name] = e
            else:
                plan.skipped.append((name, size, "metadata file over the small-file limit"))
        elif low.endswith((".zip", ".tar", ".7z", ".rar")):
            plan.skipped.append((name, size, "bulk archive; the per-ayah files are mirrored instead"))
        elif size <= SMALL_FILE_LIMIT:
            plan.stray[name] = e
        else:
            plan.skipped.append((name, size, "large non-ayah file"))
    return plan


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TiB"


def _size_ok(path: Path, size: Optional[int]) -> bool:
    return path.is_file() and (size is None or path.stat().st_size == size)


def load_upstream_md5(meta_dir: Path, present: List[str]) -> Tuple[Dict[str, str], Dict[str, str], Optional[str]]:
    """Return (md5 by basename, source file by basename, primary source name)."""
    merged: Dict[str, str] = {}
    source: Dict[str, str] = {}
    primary: Optional[str] = None
    for name in CHECKSUM_PRIORITY:
        if name not in present:
            continue
        path = meta_dir / name
        if not path.is_file():
            continue
        parsed, _ignored = parse_md5_list(path.read_text(encoding="utf-8", errors="replace"))
        if parsed and primary is None:
            primary = name
        for k, v in parsed.items():
            if k not in merged:
                merged[k] = v
                source[k] = name
    return merged, source, primary


def _extract_from_zip(zip_path: Path, dest_dir: Path, wanted: Dict[str, Entry], log: Log) -> int:
    """Extract ayah files from the bulk zip when the local copy is absent or wrong-sized."""
    extracted = 0
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        log(f"  zip unreadable ({exc}); falling back to loose downloads")
        return 0
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            base = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
            entry = wanted.get(base)
            if entry is None:
                continue
            target = dest_dir / base
            if _size_ok(target, entry.size):
                continue
            tmp = target.with_name(base + ".part")
            with zf.open(info) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            if entry.size is not None and tmp.stat().st_size != entry.size:
                # The zip is older or newer than the live file; leave it to the loose phase.
                tmp.unlink()
                continue
            tmp.replace(target)
            extracted += 1
    return extracted


def _download_many(jobs: List[Tuple[str, Path, Optional[int]]], workers: int, log: Log, label: str) -> List[Tuple[str, str]]:
    """Download (url, dest, size) jobs concurrently. Returns [(dest name, error)] for failures."""
    failures: List[Tuple[str, str]] = []
    if not jobs:
        return failures
    done = 0
    total = len(jobs)

    def run(job):
        url, dest, size = job
        try:
            download(url, dest, expected_size=size)
            return dest.name, None
        except DownloadError as exc:
            return dest.name, str(exc)

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for name, err in pool.map(run, jobs):
            done += 1
            if err:
                failures.append((name, err))
                log(f"  FAIL {name}: {err}")
            if done % 250 == 0 or done == total:
                log(f"  {label}: {done}/{total}")
    return failures


def _hash_many(paths: List[Path], workers: int) -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    if not paths:
        return out
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for path, digests in zip(paths, pool.map(hash_file, paths)):
            out[path.name] = digests
    return out


def mirror_reciter(
    reciter: Reciter,
    root: Path,
    *,
    workers: int = 8,
    use_zip: bool = True,
    keep_zip: bool = False,
    manifests_dir: Path = MANIFESTS / "audio",
    log: Log = print,
    counts: Optional[Dict[int, int]] = None,
    zip_min_bytes: int = 1 << 20,
    zip_min_missing: int = 100,
) -> dict:
    slug = reciter.slug
    folder = reciter.source_folder
    audio_dir = root / "audio" / slug
    meta_dir = audio_dir / "_upstream"
    extra_dir = audio_dir / "_extra"
    stray_dir = meta_dir / "stray"
    tmp_dir = root / "_tmp"
    for d in (audio_dir, meta_dir, extra_dir, tmp_dir):
        d.mkdir(parents=True, exist_ok=True)

    log(f"[{slug}] listing {reciter.source_url}")
    plan = classify(list_folder(folder))
    ayah_total_bytes = sum(e.size or 0 for e in plan.ayah.values())
    log(f"[{slug}] {len(plan.ayah)} ayah files ({_fmt_bytes(ayah_total_bytes)}), "
        f"{len(plan.intro)} intro, {len(plan.meta)} metadata, {len(plan.stray)} stray, "
        f"{len(plan.skipped)} skipped, subfolders {plan.subfolders}")

    # 1. Small upstream files, verbatim.
    small_jobs: List[Tuple[str, Path, Optional[int]]] = []
    for name, e in plan.meta.items():
        if not _size_ok(meta_dir / name, e.size):
            small_jobs.append((file_url(folder, name), meta_dir / name, e.size))
    for name, e in plan.intro.items():
        if not _size_ok(extra_dir / name, e.size):
            small_jobs.append((file_url(folder, name), extra_dir / name, e.size))
    for name, e in plan.stray.items():
        if not _size_ok(stray_dir / name, e.size):
            small_jobs.append((file_url(folder, name), stray_dir / name, e.size))
    failures = _download_many(small_jobs, workers, log, "metadata")

    # 2. Upstream MD5 lists.
    upstream_md5, md5_source, primary = load_upstream_md5(meta_dir, list(plan.meta))
    log(f"[{slug}] upstream md5 entries: {len(upstream_md5)}" + (f" (primary {primary})" if primary else " (none)"))

    def needs_fetch(name: str) -> bool:
        target = audio_dir / name
        return not _size_ok(target, plan.ayah[name].size)

    missing = [n for n in plan.ayah if needs_fetch(n)]
    log(f"[{slug}] locally valid by size: {len(plan.ayah) - len(missing)}; to fetch: {len(missing)}")

    # 3. Bulk zip first when it pays for itself.
    zip_used = False
    if use_zip and plan.zip_entry and (plan.zip_entry.size or 0) >= zip_min_bytes and len(missing) >= zip_min_missing:
        zip_path = tmp_dir / f"{slug}.zip"
        log(f"[{slug}] downloading {ZIP_NAME} ({_fmt_bytes(plan.zip_entry.size or 0)})")
        last_report = [0.0]

        def prog(have: int, total: Optional[int]) -> None:
            if have - last_report[0] >= 256 * 1024 * 1024:
                last_report[0] = have
                log(f"  zip: {_fmt_bytes(have)}" + (f" / {_fmt_bytes(total)}" if total else ""))

        try:
            download(file_url(folder, ZIP_NAME), zip_path, expected_size=plan.zip_entry.size, progress=prog)
            wanted = {n: plan.ayah[n] for n in missing}
            n = _extract_from_zip(zip_path, audio_dir, wanted, log)
            zip_used = True
            log(f"[{slug}] extracted {n} files from the zip")
        except DownloadError as exc:
            log(f"[{slug}] zip download failed ({exc}); using loose files")
        finally:
            if zip_path.exists() and not keep_zip:
                zip_path.unlink()
        missing = [n for n in plan.ayah if needs_fetch(n)]

    # 4. Loose files for whatever is still missing.
    loose_jobs = [(file_url(folder, n), audio_dir / n, plan.ayah[n].size) for n in missing]
    if loose_jobs:
        log(f"[{slug}] fetching {len(loose_jobs)} loose files with {workers} workers")
    failures += _download_many(loose_jobs, workers, log, "ayah files")

    # 5. Hash and compare.
    present = sorted(n for n in plan.ayah if _size_ok(audio_dir / n, plan.ayah[n].size))
    log(f"[{slug}] hashing {len(present)} files")
    digests = _hash_many([audio_dir / n for n in present], max(2, min(workers, 8)))

    mismatched = [n for n in present if n in upstream_md5 and digests[n][0] != upstream_md5[n]]
    if mismatched:
        log(f"[{slug}] {len(mismatched)} files disagree with the upstream md5 list; re-downloading once")
        for n in mismatched:
            (audio_dir / n).unlink(missing_ok=True)
        redo = [(file_url(folder, n), audio_dir / n, plan.ayah[n].size) for n in mismatched]
        failures += _download_many(redo, workers, log, "re-download")
        redo_present = [n for n in mismatched if _size_ok(audio_dir / n, plan.ayah[n].size)]
        digests.update(_hash_many([audio_dir / n for n in redo_present], 4))
        still = [n for n in redo_present if digests[n][0] != upstream_md5[n]]
        if still:
            log(f"[{slug}] {len(still)} files still differ from the md5 list; keeping the live server copy and recording the mismatch")
        mismatched = still
        present = sorted(n for n in plan.ayah if _size_ok(audio_dir / n, plan.ayah[n].size))

    # 6. Manifest.
    counts = counts or ayah_counts()
    expected = expected_ayah_files(counts)
    have_set = set(present)
    missing_ayahs = [n[:-4] for n in expected if n not in have_set]
    not_on_server = [n[:-4] for n in expected if n not in plan.ayah]
    mismatch_set = set(mismatched)

    files_rows = []
    verified = 0
    for n in present:
        md5, sha = digests[n]
        if n in upstream_md5:
            state = "upstream-mismatch" if n in mismatch_set else "upstream-match"
            if state == "upstream-match":
                verified += 1
        else:
            state = "no-upstream-md5"
        files_rows.append([n, plan.ayah[n].size, md5, sha, state])

    def side_rows(dirpath: Path, prefix: str, entries: Dict[str, Entry]) -> List[list]:
        rows = []
        for n in sorted(entries):
            p = dirpath / n
            if _size_ok(p, entries[n].size):
                md5, sha = hash_file(p)
                rows.append([f"{prefix}/{n}", p.stat().st_size, md5, sha])
        return rows

    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "slug": slug,
        "name": reciter.name,
        "source_folder": folder,
        "source_url": reciter.source_url,
        "mirrored_at": _now(),
        "bulk_zip_used": zip_used,
        "ayah_files": len(present),
        "ayah_bytes": sum(r[1] for r in files_rows),
        "expected_ayah_files": len(expected),
        "missing_ayahs": missing_ayahs,
        "missing_on_upstream": not_on_server,
        "download_failures": [{"name": n, "error": err} for n, err in failures],
        "upstream_md5": {
            "primary_source": primary,
            "entries": len(upstream_md5),
            "verified": verified,
            "mismatched": sorted(mismatched),
            "sources": sorted(set(md5_source.values())),
        },
        "columns": ["name", "bytes", "md5", "sha256", "md5_state"],
        "files": files_rows,
        "extra": side_rows(extra_dir, "_extra", plan.intro),
        "upstream_meta": side_rows(meta_dir, "_upstream", plan.meta),
        "upstream_stray": side_rows(stray_dir, "_upstream/stray", plan.stray),
        "not_mirrored": [{"name": n, "bytes": b, "reason": why} for n, b, why in plan.skipped],
        "subfolders_not_mirrored": plan.subfolders,
    }
    manifests_dir.mkdir(parents=True, exist_ok=True)
    out = manifests_dir / f"{slug}.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    status = "done" if not failures and not missing_ayahs else ("done-with-gaps" if not failures else "partial")
    _update_state(root, slug, {
        "status": status, "updated": _now(), "ayah_files": len(present), "ayah_bytes": manifest["ayah_bytes"],
        "missing_ayahs": len(missing_ayahs), "failures": len(failures), "md5_mismatches": len(mismatched),
    })
    log(f"[{slug}] {status}: {len(present)} files, {_fmt_bytes(manifest['ayah_bytes'])}, "
        f"{verified} md5-verified, {len(mismatched)} mismatched, {len(missing_ayahs)} ayahs absent, {len(failures)} failures")
    return manifest


def _update_state(root: Path, slug: str, entry: dict) -> None:
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "mirror.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    state[slug] = entry
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_state(root: Path) -> dict:
    path = root / "state" / "mirror.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def verify_reciter(reciter: Reciter, root: Path, manifests_dir: Path = MANIFESTS / "audio", log: Log = print) -> Tuple[int, List[str]]:
    """Re-hash the local tree against the committed manifest. Returns (checked, problems)."""
    path = manifests_dir / f"{reciter.slug}.json"
    if not path.is_file():
        return 0, [f"no manifest for {reciter.slug}"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    audio_dir = root / "audio" / reciter.slug
    problems: List[str] = []
    rows = manifest["files"]
    for name, size, md5, sha, _state in rows:
        p = audio_dir / name
        if not p.is_file():
            problems.append(f"missing {name}")
            continue
        if p.stat().st_size != size:
            problems.append(f"size {name}: {p.stat().st_size} != {size}")
            continue
        got_md5, got_sha = hash_file(p)
        if got_sha != sha:
            problems.append(f"sha256 {name}")
    log(f"[{reciter.slug}] verified {len(rows) - len(problems)}/{len(rows)}; problems {len(problems)}")
    return len(rows), problems
