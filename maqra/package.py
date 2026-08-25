"""Build release packages from a mirrored reciter tree.

One zip per surah (001.zip ... 114.zip), stored without compression because MP3
does not compress and a stored zip streams and seeks cleanly. Each surah zip
carries that surah's SSSAAA.mp3 files plus the SSS000.mp3 intro file when the
reciter has one. Alongside: checksums.sha256 for the zips, the reciter's
manifest, and a plain-text notice.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Callable, Dict, List

from .checksums import sha256_file
from .registry import MANIFESTS, REPO_ROOT, Reciter, split_ayah_name

Log = Callable[[str], None]
RELEASE_FILE_LIMIT = 2 * 1024 ** 3 - 1024 ** 2  # GitHub: each release asset under 2 GiB


def _notice_text(reciter: Reciter) -> str:
    rights = (REPO_ROOT / "RIGHTS.md")
    body = rights.read_text(encoding="utf-8") if rights.is_file() else ""
    head = (
        f"Maqra: {reciter.name}\n"
        f"Set: {reciter.slug}\n"
        f"Source: {reciter.source_url}\n"
        f"Files are named SSSAAA.mp3 (surah, ayah). SSS000.mp3 is the intro file where present.\n\n"
    )
    return head + body


def build_surah_zips(reciter: Reciter, root: Path, out_root: Path, log: Log, manifests_dir: Path = MANIFESTS / "audio") -> dict:
    audio_dir = root / "audio" / reciter.slug
    out_dir = out_root / reciter.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifests_dir / f"{reciter.slug}.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no manifest for {reciter.slug}; run mirror first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    by_surah: Dict[int, List[str]] = {}
    for name, _size, _md5, _sha, _state in manifest["files"]:
        parts = split_ayah_name(name)
        if not parts:
            continue
        by_surah.setdefault(parts[0], []).append(name)

    built: List[dict] = []
    for surah in sorted(by_surah):
        names = sorted(by_surah[surah])
        target = out_dir / f"{surah:03d}.zip"
        expected_bytes = sum(int((audio_dir / n).stat().st_size) for n in names)
        if target.is_file():
            # Cheap idempotence check: same member count and total uncompressed size.
            with zipfile.ZipFile(target) as zf:
                infos = zf.infolist()
                if len(infos) == len(names) and sum(i.file_size for i in infos) == expected_bytes:
                    built.append({"surah": surah, "zip": target.name, "files": len(names), "bytes": target.stat().st_size, "reused": True})
                    continue
        tmp = target.with_name(target.name + ".part")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for n in names:
                zf.write(audio_dir / n, arcname=n)
        tmp.replace(target)
        size = target.stat().st_size
        if size > RELEASE_FILE_LIMIT:
            log(f"[{reciter.slug}] WARNING {target.name} is {size} bytes, over the GitHub asset limit")
        built.append({"surah": surah, "zip": target.name, "files": len(names), "bytes": size, "reused": False})

    # Extras zip: intro files and upstream metadata, small.
    extras = [row for row in manifest.get("extra", [])] + [row for row in manifest.get("upstream_meta", [])]
    if extras:
        target = out_dir / "extras.zip"
        tmp = target.with_name(target.name + ".part")
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel, *_rest in extras:
                p = audio_dir / rel
                if p.is_file():
                    zf.write(p, arcname=rel)
        tmp.replace(target)
        built.append({"surah": None, "zip": target.name, "files": len(extras), "bytes": target.stat().st_size, "reused": False})

    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (out_dir / "NOTICE.txt").write_text(_notice_text(reciter), encoding="utf-8")

    lines = []
    for item in built:
        lines.append(f"{sha256_file(out_dir / item['zip'])}  {item['zip']}")
    for extra_name in ("manifest.json", "NOTICE.txt"):
        lines.append(f"{sha256_file(out_dir / extra_name)}  {extra_name}")
    (out_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(i["bytes"] for i in built)
    log(f"[{reciter.slug}] packaged {len(built)} zips, {total / 1024 ** 2:.0f} MiB")
    return {"slug": reciter.slug, "zips": built, "bytes": total}
