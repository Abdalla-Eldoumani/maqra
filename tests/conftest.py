from __future__ import annotations

import hashlib
import json
import os
import random
import zipfile
from pathlib import Path

import pytest

from tests.fakeupstream import FakeUpstream

TEST_COUNTS = {1: 7, 2: 3, 3: 2}  # a tiny "Qur'an" for the mirror tests


def make_reciter_folder(base: Path, folder: str, *, with_zip: bool = True, with_md5: bool = True,
                        stale_in_zip: str | None = None, missing: set[str] | None = None, seed: int = 1) -> dict:
    """Create a fake upstream reciter folder. Returns {name: bytes} of the live files."""
    rng = random.Random(seed)
    d = base / "data" / folder
    d.mkdir(parents=True, exist_ok=True)
    live: dict[str, bytes] = {}
    for s, n in TEST_COUNTS.items():
        for a in range(0, n + 1):
            name = f"{s:03d}{a:03d}.mp3"
            if missing and name in missing:
                continue
            live[name] = bytes(rng.getrandbits(8) for _ in range(rng.randint(200, 2000)))
            (d / name).write_bytes(live[name])
    (d / "bismillah.mp3").write_bytes(b"BISMILLAH" * 20)
    (d / "000_readme.txt").write_text("test readme\n")
    if with_md5:
        lines = [f"{hashlib.md5(b).hexdigest()} *{folder}/{name}" for name, b in sorted(live.items())]
        lines.append(f"{hashlib.md5(b'BISMILLAH' * 20).hexdigest()} *{folder}/bismillah.mp3")
        (d / "000_checksum.md5").write_text("\r\n".join(lines) + "\r\n")
    if with_zip:
        with zipfile.ZipFile(d / "000_versebyverse.zip", "w") as zf:
            for name, b in live.items():
                payload = b
                if stale_in_zip == name:
                    payload = b + b"STALE"  # different size: the zip copy must be rejected
                zf.writestr(f"{folder}/{name}", payload)
    (d / "PageMp3s").mkdir(exist_ok=True)
    return live


@pytest.fixture
def upstream(tmp_path: Path, monkeypatch):
    server = FakeUpstream(tmp_path / "srv")
    base = server.start()
    monkeypatch.setenv("MAQRA_UPSTREAM_BASE", base + "data/")
    monkeypatch.setenv("MAQRA_SITE_BASE", base)
    yield server, tmp_path / "srv"
    server.stop()


@pytest.fixture
def small_surahs(tmp_path: Path):
    p = tmp_path / "surahs.json"
    p.write_text(json.dumps({"surahs": [{"number": k, "ayah_count": v} for k, v in TEST_COUNTS.items()]}))
    return p
