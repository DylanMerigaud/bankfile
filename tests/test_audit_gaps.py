"""The behaviours an audit found undefended, each pinned by a test that fails without it.

A hand mutation pass over this project caught 45 of 54 broken behaviours. The nine that
survived are the ones below, and they are not a random nine: they are the branches that decide
whether a wrong figure reaches the caller. High coverage said they were exercised; nothing said
they were checked.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from bankfile.mcp.server import build_server
from bankfile.model import Transaction
from bankfile.mt940_adapter import read_mt940
from bankfile.ofx.reader import read_ofx
from bankfile.report import check_reconciliation

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "corpus" / "banks"

HEADER = (
    "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\n"
    "CHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n<OFX>\n"
    "<BANKMSGSRSV1>\n<STMTTRNRS>\n<STMTRS>\n<CURDEF>EUR\n<BANKACCTFROM>\n<ACCTID>1111\n"
    "</BANKACCTFROM>\n<BANKTRANLIST>\n"
)
FOOTER = "</BANKTRANLIST>\n</STMTRS>\n</STMTTRNRS>\n</BANKMSGSRSV1>\n</OFX>\n"


def ofx(*transactions: str) -> bytes:
    return (HEADER + "".join(transactions) + FOOTER).encode()


def test_a_transaction_with_no_amount_never_reaches_the_output() -> None:
    """The branch that drops it was executed by no test at all: disabling it let a transaction
    with `amount=None` into the returned statement and the whole suite stayed green.

    An entry with no amount cannot be reconciled, and substituting a zero would be the wrong
    but plausible line this project exists to prevent. So it is dropped, loudly.
    """
    read = read_ofx(
        ofx(
            "<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n<FITID>NOAMOUNT\n</STMTTRN>\n",
            "<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n<TRNAMT>-10.00\n<FITID>OK\n"
            "</STMTTRN>\n",
        )
    )
    assert [t.bank_reference for t in read.transactions] == ["OK"]
    assert all(t.amount is not None for t in read.transactions)
    dropped = [w for w in read.warnings if "dropped" in w.message]
    assert len(dropped) == 1
    assert "TRNAMT" in dropped[0].message


def test_a_transaction_with_no_date_never_reaches_the_output() -> None:
    read = read_ofx(ofx("<STMTTRN>\n<TRNTYPE>DEBIT\n<TRNAMT>-10.00\n<FITID>NODATE\n</STMTTRN>\n"))
    assert read.transactions == []
    assert any("DTPOSTED" in w.message for w in read.warnings)


def test_a_repeated_tag_keeps_one_value_everywhere_and_says_so() -> None:
    """The normalised field read the first value and `raw` kept the last, so a transaction
    reported -10.00 as its amount while its own raw fields said -9999.00, silently. Anyone
    auditing the normalised figure against the raw one found a different number."""
    read = read_ofx(
        ofx(
            "<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20260115\n<TRNAMT>-10.00\n"
            "<TRNAMT>-9999.00\n<FITID>A\n</STMTTRN>\n"
        )
    )
    transaction = read.transactions[0]
    assert transaction.amount == Decimal("-10.00")
    assert transaction.raw["TRNAMT"] == "-10.00", "raw must agree with the normalised field"
    repeated = [w for w in read.warnings if w.field == "TRNAMT"]
    assert len(repeated) == 1
    assert repeated[0].value == "-9999.00"


@pytest.mark.parametrize("delta", ["0.01", "-0.01", "49.05", "-49.05", "1000000"])
def test_the_reconciliation_check_is_exact_and_not_merely_close(delta: str) -> None:
    """Its exactness rested on a single data point, a file off by -49.06, so a silent tolerance
    of anything up to 49.05 passed the suite green. In a reconciliation, 49.05 is not a
    rounding difference, it is a missing entry."""
    warnings = check_reconciliation(
        Decimal("100.00"), Decimal("100.00") + Decimal(delta), transactions_of(Decimal("0"))
    )
    assert len(warnings) == 1, f"a difference of {delta} must be reported"
    assert Decimal(warnings[0].value or "0") == -Decimal(delta)


def transactions_of(total: Decimal) -> list[Transaction]:
    return [Transaction(date=datetime.date(2026, 1, 15), amount=total, currency="EUR", raw={})]


def test_a_statement_that_balances_exactly_reports_nothing() -> None:
    assert (
        check_reconciliation(
            Decimal("100.00"), Decimal("90.00"), transactions_of(Decimal("-10.00"))
        )
        == []
    )


@pytest.mark.parametrize(
    ("fixture", "field", "expected"),
    [
        ("unnamed-bank/zero-date.ofx", "closing_balance", Decimal("90.00")),
        ("hsbc-brasil/dtstart-ddmmyy.ofx", "closing_balance", Decimal("90.00")),
    ],
)
def test_the_two_unexercised_corpus_deviations_are_read_end_to_end(
    fixture: str, field: str, expected: Decimal
) -> None:
    """`DTASOF` and `DTSTART` are documented deviations that no test read through the public
    path. A corpus case nothing exercises is documentation, not a guard rail."""
    path = CORPUS / fixture
    read = read_ofx(path.read_bytes(), path=str(path))
    assert getattr(read, field) == expected
    assert len(read.transactions) == 1


def test_a_zero_balance_date_does_not_cost_the_statement() -> None:
    """Reading rules, section 5: all zeros means the date is absent, never the epoch and never
    today. `ofxtools` rejects the whole file over it."""
    path = CORPUS / "unnamed-bank" / "zero-date.ofx"
    read = read_ofx(path.read_bytes(), path=str(path))
    assert read.closing_balance == Decimal("90.00")
    assert read.transactions[0].amount == Decimal("-10.00")


def test_a_six_digit_mt940_date_is_the_format_and_not_a_warning() -> None:
    """The rule was corrected after an audit: six digits IS the MT940 format, so warning on
    every date of every file would bury the warnings that mean something."""
    path = REPO / "tests" / "fixtures" / "paired" / "account-a.sta"
    read = read_mt940(path.read_bytes(), path=str(path))
    assert [w for w in read.warnings if w.rule == "date"] == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path", ["\x00evil", "a" * 5000, "", "..", "/etc/passwd"], ids=lambda p: repr(p[:12])
)
async def test_no_path_a_model_can_type_ever_crashes_the_tool(path: str) -> None:
    """A null byte raises ValueError and an over-long path raises ENAMETOOLONG, and neither was
    caught: the tool died with a raw ToolError instead of the envelope it documents. A model
    handed a crash cannot recover; handed an envelope it can."""
    server = build_server(REPO)
    result = await server.call_tool("read_statement", {"path": path})
    # call_tool can also answer InputRequiredResult, which none of these paths does. Narrowing
    # rather than casting: if a future version starts asking for input here, the test says so.
    content = getattr(result, "structured_content", None)
    assert content is not None, f"expected a tool result, got {type(result).__name__}"
    assert content["ok"] is False
    assert content["error"]["kind"] in {"unreadable_path", "outside_root"}
