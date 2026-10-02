#!/usr/bin/env python3
"""Stamp the root VERSION into the delimited tokens in the docs/ site.

The site is static HTML served by GitHub Pages, so it cannot read VERSION at
render time. Instead it carries tokens of the form::

    <!--VERSION-->x.y.z<!--/VERSION-->

and this script rewrites whatever sits between the delimiters. It targets the
site tree only: root markdown never carries a version number and must never be
touched by this script.

The run is idempotent. A second run reports nothing because the first left
nothing to change. Only files actually rewritten are printed.

Every site page's local stylesheet and script links are also versioned by
content: each carries ?v=<hash> of the file it names, so a deploy that changes
the file changes its address and no browser pairs a new page with a cached old
stylesheet. A link to a missing file is an error that names the path.

Usage:
    python stamp_version.py
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent
VERSION_FILE = REPO_ROOT / "VERSION"
SITE_DIR = REPO_ROOT / "docs"
SITE_SUFFIXES = (".html", ".css", ".js", ".json", ".svg", ".xml", ".webmanifest")

TOKEN = re.compile(r"(<!--VERSION-->)(.*?)(<!--/VERSION-->)", re.DOTALL)

# A local stylesheet or script link plus any query it already carries. A colon
# in the path means a scheme, so absolute URLs never match; root-absolute and
# protocol-relative paths are left alone by version_assets.
ASSET_HASH_LENGTH = 10
ASSET_LINK = re.compile(
    r'\b(?P<attribute>href|src)="(?P<path>[^"?#:]+\.(?:css|js))(?:\?[^"#]*)?"'
)


def read_version() -> str:
    """Return the version string from the repository-root VERSION file."""
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def site_files(site_dir: Path) -> list[Path]:
    """Return every stampable file in the site tree, in a stable order."""
    return sorted(
        p
        for p in site_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SITE_SUFFIXES
    )


def stamp_text(text: str, version: str) -> tuple[str, int]:
    """Return the text with every token's payload set to version, plus the count.

    The replacement is a callable, not a template string, so a version
    containing a backslash or a group reference is inserted literally.
    """
    return TOKEN.subn(lambda m: f"{m.group(1)}{version}{m.group(3)}", text)


def stamp_file(path: Path, version: str) -> int:
    """Rewrite path in place if any token's payload differs. Return tokens found."""
    original = path.read_text(encoding="utf-8")
    stamped, count = stamp_text(original, version)
    if count and stamped != original:
        path.write_text(stamped, encoding="utf-8")
    return count


def asset_hash(path: Path) -> str:
    """Return the short content hash of one asset, with CRLF read as LF.

    Folding the line endings means a Windows checkout and the LF blob GitHub
    serves agree, so a run on another machine does not churn every page.
    """
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()[:ASSET_HASH_LENGTH]


def version_assets(page: Path) -> bool:
    """Set ?v=<hash> on every local asset link in page. Return True if changed.

    The page is read and written as bytes so its line endings survive.
    """
    original = page.read_bytes().decode("utf-8")

    def versioned(m: re.Match[str]) -> str:
        link = m.group("path")
        if link.startswith("/"):
            return m.group(0)
        asset = page.parent / unquote(link)
        if not asset.is_file():
            raise FileNotFoundError(f"{page} links {link}; {asset} does not exist")
        return f'{m.group("attribute")}="{link}?v={asset_hash(asset)}"'

    stamped = ASSET_LINK.sub(versioned, original)
    if stamped == original:
        return False
    page.write_bytes(stamped.encode("utf-8"))
    return True


def main() -> int:
    if not VERSION_FILE.is_file():
        print(f"ERROR: no VERSION file at {VERSION_FILE}", file=sys.stderr)
        return 1
    if not SITE_DIR.is_dir():
        print(f"ERROR: no site directory at {SITE_DIR}", file=sys.stderr)
        return 1

    version = read_version()
    if not version:
        print(f"ERROR: {VERSION_FILE} is empty", file=sys.stderr)
        return 1

    changed: list[Path] = []
    tokens = 0
    for path in site_files(SITE_DIR):
        before = path.read_text(encoding="utf-8")
        found = stamp_file(path, version)
        tokens += found
        if found and path.read_text(encoding="utf-8") != before:
            changed.append(path)

    versioned: list[Path] = []
    for path in site_files(SITE_DIR):
        if path.suffix.lower() != ".html":
            continue
        try:
            if version_assets(path):
                versioned.append(path)
        except FileNotFoundError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
    for path in versioned:
        print(f"versioned assets: {path.relative_to(REPO_ROOT).as_posix()}")

    if tokens == 0:
        print(f"No <!--VERSION--> tokens found under {SITE_DIR.name}/")
        return 0

    if not changed:
        print(f"{tokens} token(s) already at {version}; nothing to do.")
        return 0

    for path in changed:
        print(f"stamped {version}: {path.relative_to(REPO_ROOT).as_posix()}")
    print(f"{len(changed)} file(s) updated, {tokens} token(s) checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
