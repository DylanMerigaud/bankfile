"""The OFX 1.x header block and the OFX 2.x XML prologue, read from BYTES.

Reading rules, sections 1 and 2. `read_header` takes bytes and never a str: the codec is
declared INSIDE the file, so a caller who already opened it in text mode has guessed, and the
corpus measures that guess failing on the first byte outside latin-1.

Nothing here raises. A header block we cannot trust downgrades what is known about the file, it
does not cost the statement: the body is decoded and returned either way.
"""

from __future__ import annotations

import codecs
import re
from dataclasses import dataclass

from bankfile.model import ReadWarning

# The nine keys OFX 1.x defines. They are needed as a LIST, not as a validation: Wells Fargo
# writes the whole block on one physical line, and knowing the key names is the only way to cut
# it back into pairs.
KNOWN_KEYS = (
    "OFXHEADER",
    "DATA",
    "VERSION",
    "SECURITY",
    "ENCODING",
    "CHARSET",
    "COMPRESSION",
    "OLDFILEUID",
    "NEWFILEUID",
)

# The format defaults, applied when the block cannot be trusted (reading rules, section 2).
DEFAULTS = {"VERSION": "102", "DATA": "OFXSGML", "CHARSET": "1252"}

# Reading rules, section 1, step 3. A TABLE, never a codec name built by concatenation: that is
# how `ofxparse` turns the legal value NONE into the codec `cpNONE` and loses the whole file.
# NONE goes to cp1252 by choice, recorded as such: it is an ASCII superset that cannot raise on
# any byte, where `ofxtools` reads NONE as utf-8.
CHARSET_CODECS = {
    "1252": "cp1252",
    "8859-1": "iso-8859-1",
    "ISO-8859-1": "iso-8859-1",
    "NONE": "cp1252",
}

# Zero-width cut before each known key, so `OFXHEADER:100DATA:OFXSGML` becomes two fragments.
_KEY_BOUNDARY = re.compile("(?=(?:" + "|".join(KNOWN_KEYS) + "):)")

_XML_DECLARED_ENCODING = re.compile(rb"""<\?xml\b[^>]*?encoding\s*=\s*["']([^"']+)["']""")
_OFX_INSTRUCTION = re.compile(r"<\?OFX\b(.*?)\?>", re.IGNORECASE | re.DOTALL)
_ATTRIBUTE = re.compile(r"""([A-Za-z][\w.-]*)\s*=\s*["']([^"']*)["']""")
# An XML prologue item: declaration, processing instruction, comment or doctype. The body starts
# after the last of them.
_PROLOGUE_ITEM = re.compile(r"\s*(?:<\?.*?\?>|<!--.*?-->|<![^>]*>)\s*", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Header:
    """What the head of the file declares, plus the decoded body it precedes."""

    values: dict[str, str]
    encoding: str
    is_xml: bool
    body: str
    warnings: list[ReadWarning]


def read_header(data: bytes) -> Header:
    """Read the header of an OFX 1.x or 2.x document and decode the body behind it."""
    warnings: list[ReadWarning] = []
    # A byte order mark is not a header key. Left in place it becomes the first three characters
    # of `OFXHEADER`, and the value declared there is lost without a sound.
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8) :]
    if _is_xml_document(data):
        return _read_xml_header(data, warnings)
    return _read_sgml_header(data, warnings)


def _is_xml_document(data: bytes) -> bool:
    """OFX 2.x opens on a processing instruction, which OFX 1.x never has."""
    start = data[:64].lstrip().upper()
    return start.startswith((b"<?XML", b"<?OFX"))


def _read_sgml_header(data: bytes, warnings: list[ReadWarning]) -> Header:
    end = data.find(b"<")
    # First pass on iso-8859-1, which maps all 256 byte values and therefore cannot fail, only
    # to learn which codec the file declares. Every attested header block is ASCII; the payload
    # behind it is not, which is why the real decode waits for this answer. With no '<' the
    # whole file is the block, and reading it as nothing would answer cp1252 to a file that
    # declares utf-8.
    declared, _ = _parse_block((data if end < 0 else data[:end]).decode("iso-8859-1"), [])
    codec, field = _pick_codec(declared, warnings)
    text, encoding = _decode(data, codec, field, warnings)
    _warn_if_usascii_is_a_lie(data, declared, encoding, warnings)

    cut = text.find("<")
    if cut < 0:
        warnings.append(
            ReadWarning("header", None, None, "no '<' anywhere in the file, there is no body")
        )
    body = text[cut:] if cut >= 0 else ""
    values, trusted = _parse_block(text[:cut] if cut >= 0 else text, warnings)
    if not trusted or not values:
        _apply_defaults(values, warnings)
    return Header(values=values, encoding=encoding, is_xml=False, body=body, warnings=warnings)


