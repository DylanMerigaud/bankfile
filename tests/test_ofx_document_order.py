"""The statement we return is the first one the FILE writes, not the first one we look for.

A file can carry a bank account and a credit card at once, `STMTRS` and `CCSTMTRS` side by side.
The reader returns one statement and warns that it is the first, so "first" has to mean first in
document order. Reading every `STMTRS` before every `CCSTMTRS` made it mean "first of the tag we
happened to list first", which is a promise decided by our own tuple instead of by the bytes.

The cost of getting this wrong is not cosmetic: a caller told they hold the first statement of
the file reconciles a credit card against a current account's figures, and every number is
plausible.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankfile.ofx.reader import read_ofx

HEADER = (
    "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\n"
    "CHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n<OFX>\n"
)

CARD = (
    "<CREDITCARDMSGSRSV1>\n<CCSTMTTRNRS>\n<TRNUID>1\n<CCSTMTRS>\n<CURDEF>USD\n"
    "<CCACCTFROM>\n<ACCTID>4444333322221111\n</CCACCTFROM>\n<BANKTRANLIST>\n<STMTTRN>\n"
    "<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n<TRNAMT>-25.00\n<FITID>CARD\n</STMTTRN>\n"
    "</BANKTRANLIST>\n<LEDGERBAL>\n<BALAMT>-25.00\n<DTASOF>20260131\n</LEDGERBAL>\n"
    "</CCSTMTRS>\n</CCSTMTTRNRS>\n</CREDITCARDMSGSRSV1>\n"
)

BANK = (
    "<BANKMSGSRSV1>\n<STMTTRNRS>\n<TRNUID>2\n<STMTRS>\n<CURDEF>EUR\n<BANKACCTFROM>\n"
    "<ACCTID>0000123456\n<ACCTTYPE>CHECKING\n</BANKACCTFROM>\n<BANKTRANLIST>\n<STMTTRN>\n"
    "<TRNTYPE>DEBIT\n<DTPOSTED>20260116\n<TRNAMT>-10.00\n<FITID>BANK\n</STMTTRN>\n"
    "</BANKTRANLIST>\n<LEDGERBAL>\n<BALAMT>-10.00\n<DTASOF>20260131\n</LEDGERBAL>\n"
    "</STMTRS>\n</STMTTRNRS>\n</BANKMSGSRSV1>\n"
)


def document(*sections: str) -> bytes:
    return (HEADER + "".join(sections) + "</OFX>\n").encode()


def test_the_card_statement_is_returned_when_the_file_writes_it_first() -> None:
    """The case the tag order got wrong. Every field below belongs to the card statement, and
    before the fix every one of them came back from the current account further down the file."""
    read = read_ofx(document(CARD, BANK))
    assert read.account == "4444333322221111"
    assert read.currency == "USD"
    assert read.closing_balance == Decimal("-25.00")
    assert [t.bank_reference for t in read.transactions] == ["CARD"]
    assert [t.amount for t in read.transactions] == [Decimal("-25.00")]


def test_the_bank_statement_is_returned_when_the_file_writes_it_first() -> None:
    """The other order, which already worked. It is here so that a fix aimed at the case above
    cannot pass by simply preferring credit cards instead."""
    read = read_ofx(document(BANK, CARD))
    assert read.account == "0000123456"
    assert read.currency == "EUR"
    assert read.closing_balance == Decimal("-10.00")
    assert [t.bank_reference for t in read.transactions] == ["BANK"]


@pytest.mark.parametrize("sections", [(CARD, BANK), (BANK, CARD)], ids=["card first", "bank first"])
def test_the_statement_left_behind_is_reported_whichever_one_it_is(
    sections: tuple[str, ...],
) -> None:
    """Returning one statement out of two is only acceptable because we say so, and what we say
    has to hold for a mixed file too: two present, one returned."""
    read = read_ofx(document(*sections))
    reported = [w for w in read.warnings if w.field == "STMTRS"]
    assert [w.value for w in reported] == ["2"]
    assert "only the first is returned" in reported[0].message


def test_a_card_only_file_reads_without_needing_a_bank_statement() -> None:
    """A credit card export carries no `STMTRS` at all, and it is a statement like any other."""
    read = read_ofx(document(CARD))
    assert read.account == "4444333322221111"
    assert [w for w in read.warnings if w.field == "STMTRS"] == []


def test_a_document_with_no_statement_at_all_says_so_instead_of_answering_zero() -> None:
    """An OFX file can be a valid response carrying no statement: a sign-on, an error status, a
    profile. Returning an empty statement in silence would be worse than any error, because an
    empty statement reconciles to zero and reads like a real answer."""
    read = read_ofx(document("<SIGNONMSGSRSV1>\n<SONRS>\n<DTSERVER>20260115\n</SONRS>\n"))
    assert read.transactions == []
    assert read.account is None
    assert read.closing_balance is None
    assert any("carries no statement to read" in w.message for w in read.warnings)
