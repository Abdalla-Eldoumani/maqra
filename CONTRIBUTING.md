# Contributing

## What helps most

1. **Reciter metadata.** `manifests/reciters.json` carries Latin transliterations chosen for consistency, not authority. Corrections to a reciter's name, a verified Arabic name (`name_ar` is deliberately absent until each one is verified against a reliable source), the style of a set (murattal, mujawwad, muallim), or its riwayah are welcome. Cite where the correction comes from.
2. **Audio problems.** If an ayah file is cut wrong, mislabelled, or belongs to a different surah, open an issue with the slug, the file name, and what you heard. everyayah.com's own `mistakes/` and `replaced/` folders show that such reports have been acted on before; Maqra records them in the set's manifest notes and forwards them upstream.
3. **Tooling.** Bug fixes and portability fixes to `maqra/`. The mirror must keep running on a bare Python 3.10 install with no dependencies; keep new dependencies behind optional extras.

## Ground rules

- Never commit audio or images. The data root is ignored by git for a reason.
- Never edit a per-file manifest by hand. Manifests are written by `maqra mirror`; if a file changed upstream, re-run the mirror for that set and commit the regenerated manifest.
- Qur'an text does not live in this repository. Do not add it.
- One file per commit, with a message that says what changed in the file. This keeps the history readable when 80 manifests move at once.
- Run `python -m pytest` before opening a pull request. The tests run offline against a fake upstream.

## Adding a set

When everyayah.com adds a folder:

1. Add a row to `manifests/upstream-folders.psv` from the folder's listing.
2. Add the folder to the slug table in `tools/build_registry.py` and run it.
3. Run `python -m maqra mirror --only <new-slug>`, then `package`, then the two publish commands.
4. Commit the registry, the survey row, and the new manifest as separate commits.
