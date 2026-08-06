#!/usr/bin/env python3
"""validate_corpus.py: the corpus is the asset, so it is validated like code.

It checks six things, and each one maps to a way this kind of repository rots:

  a fixture with no `.md`       a bank file nobody can explain becomes noise at the first
                                refactor.
  an `.md` with no fixture      a deviation described but not reproducible.
  unanonymised data             the corpus carries structure only. A full IBAN or an account
                                number is a leak even in a private repository: it will go
                                public.
  a note missing its four facts bank, format, source, and the deviation itself. The source
                                above all: a deviation nobody can trace back is no longer
                                checkable, it is just a claim.
  a fact left blank             a `- Bank:` bullet with nothing after it passes a substring
                                search and says nothing. We require a value.
  a note quoting an account     notes quote public issues, and a public issue sometimes
                                contains a real account number. The fixture is anonymised, so
                                the note has to be too.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "corpus" / "banks"
# The bank files borrowed from other projects' test suites. They are NOT ours and they were
# NOT anonymised by us, which is exactly why they need their own guard: an audit found a named
# person's real statement in here, with balances, a jewellery payment and four days of card
# spending across two towns. Our own leak scan had never looked at this directory.
VENDORED = ROOT / "tests" / "fixtures"
REVIEWED = ROOT / "tests" / "fixtures" / "REVIEWED.json"
LEAKS = (
    # A full IBAN.
    re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b"),
    # Thirteen digits or more, separators included. No upper bound and no trailing anchor:
    # the earlier version capped at 19 could not bite inside a longer run (the closing `\b`
    # failed while another digit followed), so a 22 digit account number, the most common
    # shape there is, went through without a word. Proven by running it.
    re.compile(r"\d(?:[ -]?\d){12,}"),
)
BULLETS = ("- Bank:", "- Format:", "- Sources:")
DEVIATION = "## The deviation"
# How much prose has to sit under "## The deviation" for the section to say anything. A
# heading followed by two words describes a deviation as poorly as a heading followed by
# nothing.
MINIMUM_DEVIATION = 200


def leaks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = []
    for rx in LEAKS:
        m = rx.search(text)
        if m:
            found.append(f"{path}: looks like unanonymised data ({m.group(0)!r})")
    return found


def check_note(note: Path, fixture: Path) -> list[str]:
    text = note.read_text(encoding="utf-8", errors="replace")
    faults = []
    # `[^\S\n]*` and not `\s*`: `\s` eats newlines, so an empty bullet found its "value" at
    # the start of the next line and passed. Proven by running the check against a note whose
    # bullets are all empty.
    faults += [
        f"{note}: {bullet} missing or has no value"
        for bullet in BULLETS
        if not re.search(rf"^{re.escape(bullet)}[^\S\n]*\S", text, re.M)
    ]
    body = re.search(rf"^{re.escape(DEVIATION)}$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not body:
        faults.append(f"{note}: no {DEVIATION} section")
    elif len(body.group(1).strip()) < MINIMUM_DEVIATION:
        faults.append(f"{note}: {DEVIATION} describes nothing ({len(body.group(1).strip())} chars)")
    if fixture.name not in text:
        # A note naming a fixture other than its neighbour was copied and never reread, and
        # it then describes the wrong file in silence.
        faults.append(f"{note}: does not name its own fixture {fixture.name}")
    return faults


def check_vendored() -> list[str]:
    """Every borrowed fixture must have been read by a human, and must not have moved since.

    A plain allow-list of strings would be useless here: these files legitimately contain
    IBAN-shaped account numbers and long digit runs, so the leak regexes fire on most of them.
    What we actually need to know is that a person looked at THIS EXACT CONTENT and cleared it.
    So the manifest stores a hash. Change one byte and the clearance no longer applies, and CI
    says so until somebody reads the file again.
    """
    if not VENDORED.is_dir():
        return []
    reviewed = json.loads(REVIEWED.read_text(encoding="utf-8")) if REVIEWED.exists() else {}
    faults = []
    seen = set()
    for f in sorted(VENDORED.rglob("*")):
        if not f.is_file() or f.name in ("REVIEWED.json", "README.md", "LICENSE"):
            continue
        key = str(f.relative_to(ROOT))
        seen.add(key)
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        entry = reviewed.get(key)
        if entry is None:
            faults.append(f"{key}: borrowed fixture never reviewed, add it to {REVIEWED.name}")
        elif entry.get("sha256") != digest:
            faults.append(
                f"{key}: changed since it was reviewed, read it again and update {REVIEWED.name}"
            )
    faults.extend(
        f"{key}: reviewed in {REVIEWED.name} but no longer in the tree"
        for key in sorted(set(reviewed) - seen)
    )
    return faults


def main() -> int:
    if not BANKS.is_dir():
        print(f"{BANKS} is missing")
        return 1
    faults: list[str] = []
    fixtures = [p for p in BANKS.rglob("*") if p.is_file() and p.suffix not in (".md",)]
    for f in fixtures:
        # The leak scan runs BEFORE anything else. A fixture dropped in without its note is
        # exactly the case where nobody reread the file, so it is where real bank data is
        # most likely to be sleeping.
        faults += leaks(f)
        note = f.with_suffix(".md")
        if not note.exists():
            faults.append(f"{f}: no .md note, nobody knows what this file illustrates")
        else:
            faults += check_note(note, f)
    for note in BANKS.rglob("*.md"):
        if note.name == "README.md":
            continue
        if not any(p.with_suffix(".md") == note for p in fixtures):
            faults.append(f"{note}: describes a deviation with no fixture, so not reproducible")
            continue
        faults += leaks(note)
    faults += check_vendored()
    for x in faults:
        print(f"  {x}")
    print(f"{len(fixtures)} fixtures, {len(faults)} faults")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
