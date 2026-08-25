"""Publish mirrored sets to Hugging Face as one dataset repository per reciter set.

Why one repository per set: the Hub enforces at most 10k entries per folder
and recommends fewer than 100k files per repository. A single set is about
6.3k files, so each set fits comfortably in its own repository while the whole
archive (about 525k files) would not fit in one.

Authentication comes from the HF_TOKEN environment variable or a prior
`hf auth login`; the token is never written to any file in this project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from .registry import MANIFESTS, REPO_ROOT, Reciter

Log = Callable[[str], None]
GITHUB_URL = "https://github.com/Abdalla-Eldoumani/maqra"


def _api():
    try:
        from huggingface_hub import HfApi  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
        raise SystemExit("huggingface_hub is not installed; run: pip install 'maqra[hf]' or pip install huggingface_hub") from exc
    return HfApi()


def dataset_card(reciter: Reciter, manifest: Optional[dict]) -> str:
    lang = [p for p in reciter.language.split("+")]
    size_cat = "1K<n<10K"
    files = manifest["ayah_files"] if manifest else "?"
    mib = f"{manifest['ayah_bytes'] / 1024 ** 2:.0f} MiB" if manifest else "?"
    verified = manifest["upstream_md5"]["verified"] if manifest else "?"
    missing = len(manifest["missing_ayahs"]) if manifest else "?"
    bitrate = f"{reciter.bitrate_kbps} kbps" if reciter.bitrate_kbps else "bitrate not stated upstream"
    yaml_lang = "\n".join(f"  - {code}" for code in lang)
    rights = (REPO_ROOT / "RIGHTS.md").read_text(encoding="utf-8") if (REPO_ROOT / "RIGHTS.md").is_file() else ""
    return f"""---
pretty_name: "Maqra: {reciter.name}"
license: other
license_name: everyayah-mirror-notice
license_link: {GITHUB_URL}/blob/main/RIGHTS.md
language:
{yaml_lang}
tags:
  - quran
  - recitation
  - audio
  - verse-by-verse
  - everyayah
  - maqra
size_categories:
  - {size_cat}
---

# {reciter.name}

Part of [Maqra]({GITHUB_URL}), an open, verified archive of verse-by-verse Qur'an recitations mirrored from [everyayah.com](https://everyayah.com/).

| | |
|---|---|
| Set | `{reciter.slug}` |
| Style | {reciter.style} |
| Riwayah | {reciter.riwayah} |
| Kind | {reciter.kind} |
| Bitrate | {bitrate} |
| Ayah files | {files} ({mib}) |
| Verified against the upstream MD5 list | {verified} |
| Ayahs absent upstream | {missing} |
| Upstream folder | [{reciter.source_folder}]({reciter.source_url}) |

## Files

One MP3 per ayah, named `SSSAAA.mp3` (surah 3 digits, ayah 3 digits). `001001.mp3` is Al-Fatihah 1. Where the set has an intro file per surah it is named `SSS000.mp3`. `_extra/` holds the reciter's standalone isti'adhah and basmala files where upstream ships them; `_upstream/` holds everyayah.com's own checksum lists and notes verbatim.

Direct URL pattern:

```
https://huggingface.co/datasets/{reciter.huggingface_repo}/resolve/main/001001.mp3
```

The per-file MD5 and SHA-256 for this set live in `manifest.json` here and in the Maqra repository under `manifests/audio/{reciter.slug}.json`.

{("## Notes from the survey" + chr(10) + chr(10) + reciter.notes + chr(10)) if reciter.notes else ""}
## Rights

