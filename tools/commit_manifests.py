"""Commit new or changed per-set manifests and timing files, one file per commit.

Run after `maqra mirror` and `maqra extras`. Every file gets its own commit so the
history stays readable when 80 manifests land at once. Nothing is pushed.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main() -> int:
    status = git("status", "--porcelain", "--untracked-files=all", "--", "manifests/audio", "timings", "docs/reciters.md")
    files = []
    for line in status.splitlines():
        code, path = line[:2], line[3:].strip().strip('"')
        if code.strip() in ("??", "M", "A", "AM", "MM"):
            files.append((code.strip(), path))
    if not files:
        print("nothing to commit under manifests/audio, timings, or docs/reciters.md")
        return 0
    for code, path in sorted(files, key=lambda x: x[1]):
        p = pathlib.Path(path)
        if p.parts[0] == "manifests" and p.suffix == ".json":
            msg = f"{'add' if code == '??' else 'update'} manifest for {p.stem}"
        elif p.parts[0] == "timings":
            msg = f"{'add' if code == '??' else 'update'} timing set {p.stem}"
        else:
            msg = f"{'add' if code == '??' else 'update'} {path}"
        git("add", "--", path)
        git("commit", "-q", "-m", msg, "--", path)
        print(f"committed: {msg}")
    print(f"{len(files)} commits made; review with `git log --oneline -{len(files)}` and push when ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
