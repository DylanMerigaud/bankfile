"""Work out which format a file is, from its bytes.

Sniffing beats trusting the extension, and not by a little. The corpus already holds `.qfx`
files that are OFX 1.0.2 SGML, `.ofx` files that are OFX 2.x XML, and MT940 ships as `.sta`,
`.mt940`, `.txt` or no extension at all depending on the bank. An extension is a hint someone
typed; the first bytes are what the file actually is.
"""

from __future__ import annotations

import re
from typing import Literal

Format = Literal["MT940", "OFX"]

# The OFX 1.x header block, an OFX 2.x processing instruction, or the root tag. The first is
# what almost every file leads with; the last two catch the ones where a blank line, a comment
# or a byte order mark got in front of it.
OFX_MARKS = (
    re.compile(rb"^\s*OFXHEADER\s*:", re.I),
    re.compile(rb"<\?OFX\b", re.I),
    re.compile(rb"<OFX>", re.I),
)
# MT940 field tags at the start of a line. `:20:` opens a statement and `:61:` opens a
# transaction line; requiring either one avoids matching a stray colon inside prose.
MT940_MARKS = (
    re.compile(rb"^:20:", re.M),
    re.compile(rb"^:61:", re.M),
)


class UnknownFormatError(ValueError):
    """Raised when nothing in the file identifies a format we can read.

    This is one of the two cases where failing IS the right answer, per section 0 of
    `corpus/reading-rules.md`: there is no usable statement block at all, so there is nothing to
    degrade gracefully into. Returning an empty statement here would be worse than raising,
    because an empty statement reconciles to zero and looks like a real answer.
    """


def detect(data: bytes) -> Format:
    head = data[:4096]
    if any(mark.search(head) for mark in OFX_MARKS):
        return "OFX"
    if any(mark.search(head) for mark in MT940_MARKS):
        return "MT940"
    msg = (
        "unrecognised file: no OFX header, no <OFX> tag and no MT940 :20: or :61: field "
        "in the first 4096 bytes"
    )
    raise UnknownFormatError(msg)
