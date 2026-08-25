import hashlib
import json
from pathlib import Path

import pytest

from maqra.mirror import mirror_reciter, read_state, verify_reciter
from maqra.package import build_surah_zips
from maqra.registry import Reciter
from tests.conftest import TEST_COUNTS, make_reciter_folder


def _reciter(folder: str, slug: str = "test-set-64kbps", **kw) -> Reciter:
    base = dict(
        slug=slug, name="Test Reciter", reciter_key="test", style="murattal", riwayah="hafs", language="ar",
        kind="recitation", bitrate_kbps=64, source_folder=folder, source_url="http://example/" + folder + "/",
        upstream_checksum_files=["000_checksum.md5"], upstream_zip="000_versebyverse.zip", status="complete", notes="",
        github_release_tag=slug, huggingface_repo="maqra-project/" + slug,
    )
    base.update(kw)
    return Reciter(**base)


def _run(upstream, tmp_path, folder, reciter, **kw):
    server, docroot = upstream
    root = tmp_path / "root"
    manifests = tmp_path / "manifests"
    logs = []
    manifest = mirror_reciter(reciter, root, workers=4, manifests_dir=manifests, log=logs.append, counts=TEST_COUNTS,
                              zip_min_bytes=0, zip_min_missing=1, **kw)
    return root, manifests, manifest, logs


def test_mirror_via_zip_with_stale_entry_and_md5(upstream, tmp_path):
    server, docroot = upstream
    live = make_reciter_folder(docroot, "Test_64kbps", stale_in_zip="002002.mp3")
    reciter = _reciter("Test_64kbps")
    root, manifests, manifest, logs = _run(upstream, tmp_path, "Test_64kbps", reciter)

    audio = root / "audio" / reciter.slug
    for name, data in live.items():
        assert (audio / name).read_bytes() == data, name
    assert manifest["bulk_zip_used"] is True
    assert manifest["ayah_files"] == len(live)
    assert manifest["missing_ayahs"] == [] and manifest["missing_on_upstream"] == []
    assert manifest["upstream_md5"]["verified"] == len(live)
    assert manifest["upstream_md5"]["mismatched"] == []
    assert manifest["download_failures"] == []
    # the stale zip copy of 002002 was rejected and fetched loose
    assert any(p == "/data/Test_64kbps/002002.mp3" for _m, p in server.requests)
    # intro + metadata mirrored verbatim
    assert (audio / "_extra" / "bismillah.mp3").is_file()
    assert (audio / "_upstream" / "000_checksum.md5").is_file()
    assert (audio / "_upstream" / "000_readme.txt").read_text() == "test readme\n"
    assert manifest["subfolders_not_mirrored"] == ["PageMp3s"]
    assert manifest["not_mirrored"] == []
    # manifest rows carry both digests and the md5 state
    row = next(r for r in manifest["files"] if r[0] == "001001.mp3")
    assert row[1] == len(live["001001.mp3"])
    assert row[2] == hashlib.md5(live["001001.mp3"]).hexdigest()
    assert row[3] == hashlib.sha256(live["001001.mp3"]).hexdigest()
    assert row[4] == "upstream-match"
    # the zip was deleted after use
    assert not (root / "_tmp" / f"{reciter.slug}.zip").exists()
    assert read_state(root)[reciter.slug]["status"] == "done"
    # verify passes against the written manifest
    checked, problems = verify_reciter(reciter, root, manifests_dir=manifests, log=logs.append)
    assert checked == len(live) and problems == []


def test_mirror_loose_only_with_missing_and_retry(upstream, tmp_path):
    server, docroot = upstream
    live = make_reciter_folder(docroot, "Loose_32kbps", with_zip=False, with_md5=False, missing={"001003.mp3", "003002.mp3"})
    server.fail_first["/data/Loose_32kbps/001001.mp3"] = 2  # two 503s, then success
    reciter = _reciter("Loose_32kbps", slug="loose-32kbps", upstream_checksum_files=[], upstream_zip=None)
    root, manifests, manifest, logs = _run(upstream, tmp_path, "Loose_32kbps", reciter)

    assert manifest["bulk_zip_used"] is False
    assert manifest["ayah_files"] == len(live)
    assert manifest["missing_ayahs"] == ["001003", "003002"]
    assert manifest["missing_on_upstream"] == ["001003", "003002"]
    assert manifest["upstream_md5"]["entries"] == 0
    assert all(r[4] == "no-upstream-md5" for r in manifest["files"])
    assert manifest["download_failures"] == []
    assert read_state(root)[reciter.slug]["status"] == "done-with-gaps"
    gets = [p for m, p in server.requests if p == "/data/Loose_32kbps/001001.mp3"]
    assert len(gets) == 3


