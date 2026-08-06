#!/usr/bin/env python3
"""Build every OFX fixture in the corpus from ONE shared template.

Why a generator instead of eighteen hand-written files: a corpus fixture is only worth
something if its diff against the template IS the deviation, and nothing else. Written by
hand, fixtures drift (a space here, a date there) and the diff stops saying anything. An
audit of the first hand-assembled pass found four fixtures that no longer differed from the
template by their deviation alone, and two that did not even exercise the deviation they were
named after.

Each entry carries its sources and the lines actually quoted in the upstream issue. That is
what separates a corpus you can check from a corpus that merely sounds plausible.

    python3 scripts/build_fixtures.py            # write the fixtures
    python3 scripts/build_fixtures.py --check    # fail if the files on disk have drifted
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANKS = ROOT / "corpus" / "banks"
TEMPLATE = (ROOT / "corpus" / "template" / "ofx-1.0.2.ofx").read_text(encoding="utf-8")

HEADER = [
    "OFXHEADER:100",
    "DATA:OFXSGML",
    "VERSION:102",
    "SECURITY:NONE",
    "ENCODING:USASCII",
    "CHARSET:1252",
    "COMPRESSION:NONE",
    "OLDFILEUID:NONE",
    "NEWFILEUID:NONE",
]


def sub(text: str, before: str, after: str) -> str:
    if before not in text:
        msg = f"template has no {before!r}, the edit would bite on nothing"
        raise SystemExit(msg)
    return text.replace(before, after, 1)


# --- one function per deviation -------------------------------------------------------------


def header_on_one_line(t: str) -> str:
    return sub(t, "\n".join(HEADER), "".join(HEADER))


def blank_line_before_header_none_after(t: str) -> str:
    return "\n" + sub(t, "NEWFILEUID:NONE\n\n<OFX>", "NEWFILEUID:NONE\n<OFX>")


def non_ascii_byte_declared_usascii(t: str) -> str:
    # The header stays exactly as the template has it, USASCII plus CHARSET 1252. Only the
    # payee carries byte 0xa6, which the file declares it cannot contain.
    return sub(t, "<NAME>ANON MERCHANT", "<NAME>ANON ¦ MERCHANT")


def charset_none(t: str) -> str:
    return sub(t, "CHARSET:1252", "CHARSET:NONE")


def charset_8859_1(t: str) -> str:
    return sub(t, "CHARSET:1252", "CHARSET:8859-1")


def dtstart_ddmmyy(t: str) -> str:
    return sub(t, "<DTSTART>20260101", "<DTSTART>010126")


def check_without_payee(t: str) -> str:
    t = sub(t, "<TRNTYPE>DEBIT", "<TRNTYPE>CHECK")
    return sub(
        t,
        "<FITID>T0001\n<NAME>ANON MERCHANT\n<MEMO>ANON MEMO\n",
        "<FITID>T0001\n<CHECKNUM>1090381\n",
    )


def self_closing_memo_tag(t: str) -> str:
    return sub(t, "<MEMO>ANON MEMO", "<MEMO/>")


def character_outside_latin1(t: str) -> str:
    # Faithful to the reported file, which carries both properties at once. Splitting them
    # would invent a header combination no source attests.
    t = sub(t, "ENCODING:USASCII", "ENCODING:UTF-8")
    t = sub(t, "CHARSET:1252", "CHARSET:NONE")
    return sub(t, "<NAME>ANON MERCHANT", "<NAME>ANON UPRAVA č")


def blank_line_before_header(t: str) -> str:
    return "\n" + t


def amount_comma_decimal(t: str) -> str:
    t = sub(t, "<TRNAMT>-10.00", "<TRNAMT>-2000,00")
    return sub(
        t,
        "<BALAMT>90.00\n<DTASOF>20260131\n</LEDGERBAL>",
        "<BALAMT>2000,00\n<DTASOF>20260131\n</LEDGERBAL>",
    )


def amount_plus_sign_and_space(t: str) -> str:
    return sub(t, "<TRNAMT>-10.00", "<TRNAMT>+1 006,60")


def zero_date(t: str) -> str:
    return sub(
        t,
        "<BALAMT>90.00\n<DTASOF>20260131\n</LEDGERBAL>",
        "<BALAMT>90.00\n<DTASOF>00000000\n</LEDGERBAL>",
    )


def chknum_instead_of_checknum(t: str) -> str:
    return sub(t, "<FITID>T0001", "<FITID>T0001\n<CHKNUM>1932")


def empty_tags(t: str) -> str:
    t = sub(t, "<CURDEF>USD", "<CURDEF></CURDEF>")
    t = sub(t, "<FITID>T0001", "<FITID></FITID>")
    return sub(t, "<NAME>ANON MERCHANT", "<NAME></NAME>")


def mixed_case_trntype(t: str) -> str:
    return sub(t, "<TRNTYPE>DEBIT", "<TRNTYPE>Credit</TRNTYPE>")


def tags_outside_spec(t: str) -> str:
    # The unknown tags sit BETWEEN standard fields, as they do in the quoted excerpt, so the
    # fixture can prove a reader does not shift the fields that follow them.
    t = sub(t, "<FITID>T0001\n", "<FITID>T0001\n<VALUEDATE>20260115\n")
    return sub(
        t,
        "<NAME>ANON MERCHANT\n",
        "<NAME>ANON MERCHANT\n<TRANSACTIONSPLIT>No\n<CATEGORY>Uncategorised\n<ACCTBAL>-400.52\n",
    )


OFX_2X = """<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
      <DTSERVER>20260115</DTSERVER>
      <LANGUAGE>ENG</LANGUAGE>
      <FI><ORG>ANONBANK</ORG><FID>0001</FID></FI>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <TRNUID>1</TRNUID>
      <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
      <STMTRS>
        <CURDEF>USD</CURDEF>
        <BANKACCTFROM>
          <BANKID>000000001</BANKID>
          <ACCTID>0000123456</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
          <DTSTART>20260101</DTSTART>
          <DTEND>20260131</DTEND>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20260115</DTPOSTED>
            <TRNAMT>-10.00</TRNAMT>
            <FITID>T0001</FITID>
            <NAME>ANON ÉNERGIE</NAME>
            <MEMO>ANON MEMO</MEMO>
          </STMTTRN>
        </BANKTRANLIST>
        <LEDGERBAL>
          <BALAMT>90.00</BALAMT>
          <DTASOF>20260131</DTASOF>
        </LEDGERBAL>
        <AVAILBAL>
          <BALAMT>90.00</BALAMT>
          <DTASOF>20260131</DTASOF>
        </AVAILBAL>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
