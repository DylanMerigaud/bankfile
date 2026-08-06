"""The normalised model, a MIRROR of the JSON schemas and never their source.

`corpus/schema/transaction.schema.json` and `corpus/schema/statement.schema.json` are
authoritative. These classes follow them, and `tests/test_schema_mirror.py` fails if the two
diverge. The reverse (the code is authoritative, the schema documents it) would condemn the
TypeScript implementation to run after Python, and two implementations that each carry their
own truth end up diverging in silence.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

# The sections of corpus/reading-rules.md. A warning names the rule that fired, so a reader
# can go from a line in the output straight to the paragraph that decided it.
Rule = Literal["encoding", "header", "amount", "date", "tag"]
SourceFormat = Literal["MT940", "OFX"]


@dataclass(frozen=True, slots=True)
class ReadWarning:
    """Something we could not read, kept instead of being dropped.

    Not called `Warning`: that name is a builtin exception class, and a model type that shadows
    a builtin gets confusing at exactly the wrong moment, in a traceback.

    This type IS the failure doctrine (reading rules, section 0). A file that can be read is
    never rejected over the value of one field, so every value we could not normalise has to
    surface here. Without it, "tolerant parser" just means "parser that loses data quietly",
    which is the measured behaviour we built this corpus to document.
    """

    rule: Rule
    field: str | None
    # The raw value, verbatim. A normalised field left null tells you something is missing; it
    # does not tell you what the file actually said, and that is what you need to write the
    # next rule.
    value: str | None
    message: str


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
    # Nullable because a real file leaves CURDEF empty (ofxparse #81, two Australian banks).
    # The corpus rule for that case is explicit: keep the transaction, leave the currency
    # unset, warn. Guessing one from the country would be a wrong but plausible figure.
    currency: str | None
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
    # A string, not an int: leading zeros in a cheque number are significant.
    check_number: str | None = None

    def __post_init__(self) -> None:
        if self.currency is not None and len(self.currency) != 3:
            msg = f"expected a 3-letter ISO 4217 currency, got {self.currency!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Source:
    """Where the statement came from. The one part that legitimately differs across formats."""

    format: SourceFormat
    path: str | None = None
    encoding: str | None = None


@dataclass(frozen=True, slots=True)
class Statement:
    """A statement: one account, one period, some transactions.

    `account` and `currency` are nullable on purpose. A file whose account line is unreadable
    still carries usable entries, and dropping them would break the rule this whole model is
    built around: never lose data over one field.
    """

    source: Source
    account: str | None = None
    currency: str | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    transactions: list[Transaction] = field(default_factory=list)
    warnings: list[ReadWarning] = field(default_factory=list)
