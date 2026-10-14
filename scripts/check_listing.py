"""Checks the distro folders a change touches, and says which to build or remove.

    python scripts/check_listing.py BASE HEAD [--pr-author LOGIN] [--many]
    python scripts/check_listing.py --slug SLUG
    python scripts/check_listing.py --all

BASE and HEAD are commits. Without --many (pull requests) the change must stay
inside one distros/<slug>/ folder, compared with where it branched from BASE;
with --many (a push to main) everything between BASE and HEAD counts. --slug
checks one existing folder (a rebuild by hand); --all checks every folder (the
monthly rebuild). Each touched folder that still exists must
hold linuxlive.yaml, listing.yaml and its art (PNG or JPEG in assets/), and
may hold scripts (text, in scripts/) and files (in files/) its spec names, at
most 30 MB in all, with a valid listing; with --pr-author, the listing's author
must be the pull request's author.

A distro whose spec runs code of its own (scripts or GitHub repos) is listed,
with every script and repo, in the job summary for the reviewer.

Writes build=<JSON list>, remove=<JSON list> and code=<JSON list> (the distros
with code of their own) to $GITHUB_OUTPUT when set, and prints LISTING OK when
everything passes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,38})[a-z0-9]")
# Taken by linuxlive's own example distros and the Library's index page.
RESERVED = {"lawn-darts-linux", "testos", "index"}
LICENSES = {"MIT-0", "MIT", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0"}
MAX_BYTES = 30 * 1024 * 1024
MAX_SCRIPT_BYTES = 256 * 1024
FIELDS = {"name": 60, "author": 39, "tagline": 100, "about": 600, "credits": 400, "license": 20}
MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}


def changed(base: str, head: str, since_branch: bool) -> list[str]:
    span = f"{base}...{head}" if since_branch else f"{base}..{head}"
    out = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "--no-renames", span],
        check=True, capture_output=True, text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def check_folder(slug: str, pr_author: str | None) -> list[str]:
    problems = []
    folder = ROOT / "distros" / slug
    say = lambda msg: problems.append(f"distros/{slug}: {msg}")  # noqa: E731
    if not SLUG.fullmatch(slug):
        say("the folder name must be 3 to 40 lowercase letters, digits and dashes, not starting or ending with a dash")
    if slug in RESERVED:
        say("that name is taken")
    files = [p for p in folder.rglob("*") if not p.is_dir()]
    total = 0
    for p in files:
        rel = p.relative_to(folder).as_posix()
        if p.is_symlink():
            say(f"{rel} is a symbolic link")
            continue
        total += p.stat().st_size
        if rel in ("linuxlive.yaml", "listing.yaml") or rel.startswith("files/"):
            continue
        if rel.startswith("scripts/"):
            data = p.read_bytes()
            if b"\0" in data or len(data) > MAX_SCRIPT_BYTES:
                say(f"{rel}: scripts must be text files of at most {MAX_SCRIPT_BYTES >> 10} KB")
            continue
        suffix = p.suffix.lower()
        if not rel.startswith("assets/") or suffix not in MAGIC:
            say(f"{rel}: only linuxlive.yaml, listing.yaml, PNG or JPEG files in assets/, scripts in scripts/ and files in files/ belong here")
        elif not p.read_bytes().startswith(MAGIC[suffix]):
            say(f"{rel} is not really a {suffix[1:].upper()} file")
    if total > MAX_BYTES:
        say(f"the folder holds {total} bytes, more than {MAX_BYTES}")

    try:
        listing = yaml.safe_load((folder / "listing.yaml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        say("listing.yaml is missing")
        listing = None
    except yaml.YAMLError as exc:
        say(f"listing.yaml is not valid YAML: {exc}")
        listing = None
    if listing is not None:
        if not isinstance(listing, dict):
            say("listing.yaml must be a mapping of fields")
        else:
            for key in sorted(set(listing) - set(FIELDS)):
                say(f"listing.yaml: unknown field {key!r}")
            for key, limit in FIELDS.items():
                value = listing.get(key)
                if not isinstance(value, str) or not value.strip():
                    say(f"listing.yaml: {key} is missing or empty")
                elif len(value) > limit:
                    say(f"listing.yaml: {key} is {len(value)} characters, at most {limit}")
            if listing.get("license") not in LICENSES:
                say(f"listing.yaml: license must be one of {', '.join(sorted(LICENSES))}")
            if pr_author and str(listing.get("author", "")).lower() != pr_author.lower():
                say(f"listing.yaml: author is {listing.get('author')!r}, but the pull request is by {pr_author!r}")

    try:
        spec = yaml.safe_load((folder / "linuxlive.yaml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        say("linuxlive.yaml is missing")
        spec = None
    except yaml.YAMLError as exc:
        say(f"linuxlive.yaml is not valid YAML: {exc}")
        spec = None
    # The full spec check is the pipeline's own, in the build; here only that
    # its art lies inside this folder.
    branding = spec.get("branding") if isinstance(spec, dict) else None
    if isinstance(branding, dict):
        for key in ("wallpaper", "logo"):
            path = branding.get(key)
            if isinstance(path, str):
                target = (folder / path).resolve()
                if not target.is_relative_to(folder.resolve()) or not target.is_file():
                    say(f"linuxlive.yaml: branding.{key} {path!r} is not a file in this folder")
    if isinstance(spec, dict):
        for where, path in spec_paths(spec):
            target = (folder / path).resolve()
            if not target.is_relative_to(folder.resolve()) or not target.is_file():
                say(f"linuxlive.yaml: {where} {path!r} is not a file in this folder")
    return problems


def spec_paths(spec: dict) -> list[tuple[str, str]]:
    """The files a spec's own additions name: files' src and every script."""
    out = []
    for i, entry in enumerate(spec.get("files") or []):
        if isinstance(entry, dict) and isinstance(entry.get("src"), str):
            out.append((f"files[{i}].src", entry["src"]))
    scripts = spec.get("scripts") or {}
    if isinstance(scripts, dict):
        for kind, paths in scripts.items():
            for i, path in enumerate(paths if isinstance(paths, list) else []):
                if isinstance(path, str):
                    out.append((f"scripts.{kind}[{i}]", path))
    return out


def own_code(slug: str) -> list[str]:
    """What a distro runs of its own, for the reviewer: scripts and GitHub repos."""
    try:
        spec = yaml.safe_load((ROOT / "distros" / slug / "linuxlive.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(spec, dict):
        return []
    lines = [f"script ({where.split('[')[0].split('.')[1]}): distros/{slug}/{path}" for where, path in spec_paths(spec) if where.startswith("scripts.")]
    for repo in spec.get("repos") or []:
        if isinstance(repo, dict):
            lines.append(f"repo: {repo.get('url')}/tree/{repo.get('commit')} runs: {repo.get('run')}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?")
    parser.add_argument("head", nargs="?")
    parser.add_argument("--slug")
    parser.add_argument("--all", action="store_true", help="every distro folder (the monthly rebuild)")
    parser.add_argument("--pr-author")
    parser.add_argument("--many", action="store_true", help="allow several folders (a push to main)")
    args = parser.parse_args()

    problems = []
    slugs = set()
    if args.all:
        paths = [f"distros/{d.name}/listing.yaml" for d in sorted((ROOT / "distros").iterdir()) if d.is_dir()]
    elif args.slug:
        paths = [f"distros/{args.slug}/listing.yaml"]
        if not (ROOT / "distros" / args.slug).is_dir():
            problems.append(f"distros/{args.slug}: no such folder")
            paths = []
    elif args.base and args.head:
        paths = changed(args.base, args.head, since_branch=not args.many)
    else:
        parser.error("give BASE and HEAD, or --slug")
    for path in paths:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "distros":
            slugs.add(parts[1])
        elif not args.many:
            problems.append(f"{path}: a pull request may only change files in one distros/<slug>/ folder")
    if not (args.many or args.all) and len(slugs) > 1:
        problems.append(f"one distro per pull request; this one changes {', '.join(sorted(slugs))}")
    build = sorted(s for s in slugs if (ROOT / "distros" / s).is_dir())
    # Removal deletes library/<slug>/ in R2, so only ever a well-formed slug.
    remove = sorted(s for s in slugs - set(build) if SLUG.fullmatch(s))
    for slug in build:
        problems += check_folder(slug, args.pr_author)

    if problems:
        print("LISTING CHECK FAILED:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    code = {slug: own_code(slug) for slug in build}
    code = {slug: lines for slug, lines in code.items() if lines}
    for slug, lines in code.items():
        print(f"OWN CODE in {slug} (review every line before merging):\n- " + "\n- ".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY") and code:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            for slug, lines in code.items():
                out.write(f"### {slug} runs code of its own\n\nRead every script and repo before merging: they run as root in the build"
                          " and on every computer that installs it.\n\n" + "".join(f"- {line}\n" for line in lines) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"build={json.dumps(build)}\nremove={json.dumps(remove)}\ncode={json.dumps(sorted(code))}\n")
    print(f"LISTING OK (build: {', '.join(build) or 'none'}; remove: {', '.join(remove) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
