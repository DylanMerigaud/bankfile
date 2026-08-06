"""One statement must never be handed another statement's money.

OFX 1.x lets an aggregate omit its end tag. A file carrying two statements without `</STMTRS>`
therefore nests the second inside the first, and a reader that searches descendants returns the
second account's entries under the first account's number, stamped with the first account's
currency.

That is a wrong amount, under a wrong account, in a wrong currency, all at once, and it is
exactly the failure this library exists to prevent. It shipped, an audit found it, and these
tests are what stop it coming back.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankfile.ofx.reader import read_ofx
from bankfile.ofx.sgml import parse_tags

HEADER = (
    "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\n"
    "CHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n<OFX>\n<BANKMSGSRSV1>\n"
)


def statement(currency: str, account: str, amount: str, fitid: str, *, closed: bool) -> str:
    body = (
        f"<STMTTRNRS>\n<TRNUID>1\n<STMTRS>\n<CURDEF>{currency}\n<BANKACCTFROM>\n"
        f"<ACCTID>{account}\n<ACCTTYPE>CHECKING\n</BANKACCTFROM>\n<BANKTRANLIST>\n<STMTTRN>\n"
        f"<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n<TRNAMT>{amount}\n<FITID>{fitid}\n</STMTTRN>\n"
        f"</BANKTRANLIST>\n<LEDGERBAL>\n<BALAMT>{amount}\n<DTASOF>20260131\n</LEDGERBAL>\n"
    )
    return body + ("</STMTRS>\n</STMTTRNRS>\n" if closed else "")


def two_statements(*, closed: bool) -> bytes:
    return (
        HEADER
        + statement("EUR", "1111", "-10.00", "A", closed=closed)
        + statement("USD", "2222", "-99.00", "B", closed=closed)
        + "</BANKMSGSRSV1>\n</OFX>\n"
    ).encode()


@pytest.mark.parametrize("closed", [True, False], ids=["end tags present", "end tags omitted"])
def test_a_second_statement_never_lends_its_entries_to_the_first(closed: bool) -> None:
    read = read_ofx(two_statements(closed=closed))
    assert read.account == "1111"
    assert read.currency == "EUR"
    assert [t.amount for t in read.transactions] == [Decimal("-10.00")]
    assert [t.bank_reference for t in read.transactions] == ["A"]


@pytest.mark.parametrize("closed", [True, False], ids=["end tags present", "end tags omitted"])
def test_the_second_statement_is_reported_and_not_silently_dropped(closed: bool) -> None:
    """Returning one statement out of two is only acceptable because we say so. Silence here
    would let a caller reconcile a third of an account and believe it was whole."""
    read = read_ofx(two_statements(closed=closed))
    assert [w.field for w in read.warnings if w.field == "STMTRS"] == ["STMTRS"]


@pytest.mark.parametrize("closed", [True, False], ids=["end tags present", "end tags omitted"])
def test_the_balance_belongs_to_the_statement_it_was_read_from(closed: bool) -> None:
    assert read_ofx(two_statements(closed=closed)).closing_balance == Decimal("-10.00")


def test_a_transaction_nested_in_a_transaction_does_not_lend_its_amount() -> None:
    """The same defect one level down: fields of a transaction are read from its DIRECT
    children, never from a descendant that belongs to something else."""
    nested = (
        HEADER + "<STMTTRNRS>\n<STMTRS>\n<CURDEF>EUR\n<BANKACCTFROM>\n<ACCTID>1111\n"
        "</BANKACCTFROM>\n<BANKTRANLIST>\n<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n"
        "<TRNAMT>-10.00\n<FITID>OUTER\n<STMTTRN>\n<TRNAMT>-77.00\n<FITID>INNER\n</STMTTRN>\n"
        "</STMTTRN>\n</BANKTRANLIST>\n</STMTRS>\n</STMTTRNRS>\n</BANKMSGSRSV1>\n</OFX>\n"
    ).encode()
    amounts = [t.amount for t in read_ofx(nested).transactions]
    assert Decimal("-10.00") in amounts
    assert amounts.count(Decimal("-10.00")) == 1, "the outer entry must not be counted twice"


def test_the_tree_walk_can_be_told_not_to_enter_a_tag() -> None:
    """The primitive the fix rests on, tested on its own so a refactor cannot quietly drop it."""
    root, _ = parse_tags("<A><X>1</X><B><X>2</X></B></A>")
    assert [n.value for n in root.find_all("X")] == ["1", "2"]
    assert [n.value for n in root.find_all("X", stop_at=frozenset({"B"}))] == ["1"]