"""

CASES = [
    {
        "bank": "Wells Fargo",
        "dir": "wells-fargo",
        "case": "header-on-one-line",
        "ext": "qfx",
        "encoding": "utf-8",
        "sources": [172],
        "build": header_on_one_line,
        "quoted": [
            "OFXHEADER:100DATA:OFXSGMLVERSION:102SECURITY:NONEENCODING:USASCII"
            "CHARSET:1252COMPRESSION:NONEOLDFILEUID:NONENEWFILEUID:NONE"
        ],
    },
    {
        "bank": "Chase",
        "dir": "chase",
        "case": "blank-line-before-header-none-after",
        "ext": "qfx",
        "encoding": "utf-8",
        "sources": [160],
        "build": blank_line_before_header_none_after,
        "quoted": ["(blank line)\nOFXHEADER:100\n...\nNEWFILEUID:NONE\n<OFX>"],
    },
    {
        "bank": "Chase",
        "dir": "chase",
        "case": "non-ascii-byte-declared-usascii",
        "ext": "qfx",
        "encoding": "cp1252",
        "sources": [160, 179],
        "build": non_ascii_byte_declared_usascii,
        "quoted": [
            "SQ *ECCO UN POCO ¦ NATURA",
            "<MEMO>TRANSFERENCIA PIX DES: Laboratório Hacker De 18/10",
        ],
    },
    {
        "bank": "E*Trade",
        "dir": "etrade",
        "case": "charset-none-with-encoding-usascii",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [171, 154, 163],
        "build": charset_none,
        "quoted": ["ENCODING:USASCII\nCHARSET:NONE"],
    },
    {
        "bank": "HSBC Brasil",
        "dir": "hsbc-brasil",
        "case": "dtstart-ddmmyy",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [58],
        "build": dtstart_ddmmyy,
        "quoted": ["BANKTRANLIST :: DTSTART tag is in %d%m%y format"],
    },
    {
        "bank": "LCL",
        "dir": "lcl",
        "case": "check-without-payee",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [162],
        "build": check_without_payee,
        "quoted": ["<TRNTYPE>CHECK\n<DTPOSTED>20190221\n<TRNAMT>-19.87"],
    },
    {
        "bank": "OnPoint Community Credit Union",
        "dir": "onpoint-community-credit-union",
        "case": "self-closing-memo-tag",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [167, 81],
        "build": self_closing_memo_tag,
        "quoted": ["tokens that look like <MEMO/>", "<FI><ORG/><FID/></FI>"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "charset-8859-1-without-iso-prefix",
        "ext": "qfx",
        "encoding": "utf-8",
        "sources": [148],
        "build": charset_8859_1,
        "quoted": ["ENCODING:USASCII\nCHARSET:8859-1"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "character-outside-latin1",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [169],
        "build": character_outside_latin1,
        "quoted": ["ENCODING:UTF-8\nCHARSET:NONE", "<NAME>Finančna uprava RS</NAME>"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "xml-declaration-ofx-2",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [133],
        "build": None,
        "content": OFX_2X,
        "quoted": [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" '
            'OLDFILEUID="NONE" NEWFILEUID="NONE"?>',
        ],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "blank-line-before-header",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [161, 179],
        "build": blank_line_before_header,
        "quoted": ["My bank OFX files start with empty lines", "(blank line at start of file)"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "amount-comma-decimal",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [179],
        "build": amount_comma_decimal,
        "quoted": ["<TRNAMT>2000,00", "<BALAMT>2000,00"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "amount-plus-sign-and-space",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [173],
        "build": amount_plus_sign_and_space,
        "quoted": ["<TRNAMT>+1 006,60", "<TRNAMT>+1,006.60"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "zero-date",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [179],
        "build": zero_date,
        "quoted": ["<DTASOF>00000000"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "chknum-instead-of-checknum",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [173],
        "build": chknum_instead_of_checknum,
        "quoted": ["<CHKNUM>1932"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "empty-tags-curdef-fitid-name",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [81],
        "build": empty_tags,
        "quoted": [
            "<FITID></FITID>",
            "<NAME></NAME>",
            "account.curdef = act_curdef.contents[0].strip()\nIndexError: list index out of range",
        ],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "mixed-case-trntype",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [81],
        "build": mixed_case_trntype,
        "quoted": ["<TRNTYPE>Credit</TRNTYPE>"],
    },
    {
        "bank": "unnamed",
        "dir": "unnamed-bank",
        "case": "tags-outside-spec",
        "ext": "ofx",
        "encoding": "utf-8",
        "sources": [81],
        "build": tags_outside_spec,
        "quoted": [
            "<VALUEDATE>20180801</VALUEDATE>",
            "<TRANSACTIONSPLIT>No</TRANSACTIONSPLIT>",
            "<CATEGORY>Uncategorised</CATEGOR",
            "<ACCTBAL>-400.52</ACCTBAL>",
        ],
    },
]


def render(case: dict) -> bytes:
    content = case["content"] if case["build"] is None else case["build"](TEMPLATE)
    return content.encode(case["encoding"])


def main() -> int:
    check = "--check" in sys.argv
    drifted: list[str] = []
    manifest = []
    for case in CASES:
        path = BANKS / case["dir"] / f"{case['case']}.{case['ext']}"
        wanted = render(case)
        if check:
            if not path.exists() or path.read_bytes() != wanted:
                drifted.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(wanted)
        manifest.append(
            {
                "fixture": str(path.relative_to(ROOT)),
                "bank": case["bank"],
                "case": case["case"],
                "encoding": case["encoding"],
                "sources": case["sources"],
                "quoted": case["quoted"],
            }
        )
    if check:
        for d in drifted:
            print(f"  drifted from the template: {d}")
        print(f"{len(CASES)} fixtures, {len(drifted)} drifted")
        return 1 if drifted else 0
    (BANKS.parent / "fixtures.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(CASES)} fixtures written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
