#!/usr/bin/env python3
"""Print the CHANGELOG.md section of one version.

A GitHub Release needs a body, and the only honest source for it is the file that already had to
be written. Retyping the notes into the release form is how the two drift, and for this library a
release note that disagrees with the changelog is worse than no note at all: someone who suspects
a wrong amount reads both and has to decide which one lies.

Exits non-zero when the version has no section, so a release cannot ship with an empty body and
nobody discovers it after the fact.

    changelog_section.py 0.2.0 [--file CHANGELOG.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Keep a Changelog puts every version behind a level 2 heading with the version in brackets:
# "## [0.2.0] - 2026-08-06". The date is optional here because an unreleased section may not
# carry one yet, and refusing to read it would make this script fail on a file that is valid.
HEADING = re.compile(r"^##\s+\[(?P<version>[^\]]+)\]")


def section(text: str, version: str) -> str | None:
    """Return the body of the section for `version`, heading excluded, or None if absent."""
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match is None:
            continue
        if start is not None:
            # The next version heading closes the one we are reading.
            return "\n".join(lines[start:index]).strip("\n")
        if match.group("version") == version:
            start = index + 1
    if start is None:
        return None
    return "\n".join(lines[start:]).strip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="version to extract, without the leading v")
    parser.add_argument("--file", default="CHANGELOG.md", help="changelog path")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"no changelog at {path}", file=sys.stderr)
        return 2

    body = section(path.read_text(encoding="utf-8"), args.version)
    if body is None or not body.strip():
        print(f"CHANGELOG.md has no section for {args.version}", file=sys.stderr)
        return 1

    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
