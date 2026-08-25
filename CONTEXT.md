# Glossary

Terms as used in this repository. Avoid the alternatives listed so that code, manifests, and docs say one thing one way.

**Ayah file.** One MP3 carrying one ayah of one set, named `SSSAAA.mp3`. Avoid: verse file, clip, segment.

**Intro file.** The `SSS000.mp3` file some sets carry before a surah, holding the basmala or the isti'adhah. It is not an ayah and is not counted as one. Avoid: verse 0, bismillah file (that name is reserved for the standalone `_extra/bismillah.mp3`).

**Set.** One upstream folder mirrored as one unit: one reciter, one style, one riwayah, one bitrate. A reciter can have several sets. Identified by its slug. Avoid: reciter (when a specific bitrate or style is meant), edition, track.

**Slug.** The canonical identifier of a set: lowercase, hyphenated, ending in the bitrate where upstream states one (`mishari-alafasy-64kbps`). Used as the folder name, the Hugging Face dataset name, the GitHub release tag, and the manifest file name. Avoid: id, key, folder name (that is the upstream folder).

**Upstream folder.** The set's original folder on everyayah.com, kept verbatim in `source_folder`. Avoid: source slug.

**Reciter key.** The short identifier shared by all sets of one reciter (`alafasy`, `al-husary`). Used for selection (`--only alafasy`). Avoid: reciter id.

**Style.** How the recitation is delivered: murattal (measured), mujawwad (melodic, slow), muallim (teaching, with pauses for repetition), or unknown where upstream does not say. Avoid: mode, type.

**Riwayah.** The transmission of the reading: hafs (from Asim) for almost every set, warsh (from Nafi) for three. Avoid: qira'ah as a synonym, narration.

**Manifest.** The per-set JSON under `manifests/audio/` listing every mirrored file with its exact size, MD5, SHA-256, and MD5 state. Avoid: index, checksum file (that is the upstream `000_checksum.md5`).

**MD5 state.** Per file, one of `upstream-match` (our MD5 equals the upstream list), `upstream-mismatch` (the live file differs from the list; the live file is kept and the disagreement recorded), `no-upstream-md5` (the set has no list or the file is not in it). Avoid: verified flag.

**Timing set.** One of everyayah.com's timing zips converted to JSON: per surah, the millisecond offsets at which ayahs end in the full-surah recording. Avoid: alignment (word-level alignment is a different thing, see cpfair/quran-align).

**Data root.** The local folder that holds the mirror (`data/` by default). Never committed. Avoid: cache, store.
