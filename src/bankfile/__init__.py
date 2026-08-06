"""bankfile: one schema for every bank file format.

The public surface is deliberately tiny. `parse(path)` reads a file and returns a `Statement`
whose shape is fixed by `corpus/schema/statement.schema.json`, whatever the format underneath.
Everything else in this package is an implementation detail a caller should never need.
"""

from __future__ import annotations

from pathlib import Path

from bankfile.detect import UnknownFormatError, detect
from bankfile.model import ReadWarning, Source, Statement, Transaction
from bankfile.mt940_adapter import read_mt940
from bankfile.ofx.reader import read_ofx

__all__ = [
    "ReadWarning",
    "Source",
    "Statement",
    "Transaction",
    "UnknownFormatError",
    "parse",
    "parse_bytes",
]


def parse_bytes(data: bytes, *, path: str | None = None) -> Statement:
    """Read a statement from bytes.

    Bytes, never a str, and it is the most load bearing line in this file. The documented way to
    use `ofxparse` is to hand it a text mode file object, and that is measured as the one call
    path that dies on a character outside latin-1, because the library round trips through a
    hard coded latin-1 encode. Choosing the encoding is the reader's job, and it cannot do that
    job once someone else has already guessed.
    """
    if detect(data) == "OFX":
        return read_ofx(data, path=path)
    return read_mt940(data, path=path)


def parse(path: str | Path) -> Statement:
    file = Path(path)
    return parse_bytes(file.read_bytes(), path=str(file))
