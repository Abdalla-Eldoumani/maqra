"""Command line entry point: python -m maqra <command> [options]."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import List

from . import __version__
from .registry import MANIFESTS, REPO_ROOT, load_reciters, select

DEFAULT_ROOT = Path(os.environ.get("MAQRA_ROOT", REPO_ROOT / "data"))
DEFAULT_RELEASES = Path(os.environ.get("MAQRA_RELEASES", REPO_ROOT / "data" / "releases"))


def _log_factory(root: Path):
    logs = root / "state" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    fh = open(logs / f"maqra-{stamp}.log", "a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"{dt.datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()

    return log


def _add_selection(p: argparse.ArgumentParser) -> None:
    p.add_argument("--only", nargs="*", help="slugs or reciter keys to include")
    p.add_argument("--skip", nargs="*", help="slugs or reciter keys to exclude")
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="data root (default: ./data or $MAQRA_ROOT)")


def cmd_list(args: argparse.Namespace) -> int:
    reciters = select(load_reciters(), args.only, args.skip)
    from .mirror import read_state
    state = read_state(args.root)
    print(f"{'slug':50} {'kbps':>4} {'status':10} {'files':>6}  name")
    for r in reciters:
        st = state.get(r.slug, {})
        print(f"{r.slug:50} {str(r.bitrate_kbps or '-'):>4} {st.get('status', 'pending'):10} {str(st.get('ayah_files', '')):>6}  {r.name}")
    print(f"{len(reciters)} sets")
    return 0


def cmd_survey(args: argparse.Namespace) -> int:
    """Re-read every upstream folder listing and write a fresh survey JSON."""
    from .listing import dirs_only, files_only, list_folder
    from .registry import AYAH_FILE
    log = _log_factory(args.root)
    reciters = select(load_reciters(), args.only, args.skip)
    out = {"surveyed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "folders": {}}
    for r in reciters:
        entries = list_folder(r.source_folder)
        files = files_only(entries)
        ayah = [e for e in files if AYAH_FILE.match(e.name)]
        out["folders"][r.source_folder] = {
            "slug": r.slug,
            "ayah_files": len(ayah),
            "ayah_bytes": sum(e.size or 0 for e in ayah),
            "subfolders": [d.name for d in dirs_only(entries)],
            "other_files": [{"name": e.name, "bytes": e.size, "modified": e.modified} for e in files if not AYAH_FILE.match(e.name)],
        }
        log(f"[{r.slug}] {len(ayah)} ayah files, {sum(e.size or 0 for e in ayah) / 1024 ** 2:.0f} MiB")
    target = args.root / "state" / "survey.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"survey written to {target}")
    return 0


def cmd_mirror(args: argparse.Namespace) -> int:
    from .mirror import mirror_reciter, read_state
    log = _log_factory(args.root)
    reciters = select(load_reciters(), args.only, args.skip)
    state = read_state(args.root)
    failed: List[str] = []
    for i, r in enumerate(reciters, 1):
        if not args.force and state.get(r.slug, {}).get("status") in ("done", "done-with-gaps"):
            log(f"[{r.slug}] already {state[r.slug]['status']}; use --force to redo")
            continue
        log(f"=== {i}/{len(reciters)} {r.slug} ===")
        try:
            mirror_reciter(r, args.root, workers=args.workers, use_zip=not args.no_zip, keep_zip=args.keep_zip, log=log)
        except KeyboardInterrupt:
            log("interrupted; re-run to resume")
            return 130
        except Exception as exc:  # noqa: BLE001 - keep the batch going, report at the end
            log(f"[{r.slug}] ERROR {exc!r}")
            failed.append(r.slug)
    if failed:
        log(f"failed sets: {failed}")
        return 1
    log("mirror pass complete")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from .mirror import verify_reciter
    log = _log_factory(args.root)
    reciters = select(load_reciters(), args.only, args.skip)
    total_problems = 0
    for r in reciters:
        _checked, problems = verify_reciter(r, args.root, log=log)
        for p in problems[:20]:
            log(f"  {p}")
        total_problems += len(problems)
    log(f"verify complete: {total_problems} problems")
    return 1 if total_problems else 0


def cmd_extras(args: argparse.Namespace) -> int:
    from .extras import mirror_images, mirror_offline_zip, mirror_site_files, mirror_timings, mirror_tools
    log = _log_factory(args.root)
    nothing_chosen = not (args.timings or args.images or args.tools or args.site or args.offline_zip)
    report = {}
    if args.site or nothing_chosen:
        report["site"] = mirror_site_files(args.root, log)
    if args.timings or nothing_chosen:
        report["timings"] = mirror_timings(args.root, args.workers, log, REPO_ROOT / "timings")
    if args.images or nothing_chosen:
        report["images"] = mirror_images(args.root, args.workers, log)
    if args.tools or nothing_chosen:
        report["tools"] = mirror_tools(args.root, args.workers, log, include_exe=args.include_exe)
    if args.offline_zip:
        report["offline_zip"] = mirror_offline_zip(args.root, log)
    target = args.root / "state" / "extras.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"extras report written to {target}")
    return 0


def cmd_package(args: argparse.Namespace) -> int:
    from .package import build_surah_zips
    log = _log_factory(args.root)
    reciters = select(load_reciters(), args.only, args.skip)
    for r in reciters:
        if not (args.root / "audio" / r.slug).is_dir():
            log(f"[{r.slug}] not mirrored yet; skipping")
            continue
        build_surah_zips(r, args.root, args.releases, log)
    return 0


def cmd_publish_github(args: argparse.Namespace) -> int:
    from .publish_github import check_auth, publish_reciter
    log = _log_factory(args.root)
    if not args.dry_run:
        check_auth()
    reciters = select(load_reciters(), args.only, args.skip)
    for r in reciters:
        if not (args.releases / r.slug).is_dir():
            log(f"[{r.slug}] not packaged yet; skipping")
            continue
        publish_reciter(r, args.releases, log, repo=args.repo, dry_run=args.dry_run)
    return 0


def cmd_publish_hf(args: argparse.Namespace) -> int:
    from .publish_hf import publish_images, publish_index, publish_reciter
    log = _log_factory(args.root)
    if args.index:
        publish_index(args.root, log, namespace=args.namespace, dry_run=args.dry_run)
    if args.images:
        publish_images(args.root, log, namespace=args.namespace, dry_run=args.dry_run)
    if args.index or args.images:
        if not args.only:
            return 0
    reciters = select(load_reciters(), args.only, args.skip)
    for r in reciters:
        if not (args.root / "audio" / r.slug).is_dir():
            log(f"[{r.slug}] not mirrored yet; skipping")
            continue
        publish_reciter(r, args.root, log, namespace=args.namespace, dry_run=args.dry_run, workers=args.workers)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from .mirror import read_state
    state = read_state(args.root)
    reciters = load_reciters()
    done = [r for r in reciters if state.get(r.slug, {}).get("status") in ("done", "done-with-gaps")]
    partial = [r for r in reciters if state.get(r.slug, {}).get("status") == "partial"]
    pending = [r for r in reciters if r.slug not in state]
    total_bytes = sum(state.get(r.slug, {}).get("ayah_bytes", 0) for r in reciters)
    print(f"done {len(done)}  partial {len(partial)}  pending {len(pending)}  of {len(reciters)}; {total_bytes / 1024 ** 3:.1f} GiB mirrored")
    for r in partial:
        print(f"  partial: {r.slug} ({state[r.slug].get('failures')} failures)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="maqra", description="Mirror, verify, package, and publish everyayah.com recitations.")
    p.add_argument("--version", action="version", version=f"maqra {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="list reciter sets and their mirror status")
    _add_selection(s)
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("survey", help="re-read every upstream folder listing into state/survey.json")
    _add_selection(s)
    s.set_defaults(fn=cmd_survey)

    s = sub.add_parser("mirror", help="download and verify the per-ayah audio")
    _add_selection(s)
    s.add_argument("--workers", type=int, default=8, help="parallel downloads (default 8)")
    s.add_argument("--no-zip", action="store_true", help="never use 000_versebyverse.zip; fetch loose files only")
    s.add_argument("--keep-zip", action="store_true", help="keep the downloaded bulk zip under data/_tmp")
    s.add_argument("--force", action="store_true", help="re-run sets already marked done")
    s.set_defaults(fn=cmd_mirror)

    s = sub.add_parser("verify", help="re-hash the local audio against the committed manifests")
    _add_selection(s)
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("extras", help="timings, ayah images, site files, tools (all when no flag is given)")
    _add_selection(s)
    s.add_argument("--workers", type=int, default=8)
    s.add_argument("--timings", action="store_true")
    s.add_argument("--images", action="store_true")
    s.add_argument("--tools", action="store_true")
    s.add_argument("--site", action="store_true")
    s.add_argument("--offline-zip", action="store_true", help="also fetch the Shaatree+Walk offline zip (1 GB)")
    s.add_argument("--include-exe", action="store_true", help="also mirror the unsigned mp3splt .exe")
    s.set_defaults(fn=cmd_extras)

    s = sub.add_parser("package", help="build per-surah zips for GitHub Releases")
    _add_selection(s)
    s.add_argument("--releases", type=Path, default=DEFAULT_RELEASES, help="output root (default: data/releases)")
    s.set_defaults(fn=cmd_package)

    s = sub.add_parser("publish-github", help="create one GitHub Release per set and upload its assets")
    _add_selection(s)
    s.add_argument("--releases", type=Path, default=DEFAULT_RELEASES)
    s.add_argument("--repo", default="Abdalla-Eldoumani/maqra")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_publish_github)

    s = sub.add_parser("publish-hf", help="upload sets to Hugging Face, one dataset per set")
    _add_selection(s)
    s.add_argument("--namespace", default="maqra-project", help="HF user or organization")
    s.add_argument("--index", action="store_true", help="publish the registry, manifests, and timings as <namespace>/maqra")
    s.add_argument("--images", action="store_true", help="publish the ayah images as <namespace>/ayah-images")
    s.add_argument("--workers", type=int, default=None)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_publish_hf)

    s = sub.add_parser("status", help="summarize mirror state")
    _add_selection(s)
    s.set_defaults(fn=cmd_status)
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