def test_mirror_is_idempotent_and_resumes(upstream, tmp_path):
    server, docroot = upstream
    live = make_reciter_folder(docroot, "Idem_64kbps", with_zip=False)
    reciter = _reciter("Idem_64kbps", slug="idem-64kbps", upstream_zip=None)
    root, manifests, manifest, logs = _run(upstream, tmp_path, "Idem_64kbps", reciter)
    first_requests = len(server.requests)
    # corrupt one file and truncate another; a second run repairs exactly those
    audio = root / "audio" / reciter.slug
    (audio / "001002.mp3").write_bytes(b"corrupt-but-same-size"[: len(live["001002.mp3"])].ljust(len(live["001002.mp3"]), b"x"))
    (audio / "001004.mp3").write_bytes(live["001004.mp3"][:10])
    manifest2 = mirror_reciter(reciter, root, workers=2, manifests_dir=manifests, log=logs.append, counts=TEST_COUNTS)
    assert (audio / "001002.mp3").read_bytes() == live["001002.mp3"]  # md5 mismatch repaired
    assert (audio / "001004.mp3").read_bytes() == live["001004.mp3"]  # size mismatch repaired
    assert manifest2["upstream_md5"]["mismatched"] == []
    new_gets = [p for m, p in server.requests[first_requests:] if m == "GET" and p.endswith(".mp3")]
    assert sorted(new_gets) == ["/data/Idem_64kbps/001002.mp3", "/data/Idem_64kbps/001004.mp3"]


def test_persistent_md5_mismatch_is_recorded_not_looped(upstream, tmp_path):
    server, docroot = upstream
    live = make_reciter_folder(docroot, "Drift_64kbps", with_zip=False)
    # upstream md5 list is stale for one file: it lists a digest that no live file has
    md5_path = docroot / "data" / "Drift_64kbps" / "000_checksum.md5"
    text = md5_path.read_text().replace(hashlib.md5(live["002001.mp3"]).hexdigest(), "0" * 32)
    md5_path.write_text(text)
    reciter = _reciter("Drift_64kbps", slug="drift-64kbps", upstream_zip=None)
    root, manifests, manifest, logs = _run(upstream, tmp_path, "Drift_64kbps", reciter)
    assert manifest["upstream_md5"]["mismatched"] == ["002001.mp3"]
    row = next(r for r in manifest["files"] if r[0] == "002001.mp3")
    assert row[4] == "upstream-mismatch"
    assert (root / "audio" / reciter.slug / "002001.mp3").read_bytes() == live["002001.mp3"]
    gets = [p for m, p in server.requests if m == "GET" and p == "/data/Drift_64kbps/002001.mp3"]
    assert len(gets) == 2  # initial fetch plus exactly one re-download


def test_package_builds_one_zip_per_surah(upstream, tmp_path):
    server, docroot = upstream
    live = make_reciter_folder(docroot, "Pack_64kbps", with_zip=False)
    reciter = _reciter("Pack_64kbps", slug="pack-64kbps", upstream_zip=None)
    root, manifests, manifest, logs = _run(upstream, tmp_path, "Pack_64kbps", reciter)
    out = build_surah_zips(reciter, root, tmp_path / "rel", logs.append, manifests_dir=manifests)
    rel = tmp_path / "rel" / reciter.slug
    zips = sorted(p.name for p in rel.glob("*.zip"))
    assert zips == ["001.zip", "002.zip", "003.zip", "extras.zip"]
    import zipfile
    with zipfile.ZipFile(rel / "001.zip") as zf:
        names = sorted(zf.namelist())
        assert names == [f"001{a:03d}.mp3" for a in range(0, TEST_COUNTS[1] + 1)]
        assert all(i.compress_type == zipfile.ZIP_STORED for i in zf.infolist())
        assert zf.read("001001.mp3") == live["001001.mp3"]
    sums = (rel / "checksums.sha256").read_text().splitlines()
    assert len(sums) == 4 + 2
    assert (rel / "NOTICE.txt").read_text().startswith("Maqra: Test Reciter")
    # second run reuses the zips
    out2 = build_surah_zips(reciter, root, tmp_path / "rel", logs.append, manifests_dir=manifests)
    assert all(z["reused"] for z in out2["zips"] if z["surah"] is not None)
