# everyayah.com, surveyed

Read on 2026-08-25 through the site's own pages and directory listings. Sizes are the CDN's exact byte counts where the tool reads them and rounded listing values (MiB) in the summary tables below, which were taken from the listing pages by hand. Re-run `python -m maqra survey` for a fresh, exact reading.

## What the site is

A static file tree under `https://everyayah.com/data/`, served by BunnyCDN with byte-range support. The front page (`index.html`, formerly `versebyversequran.com`, which now redirects here) is a small Bootstrap app that builds a download URL from a reciter, a chapter, and an ayah number. Its sidebar links to the sections below. "Contact Us" goes to the Quran Foundation help centre on Zendesk. There is no robots.txt, no terms page, no license file.

| Section | Path | Content |
|---|---|---|
| Home | `/index.html` | reciter and ayah picker, preview player, download links |
| Quran Text | `/data/QuranText/` | 6236 GIF images of ayahs, `S_A.gif`, 5 MiB |
| Quran Text images (JPG) | `/data/QuranText_jpg/` | 6237 JPGs plus a few a/b variants, 53 MiB |
| Quran Text HI Res (PNG) | `/data/quranpngs/` | 6236 high-resolution PNGs plus `000_images.zip` (77 MiB), 151 MiB |
| (unlisted) | `/data/images_png/` | 6236 small PNGs, 41 MiB; the home page's preview images |
| Quran Timings Files | `/data/timings_files/` | 30 zips, 17 MiB, one text file per surah, one millisecond offset per line |
| Tools | `/data/tools/` | 10 files, 2.8 MiB: .NET splitting tools as source zips, mp3splt binaries |
| XML | `/data/XML/` | Arabic text and four translations as per-surah XML, plus `Config.xml` for a QuranReader app |
| Recitations: Ayat MP3 | `/recitations_ayat.html` | 79 sets with GO, ZIP, MD5, and More Zips links, plus "files missing" counts |
| Recitations: Page MP3 | `/recitations_pages.html` | 67 sets with page-by-page MP3s |
| Recitations JS | `/data/recitations.js` | JSON: `ayahCount[114]` and 79 numbered entries `{subfolder, name, bitrate}` |
| Old website | `/old_index.html` | the previous front page, same links |

Everything the site offers is reachable by URL without a session, so a mirror needs no login and no scraping beyond reading the listings.

## The recitation folders

86 folders under `/data/` hold per-ayah audio (79 are listed in `recitations.js`; the rest are on the server but unlisted or duplicated). Inside each:

