"""The normalised model, a MIRROR of the JSON schema and never its source.

`corpus/schema/transaction.schema.json` is authoritative. This class follows it, and
`tests/test_schema_mirror.py` fails if the two diverge. The reverse (the code is
authoritative, the schema documents it) would condemn the TypeScript implementation to run
after Python, and two implementations that each carry their own truth end up diverging in
silence.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class Transaction:
    """A transaction, whatever the source format.

    The `datetime` module is imported WHOLE and not `from datetime import date`: the field is
    named `date`, so the bare import would be shadowed by it, and the annotations that follow
    (`booking_date: date | None`) would refer to the FIELD instead of the type. mypy caught it,
    Python would never have reported it at runtime.
    """

    date: datetime.date
    # DECIMAL, never float. A cent lost in a binary64 is a wrong reconciliation, and the source
    # file already carries exact decimals: converting them to floating point destroys
    # information that was correct.
    amount: Decimal
    currency: str
    # ALWAYS filled in. The fields specific to the source format, as they are. A normalisation
    # that throws the original away forces a re-parse of the file as soon as a question falls
    # outside the schema, and by then nobody has the file any more.
    raw: dict[str, Any]
    booking_date: datetime.date | None = None
    counterparty_name: str | None = None
    counterparty_account: str | None = None
    reference: str | None = None
    purpose: str | None = None
    bank_reference: str | None = None
    type_code: str | None = None

    def __post_init__(self) -> None:
        if len(self.currency) != 3:
            msg = f"expected a 3-letter ISO 4217 currency, got {self.currency!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Statement:
    """A statement: one account, one period, some transactions."""

    account: str
    transactions: list[Transaction] = field(default_factory=list)
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    currency: str | None = None
