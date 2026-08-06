"""What `read_header` owes the corpus, asserted on the real fixture BYTES.

Every input here is a file under `corpus/banks`, read in binary, or those exact bytes mutated
by one line so the mutation itself is visible. A test written against a header string typed in
this file would only prove that the code does what the code does. The corpus is what says what
the FILES do, and the difference between the two is the whole project.

The measurements of `ofxparse` 0.21 are loaded from `corpus/measurements/2026-08-05.json` and
asserted alongside our own result: a test that says "we read nine headers" is worth much less
than one that says "we read nine where the reference parser read zero, on the same bytes".
"""

from __future__ import annotations

import codecs
import json
from pathlib import Path
from typing import Any

import pytest

from bankfile.ofx.header import Header, read_header

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
BANKS = CORPUS / "banks"
MEASURED: dict[str, Any] = json.loads(
    (CORPUS / "measurements" / "2026-08-05.json").read_text(encoding="utf-8")
)

# The nine headers OFX 1.x defines. Every 1.x fixture in the corpus carries exactly these.
NINE_HEADERS = {
    "OFXHEADER",
    "DATA",
    "VERSION",
    "SECURITY",
    "ENCODING",
    "CHARSET",
    "COMPRESSION",
    "OLDFILEUID",
    "NEWFILEUID",
}

FIXTURES = sorted(
    path.relative_to(BANKS).as_posix() for path in [*BANKS.glob("*/*.ofx"), *BANKS.glob("*/*.qfx")]
)

# A blank line where the format does not expect one, in two different banks.
BLANK_LINE_FIXTURES = [
    "chase/blank-line-before-header-none-after.qfx",
    "unnamed-bank/blank-line-before-header.ofx",
]


def raw(fixture: str) -> bytes:
    return (BANKS / fixture).read_bytes()


def read(fixture: str) -> Header:
    return read_header(raw(fixture))


@pytest.mark.parametrize("fixture", BLANK_LINE_FIXTURES)
def test_a_blank_line_costs_nine_headers_to_ofxparse_and_none_to_us(fixture: str) -> None:
    """THE reason this repository exists, made explicit.

    On these two files `ofxparse` 0.21 returns zero headers instead of nine, in both call
    modes, without raising and without a warning: `ENCODING`, `CHARSET` and `VERSION` are gone
    and nothing says so. On an ASCII fixture that costs nothing visible, which is exactly what
    makes it dangerous, since the same loss on a file carrying an accented payee fails much
    later, far from the blank line that caused it.
    """
    for mode in ("ofxparse_0_21_text_mode", "ofxparse_0_21_binary_mode"):
        assert MEASURED[fixture][mode]["ok"] is True, "the measured run did not even parse"
        assert MEASURED[fixture][mode]["headers_read"] == 0, "the measurement moved, re-measure"

    header = read(fixture)

    assert set(header.values) == NINE_HEADERS
    assert header.values["CHARSET"] == "1252"
    assert header.values["ENCODING"] == "USASCII"
    assert header.encoding == "cp1252"
    assert header.body.startswith("<OFX>")
    assert [w for w in header.warnings if w.rule == "header"] == []


def test_the_nine_headers_collapsed_onto_one_line_are_recut_on_the_known_keys() -> None:
    """Wells Fargo writes the whole block on one physical line, and `ofxparse` unpacks it into
    two values and raises. The pairs are only recoverable by knowing the key names."""
    assert MEASURED["wells-fargo/header-on-one-line.qfx"]["ofxparse_0_21_binary_mode"] == {
        "ok": False,
        "error": "ValueError: too many values to unpack (expected 2)",
    }

    header = read("wells-fargo/header-on-one-line.qfx")

    assert header.values == {
        "OFXHEADER": "100",
        "DATA": "OFXSGML",
        "VERSION": "102",
        "SECURITY": "NONE",
        "ENCODING": "USASCII",
        "CHARSET": "1252",
        "COMPRESSION": "NONE",
        "OLDFILEUID": "NONE",
        "NEWFILEUID": "NONE",
    }
    assert header.encoding == "cp1252"
    assert header.is_xml is False
    assert header.body.startswith("<OFX>")
    assert header.warnings == []


def test_a_cp1252_byte_in_a_file_declaring_usascii_is_decoded_and_reported() -> None:
    """`ENCODING:USASCII` is a statement about byte width, not a codec name: `CHARSET:1252` is
    what names the code page, and it decodes the byte exactly. The declaration is still a lie,
    so it is reported instead of being silently overruled."""
    header = read("chase/non-ascii-byte-declared-usascii.qfx")

    assert header.encoding == "cp1252"
    assert "ANON \xa6 MERCHANT" in header.body
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.field == "ENCODING"
    assert warning.value == "USASCII"
    assert "0xA6" in warning.message


