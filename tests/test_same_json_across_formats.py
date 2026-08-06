"""The promise of this project, made testable.

Phase 1 is done when the CLI returns the SAME JSON for an MT940 and an OFX of the same account.
That sentence is the whole product: without it there is no unification layer, only two parsers
in a trench coat. So it gets its own test file, and the test is written against the public API,
never against internals.

`tests/fixtures/paired/account-a.sta` and `account-a.ofx` describe the same account, the same
period and the same single transaction, one in each format. They are synthetic on purpose:
nothing in the wild ships the same statement twice in two formats, and a corpus fixture would
be the wrong tool here anyway, since this file tests the normalisation and not a bank quirk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bankfile import parse
from bankfile.serialize import to_json_dict

PAIRED = Path(__file__).resolve().parent / "fixtures" / "paired"

# The three things that legitimately differ, and nothing else may.
#
# `source` is provenance: the format and the path are exactly what the two files do not share.
#
# `raw` is, by definition, the fields of the origin format. The schema says so and keeps it on
# purpose: a normalisation that throws the original away forces a re-parse as soon as a question
# falls outside the schema.
#
# `opening_balance` is the honest one. OFX 1.x has LEDGERBAL and AVAILBAL and NO opening balance
# element at all, while MT940 carries `:60F:`. We could compute one by subtracting the
# transactions from the closing balance, and we deliberately do not: if the file holds a
# filtered window of transactions, that arithmetic silently produces a wrong but plausible
# balance, which is the single failure this project exists to avoid. So the difference is
# PINNED by its own test below rather than hidden in an exclusion list.
PROVENANCE = ("source",)
FORMAT_SPECIFIC = ("raw",)
NOT_IN_OFX = ("opening_balance",)


def normalised(path: Path) -> dict[str, Any]:
    document = to_json_dict(parse(path))
    for key in (*PROVENANCE, *NOT_IN_OFX):
        document.pop(key, None)
    for transaction in document["transactions"]:
        for key in FORMAT_SPECIFIC:
            transaction.pop(key, None)
    return document


def test_the_same_account_in_two_formats_gives_the_same_json() -> None:
    from_mt940 = normalised(PAIRED / "account-a.sta")
    from_ofx = normalised(PAIRED / "account-a.ofx")
    assert from_mt940 == from_ofx, (
        "the same account read from two formats produced two different documents:\n"
        f"MT940: {json.dumps(from_mt940, indent=2, sort_keys=True)}\n"
        f"OFX:   {json.dumps(from_ofx, indent=2, sort_keys=True)}"
    )


def test_the_shared_document_is_not_empty() -> None:
    """A test comparing two empty dictionaries passes and proves nothing. This is the guard
    against that, and it is not paranoia: an early version of the CLI returned `{}` on an
    unreadable file and the comparison above went green."""
    document = normalised(PAIRED / "account-a.sta")
    assert document["account"] == "0000123456"
    assert document["currency"] == "EUR"
    assert document["closing_balance"] == "990.00"
    assert len(document["transactions"]) == 1
    transaction = document["transactions"][0]
    assert transaction["date"] == "2026-01-15"
    assert transaction["amount"] == "-10.00"
    assert transaction["counterparty_name"] == "ANON MERCHANT"
    assert transaction["purpose"] == "INVOICE 4711"
    assert transaction["reference"] == "T0001"
    assert transaction["bank_reference"] == "B0001"
    assert transaction["type_code"] == "TRANSFER"
    assert transaction["check_number"] is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [("account-a.sta", "1000.00"), ("account-a.ofx", None)],
)
def test_the_opening_balance_difference_is_pinned_not_hidden(
    name: str, expected: str | None
) -> None:
    """MT940 carries an opening balance and OFX 1.x has no element for one.

    Excluding it from the comparison above without stating it here would let a future change
    start inventing the value without any test noticing.
    """
    assert to_json_dict(parse(PAIRED / name))["opening_balance"] == expected


def test_both_files_read_without_a_single_warning() -> None:
    """These two files are clean by construction. If reading them produces a warning, a rule
    fires where nothing is wrong, and every warning we emit on real files becomes noise."""
    for name in ("account-a.sta", "account-a.ofx"):
        document = to_json_dict(parse(PAIRED / name))
        assert document["warnings"] == [], f"{name} produced {document['warnings']}"
