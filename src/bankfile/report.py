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

from bankfile.model import ReadWarning


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