def test_charset_none_is_a_legal_value_and_decodes_as_cp1252() -> None:
    """`ofxparse` builds the codec name `cpNONE` by concatenation and dies on the lookup. NONE
    is one of the three values OFX 1.x allows, so the file is right and the parser is wrong."""
    failure = MEASURED["etrade/charset-none-with-encoding-usascii.ofx"]["ofxparse_0_21_binary_mode"]
    assert failure["error"] == "LookupError: unknown encoding: cpNONE"

    header = read("etrade/charset-none-with-encoding-usascii.ofx")

    assert header.values["CHARSET"] == "NONE"
    assert header.encoding == "cp1252"
    assert header.warnings == []


def test_charset_8859_1_without_the_iso_prefix_is_iso_8859_1() -> None:
    header = read("unnamed-bank/charset-8859-1-without-iso-prefix.qfx")

    assert header.values["CHARSET"] == "8859-1"
    assert header.encoding == "iso-8859-1"
    assert header.warnings == []


def test_encoding_utf8_decides_whatever_charset_says() -> None:
    """The payee carries U+010D, outside latin-1. `CHARSET:NONE` would send us to cp1252 and
    lose it; `ENCODING:UTF-8` wins, which is step 2 of the encoding rule."""
    header = read("unnamed-bank/character-outside-latin1.ofx")

    assert header.values["ENCODING"] == "UTF-8"
    assert header.values["CHARSET"] == "NONE"
    assert header.encoding == "utf-8"
    assert "ANON UPRAVA č" in header.body
    assert header.warnings == []


def test_ofx_2_takes_its_encoding_from_the_xml_declaration() -> None:
    """There is no `key:value` block in an OFX 2.x file, and its absence is normal: it must not
    trigger the untrusted-header path. The `<?OFX ...?>` attributes land in `values` so a caller
    reads `OFXHEADER` and `VERSION` the same way as in 1.x."""
    header = read("unnamed-bank/xml-declaration-ofx-2.ofx")

    assert header.is_xml is True
    assert header.encoding == "utf-8"
    assert header.values == {
        "OFXHEADER": "200",
        "VERSION": "202",
        "SECURITY": "NONE",
        "OLDFILEUID": "NONE",
        "NEWFILEUID": "NONE",
    }
    assert header.body.startswith("<OFX>")
    assert "ANON \xc9NERGIE" in header.body
    assert header.warnings == []


@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_corpus_fixture_yields_a_body_and_a_codec(fixture: str) -> None:
    """Eighteen files, no exception, a body that starts at the document and a named codec."""
    header = read(fixture)

    assert header.encoding
    assert header.body.startswith("<OFX>")
    assert header.body.rstrip().endswith("</OFX>")


def test_crlf_line_endings_do_not_hide_the_headers() -> None:
    """Real exports travel with Windows line endings, and the corpus files do not."""
    header = read_header(raw(BLANK_LINE_FIXTURES[0]).replace(b"\n", b"\r\n"))

    assert set(header.values) == NINE_HEADERS
    assert header.body.startswith("<OFX>")


def test_an_unknown_key_inside_a_collapsed_header_costs_that_pair_and_not_the_block() -> None:
    """The case the upstream fix cannot handle: with the newlines gone, `VENDORTAG` is swallowed
    into the value of `DATA` and no cut recovers that pair. The Wells Fargo note asks for the
    suspect VALUE to be dropped, not the line: the eight pairs cut cleanly around it are intact,
    and `DATA` alone falls back to the format default. Never raise, keep the body."""
    collapsed = raw("wells-fargo/header-on-one-line.qfx")
    header = read_header(collapsed.replace(b"VERSION:102", b"VENDORTAG:X VERSION:102"))

    assert header.values == {
        "OFXHEADER": "100",
        "VERSION": "102",
        "SECURITY": "NONE",
        "ENCODING": "USASCII",
        "CHARSET": "1252",
        "COMPRESSION": "NONE",
        "OLDFILEUID": "NONE",
        "NEWFILEUID": "NONE",
        "DATA": "OFXSGML",
    }
    assert [w.rule for w in header.warnings] == ["header", "header"]
    assert "VENDORTAG" in (header.warnings[0].value or "")
    assert "DATA" in header.warnings[1].message
    assert header.encoding == "cp1252"
    assert header.body.startswith("<OFX>")