def _parse_block(text: str, warnings: list[ReadWarning]) -> tuple[dict[str, str], bool]:
    """Cut the `KEY:VALUE` block into pairs. Returns the pairs and whether they can be trusted."""
    values: dict[str, str] = {}
    trusted = True
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Section 2: a blank line is NOT the end of the block, at the start of the file or
        # between two headers. Requiring the blank separator, or stopping at it, is the measured
        # bug that costs `ofxparse` all nine headers on two of the fixtures.
        if not line:
            continue
        if ":" not in line:
            warnings.append(
                ReadWarning("header", None, line, "line without a ':', the header block ends here")
            )
            return values, False
        fragments = _cut_into_pairs(line)
        for fragment in fragments:
            key, separator, value = fragment.partition(":")
            # Only inside a line that WAS re-cut can a fragment fail to be one pair, and then it
            # is the case the upstream fix cannot handle: an unknown key swallowed into the
            # value of the header before it. Drop that fragment ALONE. Dropping the whole line
            # with it throws away the ENCODING and CHARSET that were cut cleanly beside it, and
            # a file that declares utf-8 then comes back decoded as cp1252, with a payee that
            # reads as plausible and is wrong.
            if len(fragments) > 1 and (not separator or ":" in value):
                trusted = False
                warnings.append(
                    ReadWarning(
                        "header",
                        None,
                        fragment,
                        "fragment of a collapsed header carrying an unknown key, dropped",
                    )
                )
                continue
            _store(values, key, value, warnings)
    return values, trusted


def _cut_into_pairs(line: str) -> list[str]:
    """One physical line into `KEY:VALUE` fragments, cut on the known key names (Wells Fargo).

    A line carrying a single colon is a single pair and there is nothing to re-cut. Beyond that,
    the extra colons are either nine headers collapsed onto one line or a value that simply
    contains a colon, and only the presence of a known key name inside the line tells the two
    apart. Cutting unconditionally would turn `NEWFILEUID:20260115T10:00:00` into a header block
    we refuse to read.
    """
    if line.count(":") <= 1:
        return [line]
    fragments = [fragment for fragment in _KEY_BOUNDARY.split(line) if fragment]
    return fragments if len(fragments) > 1 else [line]


def _store(values: dict[str, str], key: str, value: str, warnings: list[ReadWarning]) -> None:
    name = key.strip().upper()
    text = value.strip()
    previous = values.get(name)
    # The last declaration wins, as everywhere else in this reader, but the one it replaces is
    # not allowed to leave without a word: on CHARSET or ENCODING it is the codec of the file
    # that just changed.
    if previous is not None and previous != text:
        warnings.append(
            ReadWarning(
                "header", name, previous, f"{name} declared twice, {text!r} replaces {previous!r}"
            )
        )
    values[name] = text


def _apply_defaults(values: dict[str, str], warnings: list[ReadWarning]) -> None:
    missing = [key for key in DEFAULTS if key not in values]
    values.update({key: DEFAULTS[key] for key in missing})
    applied = f" for {', '.join(missing)}" if missing else ""
    message = f"header block untrusted, format defaults applied{applied}"
    warnings.append(ReadWarning("header", None, None, message))


def _pick_codec(values: dict[str, str], warnings: list[ReadWarning]) -> tuple[str, str]:
    """Reading rules, section 1: `ENCODING:UTF-8` first, then the CHARSET table."""
    if _normalised(values.get("ENCODING", "")).replace("-", "").replace("_", "") == "UTF8":
        return "utf-8", "ENCODING"
    charset = values.get("CHARSET", "")
    key = _normalised(charset)
    if not key:
        return "cp1252", "CHARSET"
    codec = CHARSET_CODECS.get(key)
    if codec is None:
        warnings.append(
            ReadWarning(
                "encoding",
                "CHARSET",
                charset,
                f"CHARSET is none of {', '.join(CHARSET_CODECS)}, decoded as cp1252",
            )
        )
        return "cp1252", "CHARSET"
    return codec, "CHARSET"


