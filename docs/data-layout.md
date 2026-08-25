# Data layout

## The data root

`data/` next to the repository by default; `--root` or `MAQRA_ROOT` moves it. Nothing under it is committed.

```
data/
  audio/<slug>/
    001001.mp3 ... 114006.mp3     one file per ayah, upstream names kept exactly
    001000.mp3 ...                intro files where the set has them
    _extra/                       audhubillah.mp3, bismillah.mp3 (standalone upstream files)
    _upstream/                    000_checksum.md5, readmes, notes, verbatim
    _upstream/stray/              odd small files found beside the set upstream
    README.md, manifest.json      written by `publish-hf`, uploaded with the set
  timings/_upstream/*.zip         the 27 timing zips and their three text notes, verbatim
  images/gif|jpg|png|png-hires/   the four ayah image sets, S_A.ext
  upstream/                       recitations.js, the site pages, the site-level intro files
  tools/                          the legacy tool zips
  extras/                         the Shaatree+Walk offline zip (optional)
  releases/<slug>/                001.zip ... 114.zip, extras.zip, manifest.json, checksums.sha256, NOTICE.txt
  state/mirror.json               per-set status, resumable
  state/logs/                     one log per run
  _tmp/                           bulk zips in flight; deleted after extraction
```

## Names

Ayah files keep everyayah.com's `SSSAAA.mp3` scheme: surah then ayah, both zero-padded to three digits. It sorts correctly, it is what every existing everyayah client already expects, and it makes any mirror interchangeable with the original by swapping the base URL.

Sets use canonical slugs instead of upstream folder names because the upstream names are inconsistent (`MaherAlMuaiqly128kbps` next to `Maher_AlMuaiqly_64kbps`, `Menshawi` next to `Minshawy`, a folder with spaces). The mapping is explicit in `manifests/reciters.json` (`source_folder`) and in every manifest, so nothing is lost. See `docs/adr/0002-canonical-slugs.md`.

## Manifests

`manifests/audio/<slug>.json`, one per set, written by `maqra mirror`:

```json
{
  "schema_version": 1,
  "slug": "mishari-alafasy-64kbps",
  "name": "Mishari Rashid Alafasy",
  "source_folder": "Alafasy_64kbps",
  "source_url": "https://everyayah.com/data/Alafasy_64kbps/",
  "mirrored_at": "2026-08-26T03:12:44+00:00",
  "bulk_zip_used": true,
  "ayah_files": 6349,
  "ayah_bytes": 860745123,
  "expected_ayah_files": 6236,
  "missing_ayahs": [],
  "missing_on_upstream": [],
  "download_failures": [],
  "upstream_md5": {"primary_source": "000_checksum.md5", "entries": 6350, "verified": 6349, "mismatched": [], "sources": ["000_checksum.md5"]},
  "columns": ["name", "bytes", "md5", "sha256", "md5_state"],
  "files": [["001000.mp3", 49109, "…", "…", "upstream-match"], ["001001.mp3", 49109, "…", "…", "upstream-match"]],
  "extra": [["_extra/bismillah.mp3", 51200, "…", "…"]],
  "upstream_meta": [["_upstream/000_checksum.md5", 380928, "…", "…"]],
  "upstream_stray": [],
  "not_mirrored": [{"name": "000_versebyverse.zip", "bytes": 864907558, "reason": "bulk archive; the per-ayah files are mirrored instead"}],
  "subfolders_not_mirrored": ["PageMp3s", "merged", "zips"]
}
```

`files` is a list of rows rather than objects to keep 6,350 entries under a megabyte. `md5_state` is per file: `upstream-match`, `upstream-mismatch` (the live file differs from everyayah.com's list; the live file is kept and the disagreement recorded), or `no-upstream-md5`.

`missing_ayahs` lists ayahs absent locally as `SSSAAA`; `missing_on_upstream` lists those absent from the live listing. When the two are equal the mirror is complete relative to upstream.

## Timings

`timings/<set>.json`, one per upstream zip, written by `maqra extras --timings` (26 sets; one upstream zip holds loose MP3s rather than timings and is skipped with a reason in the extras report):

```json
{
  "schema_version": 2,
  "source_zip": "Husary_Timings.zip",
  "unit": "milliseconds",
  "surahs_covered": [1, 2, "..."],
  "surahs": {"1": {"ayahs": 7, "segments": [11705, 18048, 22513, 27115, 33956, 39337, 54260], "extra_segments": 0},
             "2": {"ayahs": 286, "segments": ["..."], "extra_segments": 1}},
  "parts": {"2": [{"part": "a", "ayah_range": [1, 117], "segments": ["..."]}]},
  "upstream_notes": {"details.txt": "..."},
  "warnings": []
}
```

Each value is where one segment of the full-surah recording ends. `extra_segments` is segments minus ayahs: +1 means the recording opens with the isti'adhah and basmala as its own segment (everyayah.com's own readme for the Ash-Shatri set says to drop that first line, about 8000 ms, to make the numbering match the ayahs); 0 means no intro segment; about one extra per ayah marks the two sets that interleave a spoken translation; negative means the upstream file stops early. `parts` carries recordings that upstream split into several audio files (`002a.txt`, `002b118-220.txt`), with offsets relative to each part. The upstream naming variants (`001.txt`, `054.TXT`, `Chapter001.txt`, `002a.txt`, `002a001-117.txt`) all fold into this one shape.

The file stem is the zip name lowercased with runs of non-alphanumerics collapsed to a hyphen. Timing sets are not keyed by slug because upstream names them by reciter, not by bitrate, and one timing set applies to every bitrate of that recording.

## Registry fields

`manifests/reciters.json`, per set: `slug`, `name`, `reciter_key`, `style` (murattal, mujawwad, muallim, unknown), `riwayah` (hafs, warsh), `language` (`ar`, `en`, `fa`, `ur`, `az`, `bs`, or `ar+en`), `kind` (recitation, translation, mixed), `bitrate_kbps`, `source_folder`, `source_url`, `upstream_checksum_files`, `upstream_zip`, `upstream_subfolders`, `survey_2026_08_25` (file count and rounded sizes seen), `status` (complete, incomplete), `notes`, `github_release_tag`, `huggingface_repo`. The `excluded_upstream_folders` list names the six folders that are not mirrored as sets, with reasons.
