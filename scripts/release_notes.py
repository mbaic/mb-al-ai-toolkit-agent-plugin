#!/usr/bin/env python3
"""Extract one version's section from CHANGELOG.md, for use as release notes.

Usage:
    python3 scripts/release_notes.py 0.1.0

Prints the body of that version's section to stdout. Exits 1 if the version has
no section, which is deliberate: a release with no changelog entry is a mistake,
not something to paper over with empty notes.
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(REPO_ROOT, "CHANGELOG.md")


def extract(version: str, text: str) -> str | None:
    """Return the section body for `version`, or None if absent.

    Matches both `## [0.1.0] — date` (reference-link style) and `## 0.1.0 — date`.
    """
    escaped = re.escape(version)
    heading = re.compile(rf"^##\s+\[?{escaped}\]?(?:\s|$)", re.M)

    match = heading.search(text)
    if not match:
        return None

    # Skip the remainder of the heading line (the date, "— 2026-08-07"), which
    # belongs to the heading rather than the notes.
    line_end = text.find("\n", match.end())
    start = len(text) if line_end == -1 else line_end + 1

    following = re.compile(r"^##\s+", re.M).search(text, start)
    body = text[start:following.start()] if following else text[start:]

    # Drop trailing reference-link definitions ("[0.1.0]: https://...") — they are
    # changelog plumbing, not release notes.
    lines = [ln for ln in body.split("\n") if not re.match(r"^\[[^\]]+\]:\s", ln)]

    return "\n".join(lines).strip("\n").strip()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: release_notes.py <version>", file=sys.stderr)
        return 2

    version = sys.argv[1].lstrip("v")

    if not os.path.isfile(CHANGELOG):
        print(f"error: {CHANGELOG} not found", file=sys.stderr)
        return 1

    with open(CHANGELOG, encoding="utf-8") as handle:
        text = handle.read()

    body = extract(version, text)
    if body is None:
        print(
            f"error: CHANGELOG.md has no section for version {version}. "
            f"Add a '## [{version}] — <date>' entry before releasing.",
            file=sys.stderr,
        )
        return 1
    if not body:
        print(f"error: the {version} section in CHANGELOG.md is empty.", file=sys.stderr)
        return 1

    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
