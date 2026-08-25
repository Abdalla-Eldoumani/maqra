import hashlib
from pathlib import Path

from maqra.checksums import hash_file, parse_md5_list


def test_parse_md5_variants():
    text = (
        "\ufeff8b2ad7066151af325f8f9b60722fafb1 *Alafasy_64kbps/001001.mp3\r\n"
        "3823fdbb8cbae87ff0d0b7fe0a85a17e  Alafasy_64kbps/001002.mp3\n"
        "A3CFEF69EADF1741FADDCFED35AC9CAE *001003.mp3\n"
        "0123456789abcdef0123456789abcdef  ./sub\\dir\\001004.mp3\n"
        "not a checksum line\n"
        "\n"
    )
    parsed, ignored = parse_md5_list(text)
    assert parsed == {
        "001001.mp3": "8b2ad7066151af325f8f9b60722fafb1",
        "001002.mp3": "3823fdbb8cbae87ff0d0b7fe0a85a17e",
        "001003.mp3": "a3cfef69eadf1741faddcfed35ac9cae",
        "001004.mp3": "0123456789abcdef0123456789abcdef",
    }
    assert ignored == 1


def test_hash_file(tmp_path: Path):
    p = tmp_path / "x.bin"
    data = b"maqra" * 1000
    p.write_bytes(data)
    md5, sha = hash_file(p)
    assert md5 == hashlib.md5(data).hexdigest()
    assert sha == hashlib.sha256(data).hexdigest()
