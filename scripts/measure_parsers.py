#!/usr/bin/env python3
"""Run the existing OFX parsers over every corpus fixture and record what they ACTUALLY do.

This plan already paid for one mistake of the other kind: a library's regex was read, a
behaviour was inferred from it, and the inference was wrong. The rule that came out of it is
to execute instead of deduce. A corpus note claiming "ofxparse chokes here" without having
watched it choke is that same mistake wearing a lab coat.

Two parsers, because the disagreement is the useful part: `ofxparse` 0.21 is the abandoned
incumbent, `ofxtools` 1.1.1 is the maintained strict one. Several fixtures pass one and fail
the other, which tells us exactly what we inherit for free and what we have to handle.

Both are deliberately NOT dependencies of this package: nothing here should pull in an
abandoned parser, and CI must not depend on it. Run this by hand in a throwaway environment
and commit the dated JSON it prints:

    uv venv /tmp/measure && VIRTUAL_ENV=/tmp/measure uv pip install ofxparse ofxtools
    /tmp/measure/bin/python scripts/measure_parsers.py > corpus/measurements/2026-08-05.json
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

BANKS = Path(__file__).resolve().parent.parent / "corpus" / "banks"
TRUNCATE = 160


def measure_ofxparse(path: Path, *, text_mode: bool) -> dict[str, object]:
    """text_mode reproduces the usage ofxparse's own README documents: parse(open(path)).

    The distinction is not cosmetic. In text mode the library round-trips through a hard
    coded latin-1 encode, so any character above U+00FF dies there whatever the file
    declares and whatever encoding you pass to open(). Measuring only the binary path would
    mark fixtures green that every documented caller breaks on.
    """
    from ofxparse import OfxParser

    try:
        handle = open(path) if text_mode else io.BytesIO(path.read_bytes())  # noqa: SIM115, PTH123
        ofx = OfxParser.parse(handle)
    except Exception as exc:  # the failure IS the measurement, whatever it is
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        transactions = ofx.account.statement.transactions
    except Exception as exc:  # the failure IS the measurement, whatever it is
        return {"ok": True, "reaching_transactions": f"{type(exc).__name__}: {exc}"}
    first = transactions[0] if transactions else None
    return {
        "ok": True,
        # Headers actually read. On the blank-line fixtures the parser does not raise, it
        # returns an EMPTY dict: nine headers silently become zero, the declared encoding
        # included. A field lost in silence is worse than an exception.
        "headers_read": len(dict(getattr(ofx, "headers", {}) or {})),
        "transactions": len(transactions),
        "first": None
        if first is None
        else {
            "type": getattr(first, "type", None),
            "amount": str(getattr(first, "amount", None)),
            "date": str(getattr(first, "date", None)),
            "payee": getattr(first, "payee", None),
            "memo": getattr(first, "memo", None),
            "checknum": getattr(first, "checknum", None),
        },
    }


def measure_ofxtools(path: Path) -> dict[str, object]:
    from ofxtools.Parser import OFXTree

    try:
        tree = OFXTree()
        tree.parse(str(path))
        ofx = tree.convert()
    except Exception as exc:  # the failure IS the measurement, whatever it is
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    statements = getattr(ofx, "statements", [])
    transactions = statements[0].transactions if statements else []
    return {
        "ok": True,
        "transactions": len(transactions),
        "first": str(transactions[0])[:TRUNCATE] if transactions else None,
    }


def main() -> int:
    out = {}
    for fixture in sorted(BANKS.rglob("*")):
        if not fixture.is_file() or fixture.suffix == ".md":
            continue
        out[str(fixture.relative_to(BANKS))] = {
            "ofxparse_0_21_text_mode": measure_ofxparse(fixture, text_mode=True),
            "ofxparse_0_21_binary_mode": measure_ofxparse(fixture, text_mode=False),
            "ofxtools_1_1_1": measure_ofxtools(fixture),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
