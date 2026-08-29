# Running the mirror

## Requirements

- Python 3.10 or newer. The mirror, verify, package, and extras commands use the standard library only.
- About 110 GB free for the full archive: 102 GB of ayah files plus one bulk zip in flight at a time (up to 4 GB). Building every set's release zips up front would take another 102 GB; `publish-github --build --cleanup` avoids that by building and deleting one set at a time.
- A network connection that can reach `everyayah.com` directly. Corporate and sandbox proxies that block it will fail the first listing request with a clear error.
- For publishing: `huggingface_hub` (`pip install huggingface_hub`) and a Hugging Face token in the `HF_TOKEN` environment variable or from `hf auth login`; the GitHub CLI `gh`, logged in with `gh auth login`. No token is ever written to a file in this project.

## Commands

```
python -m maqra list                          # sets and status
python -m maqra mirror                        # everything
python -m maqra mirror --only alafasy husary  # by reciter key or slug
python -m maqra mirror --skip al-husary       # exclude by reciter key or slug
python -m maqra mirror --workers 12           # more parallel loose downloads (default 8)
python -m maqra mirror --no-zip               # loose files only, no bulk zip
python -m maqra mirror --force --only ...     # redo a set already marked done
python -m maqra verify                        # re-hash local files against manifests
python -m maqra extras                        # timings + images + site files + tools
python -m maqra extras --timings              # just the timing zips, converted to timings/*.json
python -m maqra package                       # data/releases/<slug>/001.zip ...
python -m maqra publish-hf --only alafasy     # upload sets to Hugging Face
python -m maqra publish-hf --index --images   # the registry dataset and the images dataset
python -m maqra publish-github --only alafasy # create releases and upload assets
python -m maqra publish-github --build --cleanup # build, upload, and delete each set's zips in turn
python -m maqra status
```

`--root` (or `MAQRA_ROOT`) moves the data root. `--dry-run` on the publish commands prints what would happen.

On Windows, `scripts\windows\mirror.cmd`, `verify.cmd`, `extras.cmd`, `status.cmd`, `commit-manifests.cmd`, `publish-github.cmd`, `publish-hf.cmd`, and `publish-hf-index.cmd` run the same commands from a double-click and keep the window open at the end. They pick `py -3` when the Python launcher is installed and `python` otherwise.

## What a set run does

1. Reads the folder listing from everyayah.com: exact byte sizes for every file.
2. Fetches the small metadata files (checksum lists, readmes) into `_upstream/` and the standalone intro files into `_extra/`.
3. If more than 100 ayah files are missing locally and the folder has a `000_versebyverse.zip`, downloads that once (resumable), extracts every entry whose size matches the live listing, and deletes the zip.
4. Downloads loose files for anything still missing or wrong-sized, eight at a time, each resumable and retried with backoff on 5xx and timeouts.
5. Hashes every file (MD5 and SHA-256 in one pass) and compares with the upstream MD5 list. A file that disagrees is deleted and fetched once more; if it still disagrees, the live copy is kept and the file is marked `upstream-mismatch` in the manifest.
6. Writes `manifests/audio/<slug>.json` and records the set in `data/state/mirror.json`.

Interrupt with Ctrl+C at any point; re-run the same command and it resumes. Partial files are written as `.part` and never counted.

## Expected time

The bulk zips total about 86 GB and the loose fetches that follow are usually a few hundred files per set. On a 100 Mbit/s line the whole archive takes roughly three to four hours of transfer plus about an hour of hashing on a laptop SSD. Run it overnight; `data/state/logs/` keeps the log.

## Windows notes

- Use a path without spaces for the data root if you can; everything works with spaces, but paths stay shorter in logs and shells.
- Long paths are not an issue: the deepest path is `data/audio/<slug>/_upstream/stray/<name>`.
- The console prints ASCII only. Arabic never appears in file names or logs.
- Python from python.org or the Microsoft Store both work. Run from a terminal, not by double-clicking.
- Keep the machine awake for an overnight run: `powercfg /change standby-timeout-ac 0` before, and set it back after.

## Publishing order

1. `mirror` everything, then `verify`.
2. Commit the 80 manifests and any timing files, one file per commit: `python tools/commit_manifests.py` (or `scripts\windows\commit-manifests.cmd`), then push.
3. `publish-github --build --cleanup` (about 102 GB of uploads with under 5 GB of scratch at any moment; `gh` resumes per asset, so re-run after any interruption). Use `package` first and drop `--build` only when you want to keep the zips.
4. `publish-hf` (another 102 GB; `upload_large_folder` resumes per file and commits in batches).
5. `publish-hf --index --images`.
6. Update `docs/reciters.md` if the registry changed: `python tools/build_reciters_doc.py`.

## Creating the Hugging Face namespace

`maqra-project` is an organization. Create it once at https://huggingface.co/organizations/new, add yourself, and generate a write token for your account. To publish under a personal account instead, pass `--namespace <user>` to `publish-hf` and change `huggingface_repo` in the registry before committing manifests, so the documented URLs stay true.