{rights}
"""


def publish_reciter(reciter: Reciter, root: Path, log: Log, namespace: Optional[str] = None,
                    manifests_dir: Path = MANIFESTS / "audio", dry_run: bool = False, workers: Optional[int] = None) -> str:
    repo_id = reciter.huggingface_repo if not namespace else f"{namespace}/{reciter.slug}"
    audio_dir = root / "audio" / reciter.slug
    if not audio_dir.is_dir():
        raise SystemExit(f"{audio_dir} does not exist; run mirror first")
    manifest_path = manifests_dir / f"{reciter.slug}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None

    (audio_dir / "README.md").write_text(dataset_card(reciter, manifest), encoding="utf-8")
    if manifest is not None:
        (audio_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    if dry_run:
        n = sum(1 for _ in audio_dir.rglob("*") if _.is_file())
        log(f"[{reciter.slug}] dry run: would upload {n} files to {repo_id}")
        return repo_id

    api = _api()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    log(f"[{reciter.slug}] uploading {audio_dir} to {repo_id}")
    api.upload_large_folder(
        repo_id=repo_id,
        folder_path=str(audio_dir),
        repo_type="dataset",
        ignore_patterns=["*.part", ".cache/**"],
        num_workers=workers,
        print_report=True,
        print_report_every=120,
    )
    log(f"[{reciter.slug}] uploaded: https://huggingface.co/datasets/{repo_id}")
    return repo_id


def publish_index(root: Path, log: Log, namespace: str = "maqra-project", dry_run: bool = False) -> str:
    """Publish the registry, manifests, and timings as one small dataset repo."""
    repo_id = f"{namespace}/maqra"
    staging = root / "_tmp" / "index-repo"
    if staging.exists():
        import shutil
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    import shutil as _sh
    for rel in ("manifests", "timings", "RIGHTS.md"):
        src = REPO_ROOT / rel
        if src.is_dir():
            _sh.copytree(src, staging / rel)
        elif src.is_file():
            _sh.copy2(src, staging / rel)
    rights = (REPO_ROOT / "RIGHTS.md").read_text(encoding="utf-8") if (REPO_ROOT / "RIGHTS.md").is_file() else ""
    (staging / "README.md").write_text(f"""---
pretty_name: "Maqra index"
license: other
license_name: everyayah-mirror-notice
license_link: {GITHUB_URL}/blob/main/RIGHTS.md
language:
  - ar
tags:
  - quran
  - recitation
  - audio
  - everyayah
  - maqra
---

# Maqra index

The reciter registry, the per-file manifests (MD5 and SHA-256 for every ayah file), and the timing files for every set in [Maqra]({GITHUB_URL}). The audio itself lives in one dataset per reciter set under this namespace; `manifests/reciters.json` lists them.

## Rights

{rights}
""", encoding="utf-8")
    if dry_run:
        log(f"[index] dry run: would upload {staging} to {repo_id}")
        return repo_id
    api = _api()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_folder(repo_id=repo_id, folder_path=str(staging), repo_type="dataset", commit_message="update index")
    log(f"[index] uploaded: https://huggingface.co/datasets/{repo_id}")
    return repo_id


def publish_images(root: Path, log: Log, namespace: str = "maqra-project", dry_run: bool = False) -> str:
    repo_id = f"{namespace}/ayah-images"
    images = root / "images"
    if not images.is_dir():
        raise SystemExit(f"{images} does not exist; run `maqra extras --images` first")
    rights = (REPO_ROOT / "RIGHTS.md").read_text(encoding="utf-8") if (REPO_ROOT / "RIGHTS.md").is_file() else ""
    (images / "README.md").write_text(f"""---
pretty_name: "Maqra: ayah images"
license: other
license_name: everyayah-mirror-notice
license_link: {GITHUB_URL}/blob/main/RIGHTS.md
language:
  - ar
tags:
  - quran
  - images
  - everyayah
  - maqra
---

# Ayah images

Four renderings of every ayah of the Qur'an as served by everyayah.com, named `S_A.ext` (surah, ayah, no padding): `gif/` (QuranText), `jpg/` (QuranText_jpg), `png/` (images_png), `png-hires/` (quranpngs). Part of [Maqra]({GITHUB_URL}).

## Rights

{rights}
""", encoding="utf-8")
    if dry_run:
        log(f"[images] dry run: would upload {images} to {repo_id}")
        return repo_id
    api = _api()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_large_folder(repo_id=repo_id, folder_path=str(images), repo_type="dataset", ignore_patterns=["*.part"], print_report_every=120)
    log(f"[images] uploaded: https://huggingface.co/datasets/{repo_id}")
    return repo_id
