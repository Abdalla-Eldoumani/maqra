from pathlib import Path

from maqra.listing import Entry, parse_listing, parse_size_text, folder_url, file_url

FIXTURE = Path(__file__).parent / "fixtures" / "listing_xml.html"


def test_parse_real_listing_fixture():
    entries = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    names = [e.name for e in entries]
    assert names == ["Arabic", "English_AlHilali", "English_Shakir", "muhammad_hamidullah-french",
                     "transliteration_english", "Config.xml", "readme.txt"]
    dirs = [e for e in entries if e.is_dir]
    files = [e for e in entries if not e.is_dir]
    assert len(dirs) == 5 and all(e.size is None for e in dirs)
    assert {e.name: e.size for e in files} == {"Config.xml": 6927, "readme.txt": 86}
    assert files[0].modified == "2023-01-18T02:38:06"
    assert files[0].href == "/data/XML/Config.xml"


def test_parent_row_is_dropped():
    entries = parse_listing(FIXTURE.read_text(encoding="utf-8"))
    assert all(e.name != ".." for e in entries)


def test_size_text_fallback():
    assert parse_size_text("86 bytes") == 86
    assert parse_size_text("6 KB") == 6 * 1024
    assert parse_size_text("824 MB") == 824 * 1024 ** 2
    assert parse_size_text("1 GB") == 1024 ** 3
    assert parse_size_text("\u2014") is None


def test_urls_are_percent_encoded(monkeypatch):
    monkeypatch.delenv("MAQRA_UPSTREAM_BASE", raising=False)
    assert folder_url("warsh/warsh_Abdul_Basit_128kbps") == "https://everyayah.com/data/warsh/warsh_Abdul_Basit_128kbps/"
    assert file_url("Abu Bakr Ash-Shaatree_128kbps", "001001.mp3") == "https://everyayah.com/data/Abu%20Bakr%20Ash-Shaatree_128kbps/001001.mp3"
    assert file_url("timings_files", "Abu Bakr Ash-Shatree Fix 007.txt").endswith("/timings_files/Abu%20Bakr%20Ash-Shatree%20Fix%20007.txt")
