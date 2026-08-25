# Rights and attribution

Maqra is a mirror. It adds verification, manifests, packaging, and documentation around recordings it did not make.

## Who made what

The recitations are the work of the reciters named in `manifests/reciters.json` and of the publishers and institutions who first recorded and distributed them. Several sets carry their own credit notes upstream (Zekr, QuranExplorer.com, KetabAllah.net, Dar Al Kuran Mostar, and individual contributors); those notes are mirrored verbatim under each set's `_upstream/` folder.

everyayah.com (formerly versebyversequran.com) collected the recordings, split them into one file per ayah, produced the timing files and the MD5 lists, and has served them freely for many years. Its contact form is hosted by the Quran Foundation help centre.

Maqra copies the ayah files byte for byte, checks every file against everyayah.com's own MD5 lists where they exist and against exact byte counts everywhere, records SHA-256 for every file, and republishes the result on Hugging Face and GitHub Releases so that applications and automated agents can fetch any ayah from any reciter by URL without a browser.

## What everyayah.com says

everyayah.com publishes no site-wide license. The only explicit terms found on the site (surveyed 2026-08-25) are in `timings_files/000_disclaimer.txt`:

> (C) VerseByVerseQuran.com. You must link back to our site from your product and web-site to use these timings.

The license URL that disclaimer points to no longer resolves. One set's upstream `info.txt` (Maher Al-Muaiqly, prepared by the Zekr project in 2010) states "Recitation license: UNKNOWN". Treat that as the honest status of the whole collection: freely served, widely mirrored (the Internet Archive has hosted a 98 GB copy since 2021 and Tarteel AI republished it on Hugging Face in 2022), never formally licensed.

## What Maqra asks

Maqra grants no rights in the recordings, because it holds none. It asks the following of anyone who uses the audio from here:

1. Credit the reciter and everyayah.com, and link back to https://everyayah.com/ from any product or site that uses the audio or the timings.
2. Use the recordings for non-commercial purposes: teaching, memorisation, apps and tools offered without charge, research.
3. Do not alter the recordings. Cut, concatenate, and stream them as needed, but do not remix them, change their pitch or speed for publication, or present an edited recording as the reciter's own.
4. Keep the attribution when you redistribute: ship this notice or a link to it with any copy.

## Takedown

If you hold rights in any recording here and want it removed or its terms changed, open an issue on the Maqra repository or write to the maintainer. Removal is not contested; it is done, and the manifests are updated to record it.

## The code and the metadata

Everything Maqra itself wrote is MIT licensed (see `LICENSE`): the mirror and verification tooling, the reciter registry, the manifests with their hashes, the converted timing files, and the documentation. Use them freely, with or without the audio.
