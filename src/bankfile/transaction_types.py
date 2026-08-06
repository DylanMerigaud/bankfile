"""The shared transaction vocabulary, and the two mappings that feed it.

This module is the unification, concentrated. MT940 says `NTRF`, OFX says `XFER`, and a caller
who wants "transfers" should not have to know either. The measurement that justifies the whole
project sits right here: on the same notion of a transaction, mt940 returns 37 fields and
ofxparse returns 10, with three in common.

**The mapping is a DECISION, not a standard.** Nobody publishes a correspondence between SWIFT
transaction type identification codes and OFX `TRNTYPE`, so this table is ours and it is
arguable. Two consequences we accept on purpose:

- the vocabulary is OPEN, per section 4 of `corpus/reading-rules.md`. A code we do not know
  becomes `OTHER` with a warning, never an exception, and never a silent guess at a neighbour.
- the original code is never destroyed. It stays in the transaction's `raw`, so a caller who
  disagrees with our reading can do their own, which is precisely what people do today by hand
  and what this library is meant to stop being necessary.
"""

from __future__ import annotations

from bankfile.model import ReadWarning

# The vocabulary. Deliberately small: every entry here has to be produced by at least one of the
# two formats, otherwise it is a category nobody can ever observe.
TRANSFER = "TRANSFER"
CHECK = "CHECK"
DIRECT_DEBIT = "DIRECT_DEBIT"
DEPOSIT = "DEPOSIT"
INTEREST = "INTEREST"
DIVIDEND = "DIVIDEND"
FEE = "FEE"
ATM = "ATM"
POINT_OF_SALE = "POINT_OF_SALE"
CASH = "CASH"
PAYMENT = "PAYMENT"
CREDIT = "CREDIT"
DEBIT = "DEBIT"
HOLD = "HOLD"
OTHER = "OTHER"

# OFX 1.0.2, list of TRNTYPE values. This side is nearly a rename: the format already carries a
# vocabulary, so the only judgement calls are SRVCHG and DIRECTDEP, folded into FEE and DEPOSIT
# because a service charge is a fee and a direct deposit is a deposit.
FROM_OFX = {
    "CREDIT": CREDIT,
    "DEBIT": DEBIT,
    "INT": INTEREST,
    "DIV": DIVIDEND,
    "FEE": FEE,
    "SRVCHG": FEE,
    "DEP": DEPOSIT,
    "ATM": ATM,
    "POS": POINT_OF_SALE,
    "XFER": TRANSFER,
    "CHECK": CHECK,
    "PAYMENT": PAYMENT,
    "CASH": CASH,
    "DIRECTDEP": DEPOSIT,
    "DIRECTDEBIT": DIRECT_DEBIT,
    "REPEATPMT": PAYMENT,
    "HOLD": HOLD,
    "OTHER": OTHER,
}

# SWIFT transaction type identification codes, the `N` family carried by MT940 field :61:. Only
# the codes whose meaning is unambiguous are mapped. The rest fall through to OTHER on purpose:
# guessing that NLDP or NBOE is "close enough" to a category would be exactly the kind of
# plausible wrong answer this project refuses to produce.
FROM_MT940 = {
    "NTRF": TRANSFER,
    "NSTO": TRANSFER,
    "NMSC": OTHER,
    "NCHK": CHECK,
    "NDDT": DIRECT_DEBIT,
    "NINT": INTEREST,
    "NDIV": DIVIDEND,
    "NCHG": FEE,
    "NCOM": FEE,
    "NCMS": FEE,
    "NCLR": CASH,
}


def normalise(raw: str | None, *, source_format: str) -> tuple[str | None, list[ReadWarning]]:
    """Map a format specific transaction code onto the shared vocabulary.

    Returns `(None, [])` for an absent code: a transaction with no type is not an error, and
    inventing `OTHER` for it would claim the file said something it did not.
    """
    if raw is None or not raw.strip():
        return None, []
    code = raw.strip().upper()
    table = FROM_OFX if source_format == "OFX" else FROM_MT940
    known = table.get(code)
    if known is not None:
        return known, []
    return OTHER, [
        ReadWarning(
            rule="tag",
            field="type_code",
            value=raw,
            message=(
                f"unknown {source_format} transaction code {code!r}, normalised to {OTHER}. "
                f"The original is kept in the transaction's raw fields."
            ),
        )
    ]
