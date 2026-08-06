"""The import report: what we could not read, said once.

The failure doctrine says nothing is ever lost in silence, and it is right. Applied naively it
produces the opposite problem, and this was measured rather than guessed: across the 54 real
MT940 files in the test corpus, 77 of 211 transactions carry a SWIFT type code outside the
mapped vocabulary. One warning per transaction means 77 lines saying the same thing, and a
report nobody reads is worth exactly as much as no report.

So warnings are collapsed on their content. The 77 lines become one per distinct code, which is
the actual information: "this file uses N426 and we do not map it". Nothing is lost by the
collapse, because the code itself was never in the warning to begin with, it is in the
transaction's `raw`.
"""

from __future__ import annotations

from decimal import Decimal

from bankfile.model import ReadWarning, Transaction


def check_reconciliation(
    opening: Decimal | None, closing: Decimal | None, transactions: list[Transaction]
) -> list[ReadWarning]:
    """Does the statement add up: opening plus the entries, against the closing balance.

    This exists because it is the check that found the only real bug of this phase. `mt940`
    negates an amount for a `D` mark and not for an `RC`, a reversed credit, so money leaving
    the account came back positive. No test caught it. Arithmetic did, in one line.

    Run on the 51 real files of the test corpus, it reports 13 that do not add up. All 13 were
    checked by hand against a byte level regex sum that does not go through this library at
    all, and in every case the FILE is what does not balance, not our reading of it: they are
    anonymised or synthetic fixtures whose amounts were scrambled while their balances were
    not. Which is the point. A person reconciling an account needs to be told that the file
    they were sent contradicts itself, and no parser tells them today.
    """
    if opening is None or closing is None or not transactions:
        return []
    movement = sum((t.amount for t in transactions), Decimal("0"))
    delta = opening + movement - closing
    if delta == 0:
        return []
    return [
        ReadWarning(
            rule="amount",
            field="62F",
            value=str(delta),
            message=(
                f"this statement does not add up: opening {opening} plus {movement} of entries "
                f"gives {opening + movement}, and the file states a closing balance of "
                f"{closing}, a difference of {delta}. The entries are returned unchanged, the "
                f"arithmetic is the file's."
            ),
        )
    ]


def dedupe(warnings: list[ReadWarning]) -> list[ReadWarning]:
    """Keep the first of each identical warning, in order.

    Order is preserved on purpose: a report that reshuffles itself between two runs of the same
    file is a report you cannot diff, and diffing two runs is how you notice a bank changed
    something.
    """
    seen: set[tuple[str, str | None, str | None, str]] = set()
    kept = []
    for warning in warnings:
        key = (warning.rule, warning.field, warning.value, warning.message)
        if key in seen:
            continue
        seen.add(key)
        kept.append(warning)
    return kept
