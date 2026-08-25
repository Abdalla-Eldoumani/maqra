import json
import re
from collections import Counter

from maqra.registry import MANIFESTS, ayah_counts, expected_ayah_files, load_reciters, load_surahs, select, split_ayah_name

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_registry_integrity():
    reciters = load_reciters()
    assert len(reciters) == 80
    slugs = [r.slug for r in reciters]
    assert len(set(slugs)) == len(slugs), "duplicate slugs"
    folders = [r.source_folder for r in reciters]
    assert len(set(folders)) == len(folders), "duplicate source folders"
    for r in reciters:
        assert SLUG.match(r.slug), r.slug
        assert r.source_url.startswith("https://everyayah.com/data/") and r.source_url.endswith("/")
        assert r.style in ("murattal", "mujawwad", "muallim", "unknown")
        assert r.riwayah in ("hafs", "warsh")
        assert r.kind in ("recitation", "translation", "mixed")
        assert r.huggingface_repo == f"maqra-project/{r.slug}"
        assert r.github_release_tag == r.slug


def test_bitrate_in_slug_matches_folder():
    for r in load_reciters():
        if r.bitrate_kbps:
            assert f"{r.bitrate_kbps}kbps" in r.slug, (r.slug, r.bitrate_kbps)


def test_excluded_folders_are_documented():
    doc = json.loads((MANIFESTS / "reciters.json").read_text(encoding="utf-8"))
    excluded = {e["source_folder"] for e in doc["excluded_upstream_folders"]}
    assert len(excluded) == 6
    live = {r.source_folder for r in load_reciters()}
    assert not (excluded & live)


def test_survey_file_covers_every_folder():
    rows = [l.split("|")[0] for l in (MANIFESTS / "upstream-folders.psv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    doc = json.loads((MANIFESTS / "reciters.json").read_text(encoding="utf-8"))
    all_folders = {r["source_folder"] for r in doc["reciters"]} | {e["source_folder"] for e in doc["excluded_upstream_folders"]}
    assert set(rows) == all_folders
    assert len(rows) == 86


def test_surahs_sum_to_6236():
    surahs = load_surahs()
    assert len(surahs) == 114
    assert sum(s["ayah_count"] for s in surahs) == 6236
    assert surahs[0]["name_en"] == "Al-Fatihah" and surahs[0]["ayah_count"] == 7
    assert surahs[8]["ayah_count"] == 129 and surahs[113]["ayah_count"] == 6


def test_expected_ayah_files():
    names = expected_ayah_files(ayah_counts())
    assert len(names) == 6236
    assert names[0] == "001001.mp3" and names[-1] == "114006.mp3"
    assert "009000.mp3" not in names and "002286.mp3" in names
    assert split_ayah_name("002286.mp3") == (2, 286)
    assert split_ayah_name("audhubillah.mp3") is None


def test_select_by_slug_and_key():
    reciters = load_reciters()
    chosen = select(reciters, only=["alafasy"])
    assert {r.slug for r in chosen} == {"mishari-alafasy-64kbps", "mishari-alafasy-128kbps"}
    chosen = select(reciters, only=["mishari-alafasy-64kbps"], skip=["alafasy"])
    assert chosen == []
    counts = Counter(r.reciter_key for r in reciters)
    assert counts["al-husary"] == 5
