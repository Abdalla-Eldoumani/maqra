# Maqra

An open, verified archive of verse-by-verse Qur'an recitations: every ayah, from every reciter published by [everyayah.com](https://everyayah.com/), mirrored byte for byte, checked against upstream checksums, hashed, and republished where any application or automated agent can fetch a single ayah by URL.

مَقْرَأ, a maqra, is the hall where the Qur'an is recited and heard. That is the whole idea: one place, every reciter, every ayah.

## What is here

| Layer | Where | What |
|---|---|---|
| Registry | `manifests/reciters.json` | 80 recitation sets: slug, reciter, style, riwayah, bitrate, language, upstream folder, status, notes |
| Surahs | `manifests/surahs.json` | 114 surahs with ayah counts (sum 6236), cross-checked against everyayah.com's own table |
| Per-file manifests | `manifests/audio/<slug>.json` | name, exact bytes, MD5, SHA-256, and MD5 state (matched upstream, mismatched, or no upstream list) for every ayah file of every set |
| Timings | `timings/<set>.json` | everyayah.com's split points, one JSON per timing set, milliseconds |
| Tooling | `maqra/` | the mirror, verify, package, and publish commands (Python 3.10+, no dependencies for the mirror itself) |
| Survey | `docs/everyayah-survey.md` | what everyayah.com contains, folder by folder, and what was left out and why |
| Audio | Hugging Face and GitHub Releases | one dataset and one release per set; see `docs/hosting.md` |

The audio is not in this repository. Git and GitHub are the wrong place for 500,000 MP3 files; the manifests here are what let you verify a copy fetched from anywhere.

## Fetch an ayah

File names are `SSSAAA.mp3`: surah as three digits, ayah as three digits. `001001.mp3` is Al-Fatihah 1, `002286.mp3` is Al-Baqarah 286. `SSS000.mp3`, where a set has it, is the basmala or isti'adhah intro before the surah.

Hugging Face, one file:

```
https://huggingface.co/datasets/maqra-project/mishari-alafasy-64kbps/resolve/main/001001.mp3
```

GitHub Releases, one surah as a zip:

```
https://github.com/Abdalla-Eldoumani/maqra/releases/download/mishari-alafasy-64kbps/001.zip
```

Every set's release also carries `manifest.json` (all hashes), `checksums.sha256` (for the zips), `extras.zip` (the reciter's standalone basmala and isti'adhah files and everyayah.com's own notes), and `NOTICE.txt`.

Pick a set from the table in `docs/reciters.md` or from `manifests/reciters.json`. The slug is the same on Hugging Face, in the release tag, and in the manifest file name.

## Verify a copy

```
python -m maqra verify --only mishari-alafasy-64kbps --root /path/to/data
```

`verify` re-hashes every local file and compares it with the committed manifest. A copy that passes is byte-identical to what everyayah.com served when the manifest was written.

## Run the mirror yourself

```
git clone https://github.com/Abdalla-Eldoumani/maqra
cd maqra
python -m maqra list                      # the 80 sets and their local status
python -m maqra mirror --only alafasy     # both Alafasy sets, about 2.4 GB
python -m maqra mirror                    # everything, about 102 GB
python -m maqra extras                    # timings, ayah images, site files, tools
python -m maqra verify
```

The mirror downloads each set's `000_versebyverse.zip` once, extracts it, then fetches loose files for anything the zip lacked or that differs from the live listing, hashes everything, and compares with the upstream MD5 list. It resumes where it stopped. `docs/running-the-mirror.md` covers disk, time, Windows, and publishing.

## Layout

```
maqra/                    the package (listing, http, checksums, mirror, extras, package, publish_*)
manifests/
  reciters.json           the registry
  surahs.json             surah table
  upstream-folders.psv    the raw 2026-08-25 survey the registry was built from
  audio/<slug>.json       per-file manifests, written by `maqra mirror`
timings/<set>.json        converted timing files, written by `maqra extras --timings`
docs/                     survey, data layout, hosting, running guide, decision records
tests/                    offline tests against a fake upstream that speaks the CDN's listing format
tools/build_registry.py   regenerates the registry from the survey
data/                     local mirror root, ignored by git (override with --root or MAQRA_ROOT)
```

## What was deliberately left out

- The XML text set on everyayah.com. Its own `00_warning.txt` says the files carry many mistakes and points to the Tanzil project. Take Qur'an text from Tanzil or the Quran.com API, never from here.
- Page-by-page MP3s, per-surah zips, and the `merged/`, `mistakes/`, `replaced/`, `old/`, `notclear/` folders upstream. The per-ayah files are the curated result; those folders are the workshop floor.
- Four exact duplicate folders and one empty one. `manifests/reciters.json` lists them under `excluded_upstream_folders` with the reason for each.
- The unsigned `mp3splt` executable in `tools/`. The source zips are mirrored; the binary is available from the mp3splt project.

## Rights

The recordings belong to the reciters and their publishers; everyayah.com collected and split them; Maqra mirrors and verifies them. everyayah.com publishes no license. Credit the reciter and everyayah.com, link back, keep it non-commercial, do not alter the recordings. `RIGHTS.md` has the full notice and the takedown route. The code, registry, manifests, and documentation are MIT.

## Contributing

Corrections to reciter names, transliterations, and Arabic names are the most useful contributions; see `CONTRIBUTING.md`. Every claim about a recording should be traceable to an upstream file or a named source.