def test_a_broken_fragment_does_not_cost_the_declared_encoding_of_the_ones_beside_it() -> None:
    """The same collapsed line, this time declaring `ENCODING:UTF-8` and carrying an accented
    payee. Dropping the whole line over its one unreadable fragment also drops the `ENCODING`
    that was cut cleanly beside it, the file falls back to cp1252, and `ANON ENERGIE` comes back
    as `ANON Ã‰NERGIE` with no warning at all. That is the wrong but plausible value section 0
    of the reading rules exists to forbid, so it is pinned here.
    """
    mutated = (
        raw("wells-fargo/header-on-one-line.qfx")
        .replace(b"ENCODING:USASCII", b"ENCODING:UTF-8")
        .replace(b"VERSION:102", b"VENDORTAG:X VERSION:102")
        .replace(b"ANON MERCHANT", "ANON \xc9NERGIE".encode())
    )

    header = read_header(mutated)

    assert header.values["ENCODING"] == "UTF-8"
    assert header.encoding == "utf-8"
    assert "ANON \xc9NERGIE" in header.body


def test_a_colon_inside_a_header_value_belongs_to_the_value() -> None:
    """A line carrying one key and three colons is not a collapsed block. The re-cut fires on the
    known key names, which is what tells the Wells Fargo line apart from a value that simply
    contains a colon, so nothing here is dropped and nothing is untrusted."""
    header = read_header(
        raw("etrade/charset-none-with-encoding-usascii.ofx").replace(
            b"NEWFILEUID:NONE", b"NEWFILEUID:20260115T10:00:00"
        )
    )

    assert header.values["NEWFILEUID"] == "20260115T10:00:00"
    assert set(header.values) == NINE_HEADERS
    assert header.warnings == []


def test_the_same_header_declared_twice_does_not_change_the_codec_in_silence() -> None:
    """The last declaration wins, as everywhere else in this reader. What is forbidden is the
    silence: on CHARSET the value that just disappeared is the codec of the whole file."""
    header = read_header(
        raw("etrade/charset-none-with-encoding-usascii.ofx").replace(
            b"CHARSET:NONE", b"CHARSET:NONE\nCHARSET:8859-1"
        )
    )

    assert header.values["CHARSET"] == "8859-1"
    assert header.encoding == "iso-8859-1"
    (warning,) = header.warnings
    assert warning.rule == "header"
    assert warning.field == "CHARSET"
    assert warning.value == "NONE"


def test_a_charset_outside_the_table_falls_back_to_cp1252_with_a_warning() -> None:
    """The value is reported as an unknown header value, not as a codec error: a `LookupError`
    naming `cpNONE` points at the parser, a warning naming CHARSET points at the file."""
    header = read_header(
        raw("etrade/charset-none-with-encoding-usascii.ofx").replace(
            b"CHARSET:NONE", b"CHARSET:UTF-16"
        )
    )

    assert header.values["CHARSET"] == "UTF-16"
    assert header.encoding == "cp1252"
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.field == "CHARSET"
    assert warning.value == "UTF-16"


def test_a_declared_codec_that_cannot_decode_the_bytes_falls_back_and_says_so() -> None:
    """The real Chase bytes, relabelled `ENCODING:UTF-8`: 0xA6 is not valid utf-8, so the
    declared codec fails and cp1252 takes over. The payee survives intact."""
    header = read_header(
        raw("chase/non-ascii-byte-declared-usascii.qfx").replace(
            b"ENCODING:USASCII", b"ENCODING:UTF-8"
        )
    )

    assert header.encoding == "cp1252"
    assert "ANON \xa6 MERCHANT" in header.body
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.value == "utf-8"


def test_when_cp1252_also_fails_the_last_resort_is_iso_8859_1() -> None:
    """0x81 is undefined in cp1252 and valid in iso-8859-1, which maps all 256 byte values.
    Never `errors='ignore'`: that returns a payee that reads as correct."""
    header = read_header(
        raw("chase/non-ascii-byte-declared-usascii.qfx")
        .replace(b"ENCODING:USASCII", b"ENCODING:UTF-8")
        .replace(b"\xa6", b"\x81")
    )

    assert header.encoding == "iso-8859-1"
    assert "ANON \x81 MERCHANT" in header.body
    assert [w.value for w in header.warnings] == ["utf-8", "cp1252"]


