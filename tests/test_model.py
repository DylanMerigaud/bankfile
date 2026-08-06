"""The model invariants, the ones whose violation produces a WRONG result and not an error."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from bankfile.model import Transaction


def tx(**kw: object) -> Transaction:
    base: dict[str, object] = {
        "date": datetime.date(2026, 1, 15),
        "amount": Decimal("-42.17"),
        "currency": "EUR",
        "raw": {},
    }
    base.update(kw)
    return Transaction(**base)  # type: ignore[arg-type]


def test_the_amount_stays_exact() -> None:
    """The trap this project has to avoid: 0.1 + 0.2 in floating point is not 0.3, and a bank
    reconciliation that is wrong by one cent is a wrong reconciliation."""
    total = tx(amount=Decimal("0.1")).amount + tx(amount=Decimal("0.2")).amount
    assert total == Decimal("0.3")
    # The same computation in binary64, so the reason for Decimal is visible, not just asserted.
    in_floating_point = 0.1 + 0.2
    assert in_floating_point != 0.3
    assert Decimal(str(in_floating_point)) != Decimal("0.3")


def test_a_malformed_currency_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        tx(currency="EURO")


def test_the_transaction_is_immutable() -> None:
    """A statement object that changes after the fact makes the reconciliation unauditable."""
    t = tx()
    with pytest.raises(AttributeError):
        t.amount = Decimal("0")  # type: ignore[misc]
