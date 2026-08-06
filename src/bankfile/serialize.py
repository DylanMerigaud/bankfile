"""Turn a `Statement` into the JSON document described by `corpus/schema/statement.schema.json`.

Kept apart from the model on purpose. The model is a mirror of the schema and nothing else; the
moment it grows a `to_json` method, the temptation is to shape the model around what is
convenient to serialise, and the schema stops being the authority.

Every money value leaves as a STRING. That is the schema's decision and it is the one that
matters most in this file: `json.dumps` on a float silently rounds, and a cent lost inside a
binary64 is a false reconciliation that nobody sees.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from bankfile.model import ReadWarning, Statement, Transaction


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _day(value: datetime.date | None) -> str | None:
    return None if value is None else value.isoformat()


def _jsonable(value: Any) -> Any:
    """Last line of defence for `raw`, whose contents we do not control.

    The origin fields come from another library (mt940 hands back `Decimal`, `date` and its own
    `Amount` objects). A reader that forgets to convert one of them would make the CLI die on
    `json.dumps` while the statement itself was read perfectly. Stringifying is the right
    failure here: losing the type of an origin field is a nuisance, losing the whole statement
    over it is not.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def transaction_to_json_dict(transaction: Transaction) -> dict[str, Any]:
    return {
        "date": _day(transaction.date),
        "booking_date": _day(transaction.booking_date),
        "amount": _money(transaction.amount),
        "currency": transaction.currency,
        "counterparty_name": transaction.counterparty_name,
        "counterparty_account": transaction.counterparty_account,
        "reference": transaction.reference,
        "purpose": transaction.purpose,
        "bank_reference": transaction.bank_reference,
        "type_code": transaction.type_code,
        "check_number": transaction.check_number,
        "raw": _jsonable(transaction.raw),
    }


def warning_to_json_dict(warning: ReadWarning) -> dict[str, Any]:
    return {
        "rule": warning.rule,
        "field": warning.field,
        "value": warning.value,
        "message": warning.message,
    }


def to_json_dict(statement: Statement) -> dict[str, Any]:
    return {
        "account": statement.account,
        "currency": statement.currency,
        "opening_balance": _money(statement.opening_balance),
        "closing_balance": _money(statement.closing_balance),
        "transactions": [transaction_to_json_dict(t) for t in statement.transactions],
        "warnings": [warning_to_json_dict(w) for w in statement.warnings],
        "source": {
            "format": statement.source.format,
            "path": statement.source.path,
            "encoding": statement.source.encoding,
        },
    }
