# Where the audio lives and how to fetch it

Two public homes, kept in sync from the same local mirror. Both are addressed by the set's slug.

## Hugging Face: one dataset per set

Namespace `maqra-project`. Each set is its own dataset repository because the Hub allows at most 10,000 entries per folder and recommends fewer than 100,000 files per repository; one set is about 6,350 files, the whole archive about 500,000.

```
https://huggingface.co/datasets/maqra-project/<slug>
https://huggingface.co/datasets/maqra-project/<slug>/resolve/main/<SSSAAA>.mp3
https://huggingface.co/datasets/maqra-project/<slug>/resolve/main/manifest.json
```

Two more datasets: `maqra-project/maqra` (the registry, all manifests, all timing files) and `maqra-project/ayah-images` (the four image sets).

From Python:

```python
from huggingface_hub import hf_hub_download
path = hf_hub_download("maqra-project/mishari-alafasy-64kbps", "001001.mp3", repo_type="dataset")
```

With the `datasets` library, `load_dataset("audiofolder", data_dir=...)` after `snapshot_download`, or stream individual files by URL.

## GitHub Releases: one release per set

Repository `Abdalla-Eldoumani/maqra`, tag = slug. Assets per release: `001.zip` to `114.zip` (one zip per surah, stored uncompressed so any tool can stream inside it), `extras.zip`, `manifest.json`, `checksums.sha256`, `NOTICE.txt`. Every asset is far below GitHub's 2 GiB limit; a release holds at most 118 assets against the 1,000 allowed.

```
https://github.com/Abdalla-Eldoumani/maqra/releases/download/<slug>/<SSS>.zip
https://github.com/Abdalla-Eldoumani/maqra/releases/download/<slug>/manifest.json
```

Whole set with the GitHub CLI:

```
gh release download mishari-alafasy-64kbps -R Abdalla-Eldoumani/maqra -D alafasy-64
sha256sum -c alafasy-64/checksums.sha256
```

If a set is ever re-mirrored with changed upstream files, the new release is tagged `<slug>-r2` and the registry's `github_release_tag` moves; older tags stay.

## For automated agents

An agent that needs "Al-Fatihah ayah 1 by Alafasy" does three things: read `manifests/reciters.json` (or `docs/reciters.md`) to pick a slug, format the file name as `SSSAAA.mp3`, and fetch the Hugging Face URL above. No API key, no session, no HTML. To confirm the bytes, compare the SHA-256 with the row in `manifests/audio/<slug>.json`.

Surah and ayah bounds are in `manifests/surahs.json` (114 entries, 6236 ayahs). The intro file `SSS000.mp3` exists only in sets whose manifest lists it; check before requesting it.

## everyayah.com itself

The original stays where it is. Maqra changes nothing upstream and links back to it everywhere. Clients that already use everyayah.com URLs can keep doing so; the Hugging Face URL for the same file is the everyayah path with the base swapped and the folder renamed to the slug.

## Bandwidth and courtesy

Hugging Face and GitHub serve these at no cost to the project. Fetch what you need, cache what you fetch, and prefer the per-surah zips over 6,000 single-file requests when you need a whole set.
