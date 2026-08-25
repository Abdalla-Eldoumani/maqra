import json
import zipfile
from pathlib import Path

from maqra.extras import convert_timings, mirror_folder_flat, parse_timing_zip


def _timing_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("001.txt", "6054\r\n15993\r\n28555\r\n")
        zf.writestr("Husary/002.txt", "5122\n15502\n\n29737\n")
        zf.writestr("003.TXT", "abc\n1000\n")
        zf.writestr("Chapter004.txt", "10\n20\n")
        zf.writestr("005a.txt", "1\n2\n")
        zf.writestr("005b006-010.txt", "3\n4\n")
        zf.writestr("details.txt", "from example.org")
        zf.writestr("000_disclaimer.txt", "(C) VerseByVerseQuran.com")
        zf.writestr("readme.htm", "<p>ignored</p>")


def test_parse_timing_zip(tmp_path: Path):
    zp = tmp_path / "Husary_Timings.zip"
    _timing_zip(zp)
    whole, parts, notes, warnings = parse_timing_zip(zp)
    assert whole == {1: [6054, 15993, 28555], 2: [5122, 15502, 29737], 3: [1000], 4: [10, 20]}
    assert parts == {5: [{"part": "a", "ayah_range": None, "segments": [1, 2]}, {"part": "b", "ayah_range": [6, 10], "segments": [3, 4]}]}
    assert notes == {"details.txt": "from example.org", "000_disclaimer.txt": "(C) VerseByVerseQuran.com"}
    assert len(warnings) == 2
    assert any("readme.htm" in w for w in warnings)
    assert any("non-numeric" in w for w in warnings)


def test_convert_timings_writes_one_json_per_zip(tmp_path: Path):
    src = tmp_path / "up"
    src.mkdir()
    _timing_zip(src / "Husary_Timings.zip")
    _timing_zip(src / "Abu Bakr Ash-Shaatree.zip")
    with zipfile.ZipFile(src / "Not Timings.zip", "w") as zf:
        zf.writestr("010.mp3", b"\x00" * 10)
    out = tmp_path / "timings"
    index = convert_timings(src, out, lambda m: None, counts={1: 3, 2: 2, 3: 1, 4: 2, 5: 10})
    names = sorted(p.name for p in out.glob("*.json"))
    assert names == ["abu-bakr-ash-shaatree.json", "husary-timings.json"]
    doc = json.loads((out / "husary-timings.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == 2 and doc["unit"] == "milliseconds"
    assert doc["surahs"]["1"] == {"ayahs": 3, "segments": [6054, 15993, 28555], "extra_segments": 0}
    assert doc["surahs"]["2"]["extra_segments"] == 1
    assert doc["parts"]["5"][1]["ayah_range"] == [6, 10]
    assert doc["surahs_covered"] == [1, 2, 3, 4, 5]
    assert doc["upstream_notes"]["details.txt"] == "from example.org"
    assert doc["source_zip"] == "Husary_Timings.zip"
    assert "everyayah.com" in doc["license_note"]
    assert [i.get("surahs") for i in index if not i.get("skipped")] == [5, 5]
    assert [i["source_zip"] for i in index if i.get("skipped")] == ["Not Timings.zip"]


def test_mirror_folder_flat_skips_and_resumes(upstream, tmp_path: Path):
    server, docroot = upstream
    folder = docroot / "data" / "tools"
    folder.mkdir(parents=True)
    (folder / "split.zip").write_bytes(b"Z" * 500)
    (folder / "mp3splt.exe").write_bytes(b"M" * 300)
    dest = tmp_path / "out"
    logs = []
    summary = mirror_folder_flat("tools", dest, 2, logs.append, skip=lambda n: "exe" if n.endswith(".exe") else None)
    assert summary["fetched"] == 1 and summary["failures"] == []
    assert summary["skipped"] == [{"name": "mp3splt.exe", "bytes": 300, "reason": "exe"}]
    assert (dest / "split.zip").stat().st_size == 500 and not (dest / "mp3splt.exe").exists()
    before = len(server.requests)
    summary2 = mirror_folder_flat("tools", dest, 2, logs.append, skip=lambda n: "exe" if n.endswith(".exe") else None)
    assert summary2["fetched"] == 0
    assert [p for m, p in server.requests[before:] if m == "GET"] == ["/data/tools/"]
