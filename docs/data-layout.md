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
  timings/_upstream/*.zip         the 30 timing zips, verbatim
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

`timings/<set>.json`, one per upstream zip, written by `maqra extras --timings`:

```json
{
  "schema_version": 1,
  "source_zip": "Husary_Timings.zip",
  "unit": "milliseconds",
  "surahs": {"1": [6054, 15993, 28555, 44632, 66760, 85974, 105342], "2": ["…"]},
  "warnings": []
}
```

The file stem is the zip name lowercased with runs of non-alphanumerics collapsed to a hyphen. The timing sets are not keyed by slug because upstream names them by reciter, not by bitrate, and one timing set applies to every bitrate of that recording.

## Registry fields

`manifests/reciters.json`, per set: `slug`, `name`, `reciter_key`, `style` (murattal, mujawwad, muallim, unknown), `riwayah` (hafs, warsh), `language` (`ar`, `en`, `fa`, `ur`, `az`, `bs`, or `ar+en`), `kind` (recitation, translation, mixed), `bitrate_kbps`, `source_folder`, `source_url`, `upstream_checksum_files`, `upstream_zip`, `upstream_subfolders`, `survey_2026_08_25` (file count and rounded sizes seen), `status` (complete, incomplete), `notes`, `github_release_tag`, `huggingface_repo`. The `excluded_upstream_folders` list names the six folders that are not mirrored as sets, with reasons.
