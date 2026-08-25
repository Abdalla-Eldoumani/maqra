"""Render docs/reciters.md from manifests/reciters.json. Run after editing the registry."""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REG = ROOT / "manifests" / "reciters.json"
OUT = ROOT / "docs" / "reciters.md"


def main() -> None:
    doc = json.loads(REG.read_text(encoding="utf-8"))
    rows = doc["reciters"]
    lines = [
        "# Reciter sets",
        "",
        f"{len(rows)} sets, generated from `manifests/reciters.json`. The slug is the folder name in the data root, the Hugging Face dataset name under `maqra-project/`, the GitHub release tag, and the manifest file name under `manifests/audio/`.",
        "",
        "| Slug | Reciter and set | Style | Riwayah | Lang | kbps | Files (survey) | Status | Upstream folder |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r["survey_2026_08_25"]
        lines.append(
            f"| `{r['slug']}` | {r['name']} | {r['style']} | {r['riwayah']} | {r['language']} | {r['bitrate_kbps'] or ''} | "
            f"{s['ayah_files_seen']} | {r['status']} | [{r['source_folder']}]({r['source_url']}) |"
        )
    lines += ["", "## Notes recorded during the survey", ""]
    for r in rows:
        if r["notes"]:
            lines.append(f"- `{r['slug']}`: {r['notes']}")
    lines += ["", "## Upstream folders not mirrored as sets", ""]
    for e in doc["excluded_upstream_folders"]:
        lines.append(f"- `{e['source_folder']}`: {e['reason']}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