def _decode(data: bytes, codec: str, field: str, warnings: list[ReadWarning]) -> tuple[str, str]:
    """Decode with the declared codec, then retry. Never `errors='ignore'`, which truncates a
    payee name without saying so, and never ASCII, which is nobody's declaration."""
    # dict.fromkeys keeps the order and drops the duplicate when cp1252 is what was declared.
    for candidate in dict.fromkeys((codec, "cp1252")):
        try:
            text = data.decode(candidate)
        except UnicodeDecodeError as failure:
            warnings.append(
                ReadWarning(
                    "encoding",
                    field,
                    candidate,
                    f"{candidate} cannot decode byte 0x{data[failure.start]:02X} at offset "
                    f"{failure.start}, retrying with the next codec",
                )
            )
            continue
        return text, candidate
    # iso-8859-1 is last because it maps all 256 byte values, so this line cannot fail.
    return data.decode("iso-8859-1"), "iso-8859-1"


def _warn_if_usascii_is_a_lie(
    data: bytes, values: dict[str, str], encoding: str, warnings: list[ReadWarning]
) -> None:
    """`ENCODING:USASCII` states a byte width, and CHARSET names the code page, so a high byte
    is decoded rather than dropped. The declaration is still false, and silence about it is how
    an encoding question gets settled twice, differently, in two places."""
    if _normalised(values.get("ENCODING", "")) != "USASCII":
        return
    offset = next((index for index, byte in enumerate(data) if byte > 0x7F), None)
    if offset is None:
        return
    warnings.append(
        ReadWarning(
            "encoding",
            "ENCODING",
            values["ENCODING"],
            f"declared USASCII but byte 0x{data[offset]:02X} at offset {offset} is not ASCII, "
            f"decoded with {encoding} as CHARSET says",
        )
    )


def _read_xml_header(data: bytes, warnings: list[ReadWarning]) -> Header:
    """OFX 2.x: the codec comes from the XML declaration, and the `<?OFX ...?>` attributes take
    the place of the 1.x block. The absence of that block is normal here and must never trigger
    the untrusted-header path."""
    text, encoding = _decode(data, _xml_codec(data, warnings), "encoding", warnings)
    instruction = _OFX_INSTRUCTION.search(text)
    values = (
        {key.upper(): value for key, value in _ATTRIBUTE.findall(instruction.group(1))}
        if instruction is not None
        else {}
    )

    cut = 0
    while (item := _PROLOGUE_ITEM.match(text, cut)) is not None:
        cut = item.end()
    # The body starts at the document, not at the file: the prologue is already in `values`, and
    # handing `<?xml ...?>` to the tag reader would make it invent a node out of a declaration.
    start = text.find("<", cut)
    if start < 0:
        message = "nothing but a prologue in the file, there is no body"
        warnings.append(ReadWarning("header", None, None, message))
    return Header(
        values=values,
        encoding=encoding,
        is_xml=True,
        body=text[start:] if start >= 0 else "",
        warnings=warnings,
    )


def _xml_codec(data: bytes, warnings: list[ReadWarning]) -> str:
    match = _XML_DECLARED_ENCODING.search(data, 0, 512)
    if match is None:
        # What the XML specification requires when the declaration omits the encoding.
        return "utf-8"
    declared = match.group(1).decode("iso-8859-1")
    try:
        # Guarded, so an unusable value is reported as a header value we could not read and not
        # as a LookupError naming a codec nobody wrote. XML allows any registered charset, so a
        # four-entry table would refuse files the format accepts.
        name = codecs.lookup(declared).name
        # The probe is what separates a text codec from base64, hex or rot13: `codecs.lookup`
        # accepts all four and `bytes.decode` raises LookupError on the last three, which would
        # leave this module the only one in the reader that can end a read on a traceback. Only
        # LookupError is caught here, so utf-16, a text codec that cannot read a lone byte, is
        # not rejected by its own probe.
        b"\x00".decode(name)
    except UnicodeDecodeError:
        return name
    except LookupError:
        warnings.append(
            ReadWarning(
                "encoding",
                "encoding",
                declared,
                "the XML declaration names an encoding that cannot decode text, read as utf-8",
            )
        )
        return "utf-8"
    return name


def _normalised(value: str) -> str:
    return value.strip().upper()