| Item | Meaning |
|---|---|
| `SSSAAA.mp3` | one file per ayah; `001001.mp3` is Al-Fatihah 1 |
| `SSS000.mp3` | intro (basmala or isti'adhah) before each surah, in the sets that have it; 6349 or 6350 files instead of 6236 |
| `000_checksum.md5` | MD5 for every file, `digest *Folder/name` per line; present in 73 of 86 folders (a few have only `000_unverified_checksum.md5`, `md5.sum`, or a differently named list) |
| `000_versebyverse.zip` | all ayah files in one archive, 0.2 to 4 GiB; present in 83 folders |
| `audhubillah.mp3`, `bismillah.mp3` | standalone isti'adhah and basmala |
| `PageMp3s/` | `Page001.mp3` to `Page604.mp3`, the Madinah mushaf page by page, plus `000_allfiles.zip` |
| `zips/` | `001.zip` to `114.zip`, one per surah |
| `merged/`, `mistakes/`, `replaced/`, `old/`, `new/`, `notclear/`, `glitches/`, `original/` | the workshop: superseded or questionable files kept beside the curated set |
| `000_readme.txt`, `000_details.txt`, `info.txt`, `_notes.txt`, `000_disclaimer.txt` | credits and caveats, mirrored verbatim under `_upstream/` |

Totals across the 86 folders: 524,923 ayah files, about 107 GiB of per-ayah MP3, about 86 GiB of bulk zips beside them. After removing the four duplicate folders, the empty one, and the one that only ships an offline zip, the mirrored collection is 80 sets, 499,631 ayah files, about 102 GiB.

Sets by file count: 23 folders carry exactly 6236 files (no intros), 38 carry 6349 or 6350 (an intro for every surah, with or without one for At-Tawbah), 19 carry a handful more or fewer than a clean count (intros for some surahs only, or a stray extra), and five are short:

| Folder | Files | Missing | Site's own note |
|---|---|---|---|
| `Mustafa_Ismail_48kbps` | 2017 | 4219 | "4220 files missing" |
| `Menshawi_32kbps` | 5933 | 303 | "303 files missing" |
| `warsh/warsh_Abdul_Basit_128kbps` | 6214 | 22 | "47 files missing" |
| `Ibrahim_Akhdar_64kbps` | 0 | 6236 | "6236 files missing"; the zip is 527 bytes |
| `MultiLanguage/Shaatree_Walk_64kbps` | 0 | all | only `shatriwalk-64kbps-offline.recit.zip`, 1 GiB |

The full folder-by-folder table with subfolders and side files is `manifests/upstream-folders.psv`.

### Duplicates and oddities

- `Abu Bakr Ash-Shaatree_128kbps` (with spaces) and `Abu_Bakr_Ash-Shaatree_128kbps` are identical in count and size; the site links the underscore one.
- `Saood bin Ibraaheem Ash-Shuraym_128kbps` and `Saood_ash-Shuraym_128kbps` differ by one stray file; the site links the underscore one.
- `English/Ibrahim_Walk_192kbps_TEST` is a copy of `English/Sahih_Intnl_Ibrahim_Walk_192kbps`.
- `translations/bosnian/besim_korkut_ajet_po_ajet_audio` is a copy of `translations/besim_korkut_ajet_po_ajet` without checksum or zip.
- `Minshawy_Teacher_128kbps` and `Nabil_Rifa3i_48kbps` exist on the server; the first is listed nowhere, the second appears in the picker but not in `recitations.js`.
- `recitations.js` labels Parhizgar as `Parhizgar_64Kbps`; the folder is `Parhizgar_48kbps`.
- `AbdulSamad_64kbps_QuranExplorer.Com/000_readme.txt`: "There are errors reported in this recitation. From Surah Baqara verse 22 its incorrect."
- `MaherAlMuaiqly128kbps/info.txt` (Zekr project, 2010): "Recitation license: UNKNOWN".
- `Karim_Mansoori_40kbps/000_details.txt`: pre-split files downloaded from islam4u.com.
- `Nabil_Rifa3i_48kbps/000 details.txt`: provided by Ebrahim Badiee, Shiraz, August 2019 to June 2020.
- The listing "Modified" dates are all January 2023 (the move to the current CDN); HTTP `Last-Modified` on individual files can be later (a sampled ayah file said January 2025), so the loose files, not the zips, are the source of truth, and the mirror treats them that way.

## Timings

Each zip in `timings_files/` unpacks to `001.txt` to `114.txt`. Each line is an integer: the millisecond offset in the full-surah recording at which an ayah ends. The disclaimer file states the terms (link back to everyayah.com) and warns that "many of our mp3s have been fixed manually after splitting these files, so this will not provide 100% accurate results." 30 timing sets exist, covering roughly a third of the reciters. Maqra converts each zip to one JSON file under `timings/`. Word-level timestamps for several everyayah sets exist separately in the MIT-licensed [cpfair/quran-align](https://github.com/cpfair/quran-align) project (data CC BY 4.0).

## Images

Four renderings of every ayah, named `S_A.ext` without zero padding (`1_1.png`, `2_286.png`): GIF (small, the oldest set, with a few stray `-7_*.gif` files and old site graphics), JPG, PNG, and high-resolution PNG. `quranpngs/000_images.zip` bundles the high-resolution set. Maqra mirrors all four into `images/` and publishes them as one Hugging Face dataset; they are not committed to git.

## XML text: not mirrored

`XML/Arabic/00_warning.txt` reads, in full: "There are tons of mistakes in this XML files. Please see Tanzil Project for more details." Two translation files are 0 bytes (`alhilali_english_114.xml`, `transliteration_english_114.xml`). The Arabic is in a plain, non-Uthmani orthography. None of this is a source anyone should ship Qur'an text from, so Maqra records that it exists and stops there. Use Tanzil or the Quran.com API for text.

## Tools: partially mirrored

`ASPNet_Quran_Library.zip`, `QuranSplitter.zip`, the two `CustomVerseByVerseQuranSplitTool` zips, `Quran XML Converter (.NET).zip`, `mp3SplitHelper_src.zip`, `mp3splthelper.zip`, `split.zip`: mirrored verbatim as historical source. `mp3splt-2.1-win32.zip` and `mp3splt_2.2.2_beta_i386.exe`: the binary is skipped by default (`--include-exe` fetches it); mp3splt is GPL software available from its own project.

## Licensing, as found

No license statement exists on the site. The timings disclaimer asks for a link back. One set's info file says the recitation license is unknown. The site's contact form is the Quran Foundation's help centre, whose own terms for Quran.com restrict scraping and redistribution of Quran.com content, but do not mention everyayah.com. Public precedent for mirroring: the Internet Archive item `quran-every-ayah` (98 GB, added 2021), the Hugging Face dataset `tarteel-ai/everyayah` (2022, 311 GB, declared CC BY 4.0 by Tarteel), a dozen derived Hugging Face datasets, and the Quran Android app, which fetches from everyayah.com at runtime. Maqra's position is in `RIGHTS.md`.

## Sources read

- https://everyayah.com/ and `/index.html`, `/old_index.html`, `/recitations_ayat.html`, `/recitations_pages.html`, `/src/getfile.html`
- https://everyayah.com/data/ and every recitation folder listing, plus `XML/`, `tools/`, `timings_files/`, the four image folders, and samples of `PageMp3s/`, `zips/`, `merged/`, `mistakes/`, `replaced/`, `old/`, `new/`, `glitches/`, `notclear/`
- https://everyayah.com/data/recitations.js
- https://everyayah.com/data/timings_files/000_disclaimer.txt and `Husary_Timings.zip`
- https://everyayah.com/data/XML/Arabic/00_warning.txt, `Config.xml`, `Quran_Arabic_001.xml`
- The `000_readme.txt`, `000_details.txt`, `info.txt` files named above
- https://github.com/quran/quran_android/issues/434
- https://archive.org/details/quran-every-ayah
- https://huggingface.co/datasets/tarteel-ai/everyayah
- https://github.com/cpfair/quran-align
- https://quran.com/en/terms-and-conditions
- https://quran.zendesk.com/hc/en-us/community/posts/360061542052