def test_a_utf8_byte_order_mark_does_not_swallow_the_first_header() -> None:
    header = read_header(codecs.BOM_UTF8 + raw("etrade/charset-none-with-encoding-usascii.ofx"))

    assert header.values["OFXHEADER"] == "100"
    assert header.encoding == "cp1252"


def test_an_unknown_encoding_in_the_xml_declaration_warns_and_reads_as_utf_8() -> None:
    header = read_header(
        raw("unnamed-bank/xml-declaration-ofx-2.ofx").replace(
            b'encoding="UTF-8"', b'encoding="NOSUCHCODEC"'
        )
    )

    assert header.encoding == "utf-8"
    assert header.body.startswith("<OFX>")
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.value == "NOSUCHCODEC"


def test_an_xml_declaration_naming_a_codec_that_is_not_text_is_reported_instead_of_raising() -> (
    None
):
    """`codecs.lookup` accepts base64, hex and rot13, and `bytes.decode` raises LookupError on
    them, which is not a `UnicodeDecodeError` and would leave this module the only one able to
    end a read on a traceback. The declaration is unusable, so the XML default applies."""
    header = read_header(
        raw("unnamed-bank/xml-declaration-ofx-2.ofx").replace(
            b'encoding="UTF-8"', b'encoding="base64"'
        )
    )

    assert header.encoding == "utf-8"
    assert "ANON \xc9NERGIE" in header.body
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.value == "base64"


def test_a_text_codec_that_cannot_read_one_byte_is_still_a_text_codec() -> None:
    """utf-16 fails on a lone byte exactly as base64 does, and the two must not share a fate:
    one is a codec the file may legitimately declare, the other is not a text codec at all. Here
    the declaration lies about utf-8 bytes, so the codec is kept, it fails on the DATA, and the
    fallback chain of section 1 step 4 takes over and says so."""
    header = read_header(
        raw("unnamed-bank/xml-declaration-ofx-2.ofx").replace(
            b'encoding="UTF-8"', b'encoding="utf-16"'
        )
    )

    assert header.encoding == "cp1252"
    assert header.body.startswith("<OFX>")
    (warning,) = header.warnings
    assert warning.rule == "encoding"
    assert warning.value == "utf-16"


def test_an_xml_declaration_without_an_encoding_reads_as_utf_8() -> None:
    """What the XML specification itself requires when the declaration omits the encoding."""
    header = read_header(
        raw("unnamed-bank/xml-declaration-ofx-2.ofx").replace(b' encoding="UTF-8"', b"")
    )

    assert header.is_xml is True
    assert header.encoding == "utf-8"
    assert header.warnings == []


def test_an_ofx_2_file_truncated_after_its_prologue_is_reported_instead_of_raising() -> None:
    """A download cut short still declares its version and its codec, and those are worth
    keeping: what is missing is the body, and that is what the warning says."""
    header = read_header(raw("unnamed-bank/xml-declaration-ofx-2.ofx").split(b"<OFX>")[0])

    assert header.is_xml is True
    assert header.values["VERSION"] == "202"
    assert header.body == ""
    assert [w.rule for w in header.warnings] == ["header"]


def test_a_file_with_no_tag_at_all_is_reported_instead_of_raising() -> None:
    header = read_header(b"OFXHEADER:100\nDATA:OFXSGML\n")

    assert header.body == ""
    assert header.values["OFXHEADER"] == "100"
    assert [w.rule for w in header.warnings] == ["header"]


def test_an_empty_file_is_reported_instead_of_raising() -> None:
    header = read_header(b"")

    assert header.body == ""
    assert header.values == {"VERSION": "102", "DATA": "OFXSGML", "CHARSET": "1252"}
    assert [w.rule for w in header.warnings] == ["header", "header"]


def test_a_line_without_a_colon_ends_the_header_block() -> None:
    """Section 2: the block ends at the first `<` or at the first line without a `:`. What
    follows is not a header, and guessing at it is how a body line becomes a codec name."""
    header = read_header(
        raw("etrade/charset-none-with-encoding-usascii.ofx").replace(
            b"NEWFILEUID:NONE\n", b"NEWFILEUID:NONE\nnot a header line\n"
        )
    )

    assert set(header.values) == NINE_HEADERS
    assert [w.rule for w in header.warnings] == ["header", "header"]
    assert header.warnings[0].value == "not a header line"
    assert header.body.startswith("<OFX>")


def test_the_header_is_immutable() -> None:
    header = read("etrade/charset-none-with-encoding-usascii.ofx")

    with pytest.raises(AttributeError):
        header.encoding = "utf-8"  # type: ignore[misc]
