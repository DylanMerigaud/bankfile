"""Does the statement add up, and does it say so when it does not.

This check is here because it is the one that found the only real bug of phase 1. `mt940`
negates an amount for a `D` mark and not for an `RC`, a reversed credit, so money leaving an
account came back positive. Every unit test passed. One line of arithmetic did not.

So the arithmetic is now part of the output rather than something a reviewer happens to run.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from bankfile.mt940_adapter import read_mt940

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mt940"
CORPUS = sorted(FIXTURES.rglob("*.sta"))
# `:61:` value date, optional entry date, mark, optional funds code, amount. Deliberately naive
# and deliberately NOT going through the library: a check that shares the code it is checking
# proves nothing.
#
# The `\s*` before the amount is not decoration. `self-provided/sparkassen.sta` wraps the field
# in the middle, mark on one line and amount on the next, which is why that file is in the
# corpus at all. Without it this cross-check would read zero and accuse the parser.
STATEMENT_LINE = re.compile(r"^:61:(?:\d{6})(?:\d{4})?(RC|RD|C|D)(?:[A-Z])?\s*([\d,.]+)", re.M)


def sum_from_the_bytes(path: Path) -> Decimal:
    total = Decimal("0")
    for mark, amount in STATEMENT_LINE.findall(path.read_bytes().decode("latin-1")):
        value = Decimal(amount.rstrip(",.").replace(",", "."))
        # A debit and the reversal of a credit both take money OUT. `mt940` gets the second
        # one wrong, which is exactly why this regex does not ask it.
        total += -value if mark in ("D", "RC") else value
    return total


@pytest.mark.parametrize("fixture", CORPUS, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_our_sum_matches_a_sum_computed_from_the_raw_bytes(fixture: Path) -> None:
    """The adapter's amounts against the same amounts read with a regex.

    Thirteen of these files do not reconcile against their own closing balance. This test is
    what says whose fault that is: if the two sums agree, we read the file correctly and the
    file is the thing that does not add up.
    """
    statement = read_mt940(fixture.read_bytes(), path=str(fixture))
    if not statement.transactions:
        pytest.skip("no entries to sum")
    ours = sum((t.amount for t in statement.transactions), Decimal("0"))
    assert ours == sum_from_the_bytes(fixture)


def test_a_reversed_credit_takes_money_out() -> None:
    """`RC` is the reversal of a credit, so it is negative. `mt940` returns it positive.

    Measured on this file: the library hands back `+204.88` for both of its `RC` lines. A
    positive amount for money that left the account is the wrong but plausible figure this
    whole project is built to prevent.
    """
    fixture = FIXTURES / "betterplace" / "sepa_mt9401.sta"
    statement = read_mt940(fixture.read_bytes(), path=str(fixture))
    reversals = [t for t in statement.transactions if t.raw.get("status") in ("RC", "RD")]
    assert reversals, "this fixture is the one carrying reversals, it must still have them"
    assert all(t.amount < 0 for t in reversals), [str(t.amount) for t in reversals]


def test_a_statement_that_does_not_add_up_says_so() -> None:
    """The file's own numbers contradict each other, and the reader is told.

    No existing parser tells you this. Someone reconciling an account needs to know that the
    file they were sent does not agree with itself, and needs to know it from the tool rather
    than from a spreadsheet three days later.
    """
    fixture = FIXTURES / "jejik" / "ing.sta"
    statement = read_mt940(fixture.read_bytes(), path=str(fixture))
    mismatches = [w for w in statement.warnings if w.field == "62F"]
    assert len(mismatches) == 1
    assert mismatches[0].rule == "amount"
    assert mismatches[0].value == "-49.06"


def test_a_statement_that_adds_up_says_nothing() -> None:
    """A check that fires on a clean file is noise, and noise is how a report stops being read."""
    # A single account file: rabobank.sta holds two, so our reader nulls its balances.
    fixture = FIXTURES / "jejik" / "sns.sta"
    statement = read_mt940(fixture.read_bytes(), path=str(fixture))
    assert statement.opening_balance is not None
    assert statement.closing_balance is not None
    movement = sum((t.amount for t in statement.transactions), Decimal("0"))
    assert statement.opening_balance + movement == statement.closing_balance
    assert [w for w in statement.warnings if w.field == "62F"] == []
