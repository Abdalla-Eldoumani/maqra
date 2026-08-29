"""Publish packaged sets as GitHub Releases through the gh CLI.

One release per reciter set, tagged with the set's slug. Assets: 001.zip ...
114.zip (one per surah, each far below GitHub's 2 GiB per-asset limit),
extras.zip, manifest.json, checksums.sha256, NOTICE.txt. Uploads skip assets
that already exist, so an interrupted run resumes.

gh must be installed and authenticated (`gh auth status`). No token is read or
stored by this module.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional

from .registry import MANIFESTS, REPO_ROOT, Reciter

Log = Callable[[str], None]
DEFAULT_REPO = "Abdalla-Eldoumani/maqra"
BATCH = 25


def _gh(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    if shutil.which("gh") is None:
        raise SystemExit("gh (GitHub CLI) is not installed or not on PATH")
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def check_auth() -> None:
    res = _gh(["auth", "status"], check=False)
    if res.returncode != 0:
        raise SystemExit("gh is not authenticated; run `gh auth login` first\n" + res.stderr)


def release_notes(reciter: Reciter, manifest: Optional[dict]) -> str:
    rights = (REPO_ROOT / "RIGHTS.md").read_text(encoding="utf-8") if (REPO_ROOT / "RIGHTS.md").is_file() else ""
    files = manifest["ayah_files"] if manifest else "?"
    mib = f"{manifest['ayah_bytes'] / 1024 ** 2:.0f} MiB" if manifest else "?"
    verified = manifest["upstream_md5"]["verified"] if manifest else "?"
    missing = len(manifest["missing_ayahs"]) if manifest else "?"
    bitrate = f"{reciter.bitrate_kbps} kbps" if reciter.bitrate_kbps else "bitrate not stated upstream"
    notes = (
        f"Verse-by-verse recitation mirrored from [everyayah.com]({reciter.source_url}).\n\n"
        f"Set `{reciter.slug}`: {reciter.style}, riwayah {reciter.riwayah}, {bitrate}. "
        f"{files} ayah files, {mib}, {verified} verified against the upstream MD5 list, {missing} ayahs absent upstream.\n\n"
        "Assets: one zip per surah (`001.zip` to `114.zip`, files inside named `SSSAAA.mp3`), `extras.zip` (intro files and upstream notes), "
        "`manifest.json` (MD5 and SHA-256 for every file), `checksums.sha256` (for the assets here), `NOTICE.txt`.\n\n"
        f"Also on Hugging Face: https://huggingface.co/datasets/{reciter.huggingface_repo}\n\n"
    )
    if reciter.notes:
        notes += f"Survey notes: {reciter.notes}\n\n"
    return notes + "## Rights\n\n" + rights


def existing_assets(tag: str, repo: str) -> Optional[List[str]]:
    res = _gh(["release", "view", tag, "-R", repo, "--json", "assets"], check=False)
    if res.returncode != 0:
        return None
    data = json.loads(res.stdout or "{}")
    return [a["name"] for a in data.get("assets", [])]


def publish_reciter(reciter: Reciter, releases_root: Path, log: Log, repo: str = DEFAULT_REPO,
                    manifests_dir: Path = MANIFESTS / "audio", dry_run: bool = False) -> str:
    out_dir = releases_root / reciter.slug
    if not out_dir.is_dir():
        raise SystemExit(f"{out_dir} does not exist; run package first")
    manifest_path = manifests_dir / f"{reciter.slug}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    tag = reciter.github_release_tag
    title = f"{reciter.name} ({reciter.bitrate_kbps} kbps)" if reciter.bitrate_kbps else reciter.name

    assets = sorted(p for p in out_dir.iterdir() if p.is_file() and not p.name.endswith(".part"))
    if dry_run:
        log(f"[{reciter.slug}] dry run: release {tag} on {repo} with {len(assets)} assets")
        return tag

    notes_path = out_dir / "release-notes.md"
    notes_path.write_text(release_notes(reciter, manifest), encoding="utf-8")
    have = existing_assets(tag, repo)
    if have is None:
        log(f"[{reciter.slug}] creating release {tag}")
        _gh(["release", "create", tag, "-R", repo, "--title", title, "--notes-file", str(notes_path), "--latest=false"])
        have = []
        time.sleep(5)  # a just-created release can briefly reject uploads
    else:
        _gh(["release", "edit", tag, "-R", repo, "--title", title, "--notes-file", str(notes_path)], check=False)

    todo = [p for p in assets if p.name not in have and p.name != "release-notes.md"]
    log(f"[{reciter.slug}] {len(have)} assets present, {len(todo)} to upload")
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        _upload_batch(tag, repo, batch, log, reciter.slug)
        log(f"[{reciter.slug}] uploaded {min(i + BATCH, len(todo))}/{len(todo)}")
    return tag


def _upload_batch(tag: str, repo: str, batch: List[Path], log: Log, slug: str, attempts: int = 4) -> None:
    """Upload one batch with retries. --clobber makes a retry safe when the
    failed attempt landed only part of the batch. The real gh error is printed,
    not swallowed."""
    last = None
    for attempt in range(1, attempts + 1):
        res = _gh(["release", "upload", tag, "-R", repo, "--clobber", *[str(p) for p in batch]], check=False)
        if res.returncode == 0:
            return
        last = res
        detail = (res.stderr or res.stdout or "").strip()
        log(f"[{slug}] upload attempt {attempt}/{attempts} failed: {detail[:400]}")
        time.sleep(15 * attempt)
    raise SystemExit(f"[{slug}] upload failed after {attempts} attempts; last gh error:\n" + ((last.stderr or last.stdout or "").strip()))
