"""MT940 read through `wolph/mt940`, mapped onto the shared model.

The parser is NOT reimplemented. It already does the hard part of MT940, which is the `:86:`
field: reassembling a purpose across `?2x` subfields and across physical line breaks. That was
verified by running it on real German files, and it is the part every from-scratch MT940 reader
gets wrong first.

What this module owns is the mapping, and the mapping is where the value is: the two models
agree on almost nothing. `entry_date` is our booking date, an amount is an object carrying its
own currency, a transaction knows its statement only through a back-reference, and the raw data
is full of types `json.dumps` refuses. It also means auditing what the parser decided on its
own, twice measured against a real file:

- the sign of a REVERSAL. SWIFT field `:61:` marks an entry `C`, `D`, `RC` (reversal of a
  credit) or `RD` (reversal of a debit); `mt940` negates the amount for `D` only, so a reversed
  credit comes back positive when it took money OUT. `betterplace/sepa_mt9401.sta` proves it by
  arithmetic: the block opens at -1234718,36 and closes at -1237628,23, and the sum of its
  entries only lands there if the `RC` line of 204,88 is negative. The sign is therefore taken
  from the mark and not from the parser.
- a date the file wrote and the calendar refuses. `self-provided/february_30.sta` dates an entry
  30 February, and `mt940` silently moves it to the 29th. We keep the moved date, because the
  entry is otherwise sound and the model has no null date, but the day the file actually stated
  is put back into `raw` and a `date` warning names it. A date quietly moved by one day is the
  wrong but plausible value of section 0, and it must never reach a reconciliation unannounced.

Four more decisions, the first three of them the failure doctrine of
`corpus/reading-rules.md` section 0 applied to a real corpus:

- A file holding several accounts (six of the 54 corpus files do) cannot become one statement.
  The entries are kept, the account and both balances go null and say why. An opening balance
  taken from one account next to a closing balance taken from another is exactly the "wrong but
  plausible number" the doctrine is built to prevent.
- A transaction whose file names no currency anywhere keeps a null currency and a warning
  carrying what the file did say. Four corpus files are in that case. The entry is never
  dropped: losing a real 30,00 movement over a missing label is the worse of the two failures,
  and naming a currency the file never gave would be the wrong but plausible value.
- A statement block that no dialect can parse costs that block only. The rest of the file, and
  the reasons, come back to the caller.
- `type_code` carries the shared vocabulary of `bankfile.transaction_types`, not the SWIFT code
  itself. MT940 says `NTRF` where OFX says `XFER` for the same movement, so keeping the code
  verbatim would make the two formats disagree on the same account, which is the one thing this
  phase has to prove they do not. Both raw codes, `id` and the German GVC `transaction_code`,
  stay in `raw`.

Two clauses of the corpus rules are deliberately NOT applied here, and they need arbitration
rather than silence. Both were written from OFX files, and MT940 is the format where SWIFT
already fixed what they leave open:

- section 5, "exactly six digits is DDMMYY, and WARN". In MT940 six digits is the FORMAT: the
  value date of `:61:` is `6!n` YYMMDD. Reading `110722` as 22 July 2011 is not a guess, and
  warning on every date of every file would bury the warnings that mean something.
- section 3, "a comma followed by exactly three digits is ambiguous, and WARN". In MT940 the
  comma is the decimal mark by specification and there is no thousands separator, so `1,500` is
  one and a half, and a three digit group is what a three decimal currency looks like (BHD,
  KWD, TND). No corpus file has one, and a warning there would be noise on a correct value.

The rest of the sections IS applied: amounts are Decimal and never float, an empty tag reads as
absent, an unknown transaction code becomes OTHER with a warning, and the encoding chain is in
`_decode` with its own disagreement written down.
"""

from __future__ import annotations

import calendar
import datetime
import re
from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

import mt940
from mt940.models import Transactions
from mt940.processors import date_fixup_pre_processor

from bankfile.model import ReadWarning, Source, Statement, Transaction
from bankfile.report import dedupe
from bankfile.transaction_types import normalise as normalise_type

_Tags = dict[int | str, mt940.tags.Tag] | None
# A parsed tag, as `mt940` hands it to a processor: the keys are tag and bank specific. Spelled
# out here rather than imported from `mt940._types`, a private module we should not pin to.
_TagDict = dict[str, Any]

_ASNB = mt940.tags.StatementASNB()
_GLS = mt940.tags.StatementGLS()

# Tried in order, and only ever because the standard tags failed. Both variants relax the length
# of the `:61:` customer reference, which the standard tag caps at 16 characters: ASNB puts a
# full IBAN there, GLS a SEPA end-to-end reference. Relaxing the standard tag itself is not an
# option, it would change how banks that legitimately pack data after a 16x reference (Rabobank)
# are read.
_VARIANTS: tuple[tuple[str, _Tags], ...] = (
    ("ASNB", {_ASNB.id: _ASNB}),
    ("GLS", {_GLS.id: _GLS}),
)

# `:20:` is the transaction reference, once per statement. It is therefore where one statement
# block ends and the next begins in a file that concatenates several. The newline after the
# first colon is part of the tag syntax and banks do use it (`self-provided/sparkassen.sta`
# wraps `:86:` that way): missing a wrapped `:20:` would glue two statements, and two accounts,
# into one block whose balances no longer belong to its entries.
_BLOCK_START = re.compile(r"(?m)^(?=:\n?20:)")
_ANY_TAG = re.compile(r"(?m)^:\n?(?:\d{2}|NS)[A-Z]?:")
_STATEMENT_LINE = re.compile(r"(?m)^:\n?61:")
_REFERENCE = re.compile(r"(?m)^:\n?20:(?P<reference>.*)")

_OBJECT_ADDRESS = re.compile(r" at 0x[0-9a-f]+")

# SWIFT field :61: subfield 3, the debit/credit mark. `RC` is the reversal OF a credit, so the
# money leaves the account, and `RD` the reversal of a debit. `mt940` negates on `D` alone,
# which leaves a reversed credit positive: the sign is taken from this set instead.
_DEBIT_MARKS = frozenset({"D", "RC"})

# Balance tags, in the order they are trusted. `:60F:`/`:62F:` are the statement's own opening
# and closing; `:60:`/`:60M:` are the continuation forms, used when a bank splits one statement
# over several files or pages. Falling back to them keeps a real figure instead of a null, and
# the fallback is always named because a continuation balance is not the same claim.
_OPENING = ("final_opening_balance", "opening_balance", "intermediate_opening_balance")
_CLOSING = ("final_closing_balance", "closing_balance", "intermediate_closing_balance")
_BALANCE_TAG = {
    "final_opening_balance": ":60F:",
    "opening_balance": ":60:",
    "intermediate_opening_balance": ":60M:",
    "final_closing_balance": ":62F:",
    "closing_balance": ":62:",
    "intermediate_closing_balance": ":62M:",
}


def read_mt940(data: bytes, *, path: str | None = None) -> Statement:
    """Read MT940 bytes into a statement. Never raises: what cannot be read is reported."""
    text, encoding, warnings = _decode(data)
    blocks, parse_warnings = _parse(text)
    warnings += parse_warnings

    transactions: list[Transaction] = []
    for block in blocks:
        for entry in block.transactions:
            transaction, entry_warnings = _transaction(entry.data, block.currency)
            warnings += entry_warnings
            if transaction is not None:
                transactions.append(transaction)

    accounts = _distinct(_text(block.data.get("account_identification")) for block in blocks)
    currencies = _distinct(_currency(block.currency) for block in blocks)
    account = accounts[0] if len(accounts) == 1 else None
    currency = currencies[0] if len(currencies) == 1 else None

    opening = closing = None
    if len(accounts) <= 1 and len(currencies) <= 1:
        opening, opening_warning = _balance(blocks, _OPENING, last=False)
        closing, closing_warning = _balance(blocks, _CLOSING, last=True)
        warnings += [w for w in (opening_warning, closing_warning) if w is not None]

    if len(accounts) > 1:
        warnings.append(
            ReadWarning(
                rule="tag",
                field="account_identification",
                value=", ".join(accounts),
                message=(
                    f"the file holds {len(accounts)} accounts and a statement carries one, "
                    f"so the account and the balances are left null; the entries are kept"
                ),
            )
        )
    if len(currencies) > 1:
        warnings.append(
            ReadWarning(
                rule="tag",
                field="currency",
                value=", ".join(currencies),
                message=(
                    f"the file holds {len(currencies)} currencies, so the statement currency "
                    f"and both balances are left null; every entry keeps the currency of its "
                    f"own block"
                ),
            )
        )

    if not any(block.data or block.transactions for block in blocks):
        warnings.append(
            ReadWarning(
                rule="tag",
                field=None,
                value=None,
                message="no MT940 tag was recognised, nothing in this input is a statement",
            )
        )

    return Statement(
        source=Source(format="MT940", path=path, encoding=encoding),
        account=account,
        currency=currency,
        opening_balance=opening,
        closing_balance=closing,
        transactions=transactions,
        warnings=dedupe(warnings),
    )


def _decode(data: bytes) -> tuple[str, str, list[ReadWarning]]:
    """Reading rules section 1, on a format that declares no charset.

    MT940 has no header naming its encoding, so the table lands on the default, cp1252. utf-8 is
    tried first because it is the only codec here that can PROVE it is right: a byte string
    either is valid utf-8 or it is not, and a modern export decoded as cp1252 would turn every
    accent into two plausible characters without anything failing.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _decode_legacy(data)
    return text, "utf-8", []


def _decode_legacy(data: bytes) -> tuple[str, str, list[ReadWarning]]:
    """cp1252, then iso-8859-1.

    The reading rules say neither of the two can fail on a single byte. That is true of
    iso-8859-1 and FALSE of cp1252, which leaves 0x81, 0x8d, 0x8f, 0x90 and 0x9d unassigned:
    `self-provided/raiffeisen-cmi.sta`, a DOS code page export, raises on 0x81. So the last
    codec has to be the one that maps all 256 values, and the choice is reported rather than
    assumed.
    """
    try:
        text, codec = data.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        text, codec = data.decode("iso-8859-1"), "iso-8859-1"
    return (
        text,
        codec,
        [
            ReadWarning(
                rule="encoding",
                field=None,
                value=None,
                message=f"not valid utf-8, decoded as {codec}; text fields may be wrong",
            )
        ],
    )


def _parse(text: str) -> tuple[list[Transactions], list[ReadWarning]]:
    """Parse every statement block, with the dialect that loses the fewest of them."""
    blocks = _split(text)
    parsed, failures = _attempt(blocks, None)
    dialect: str | None = None

    for name, tags in _VARIANTS:
        if not failures:
            break
        good, bad = _attempt(blocks, tags)
        if len(bad) < len(failures):
            parsed, failures, dialect = good, bad, name

    warnings = []
    if dialect is not None:
        warnings.append(
            ReadWarning(
                rule="tag",
                field=None,
                value=None,
                message=(
                    f"the standard :61: statement line does not match this file, "
                    f"read with the {dialect} variant tag instead"
                ),
            )
        )
    # The reference and the count of `:61:` lines are what make two lost blocks two warnings
    # instead of one: they are deduplicated on content, and "could not be read" is the same
    # sentence for every block. A report that collapses two losses into one under-states how
    # much of the file is missing, which is the silent loss this doctrine forbids.
    warnings += [
        ReadWarning(
            rule="tag",
            field=None,
            value=_reference(block),
            message=(
                f"a statement block could not be read and was left out, "
                f"{_lost(block)} lost with it: {reason}"
            ),
        )
        for block, reason in failures
    ]
    return parsed, warnings


def _attempt(blocks: list[str], tags: _Tags) -> tuple[list[Transactions], list[tuple[str, str]]]:
    """Every block read with one dialect: what came out, and why the rest did not."""
    attempt = [(block, _parse_block(block, tags)) for block in blocks]
    return (
        [result for _, result in attempt if isinstance(result, Transactions)],
        [(block, result) for block, result in attempt if isinstance(result, str)],
    )


def _lost(block: str) -> str:
    """How many entries a block took with it. A count is what makes the loss measurable."""
    count = len(_STATEMENT_LINE.findall(block))
    return f"{count} statement line{'' if count == 1 else 's'}"


def _reference(block: str) -> str | None:
    """The `:20:` reference of a block, which is how a bank names one statement."""
    match = _REFERENCE.search(block)
    return _text(match.group("reference")) if match else None


def _split(text: str) -> list[str]:
    """One block per `:20:`.

    Parsing the blocks separately, instead of letting them merge into one collection, is what
    keeps the balances honest: in a file split per day, the merged view reports the LAST block's
    opening balance next to the whole month's entries. A file with no `:20:` at all is still a
    statement, and a real one: two corpus files start straight at `:61:`.

    Whatever sits BEFORE the first `:20:` is a block too, whenever it holds a tag. Nine corpus
    files open on a SWIFT envelope (`{1:F01...}{4:`) or a bank header, which carries no tag and
    is rightly dropped; but a file whose entries start before its first `:20:` would otherwise
    lose them all without a word.
    """
    blocks = [block for block in _BLOCK_START.split(text) if _ANY_TAG.search(block)]
    return blocks or [text]


def _parse_block(block: str, tags: _Tags) -> Transactions | str:
    """Parse one block, or return the reason it could not be parsed.

    `Transactions.parse` is called directly rather than `mt940.parse`, which sniffs whether its
    argument is a path and would read a file off the disk when handed short input. Bank data is
    never a filename.

    Every exception is caught because the parser has no failure type of its own: a tag that does
    not match raises RuntimeError, an impossible date raises ValueError, and an amount of "," a
    decimal.InvalidOperation. Enumerating them is how the next bank gets an exception out of a
    reader whose contract is to never raise.
    """
    parsed = Transactions(tags=dict(tags) if tags else None, processors=_PROCESSORS)
    try:
        parsed.parse(block)
    except Exception as error:
        # The parser puts the repr of its tag object in the message, memory address included.
        # Two runs of the same file would then produce two different reports, and a report you
        # cannot diff is a report that never tells you a bank changed something.
        return f"{type(error).__name__}: {_OBJECT_ADDRESS.sub('', str(error))}"
    return parsed


def _record_impossible_date(
    _transactions: Transactions, _tag: mt940.tags.Tag, tag_dict: _TagDict, *_args: Any
) -> _TagDict:
    """Keep the day the file wrote when the calendar refuses it.

    `mt940` repairs 30 February into the last day of the month, one line further down the same
    processor chain, and repairing it is the right call: the entry is sound and dropping it
    would lose a real movement. Repairing it in SILENCE is not, because the value date is what a
    reconciliation matches on. So the original is captured here, before the repair, and the
    mapping turns it into a `date` warning.
    """
    year, month, day = tag_dict.get("year"), tag_dict.get("month"), tag_dict.get("day")
    # Same arithmetic as the repair itself, on the same two-digit year, so that this fires
    # exactly when the repair does and never on a date the parser left alone.
    if month == "02" and year and day and int(day, 10) > calendar.monthrange(int(year, 10), 2)[1]:
        tag_dict["impossible_value_date"] = f"{year}{month}{day}"
    return tag_dict


# The library's own statement pre-processor is kept and merely preceded: dropping it would turn
# an impossible date back into an exception, which costs the whole block.
_PROCESSORS: dict[str, list[Callable[..., _TagDict]]] = {
    "pre_statement": [_record_impossible_date, date_fixup_pre_processor]
}


def _transaction(
    data: dict[str, Any], statement_currency: str | None
) -> tuple[Transaction | None, list[ReadWarning]]:
    """One `:61:` line, plus whatever its `:86:` field carried, onto our transaction."""
    date = _date(data.get("date"))
    amount = _decimal(data.get("amount"))
    if date is None or amount is None:
        # Not reachable through `:61:`, which yields both or raises. Kept because the model
        # cannot represent an entry without them and the doctrine forbids raising over a field.
        field = "date" if date is None else "amount"
        message = f"a transaction without a {field} cannot be represented, entry left out"
        return None, [ReadWarning(rule="tag", field=field, value=None, message=message)]

    warnings: list[ReadWarning] = []
    impossible = _text(data.get("impossible_value_date"))
    if impossible is not None:
        warnings.append(
            ReadWarning(
                rule="date",
                field="date",
                value=impossible,
                message=(
                    f"the file dates this entry {impossible} (YYMMDD), a day February does not "
                    f"have; the entry is kept on {date.isoformat()} and the date it claimed is "
                    f"in its raw fields"
                ),
            )
        )

    # `id` is the SWIFT transaction type identification code (NTRF, NCHK...), the only field
    # here with a cross-format meaning. `transaction_code` is the German GVC, a national code,
    # and it stays in `raw` where a caller who wants it can still find it.
    type_code, type_warnings = normalise_type(_text(data.get("id")), source_format="MT940")
    warnings += type_warnings
    declared = getattr(data.get("amount"), "currency", None)
    currency = _currency(declared) or _currency(statement_currency)
    if currency is None:
        # Left null, never filled with a placeholder. The schema made this field nullable at
        # the corpus's request precisely so that "we do not know" stays distinct from a value.
        warnings.append(
            ReadWarning(
                rule="tag",
                field="currency",
                value=_text(declared),
                message=(
                    "no currency on the amount and none on the statement balance, "
                    "the amount is kept without one"
                ),
            )
        )

    return (
        Transaction(
            date=date,
            amount=_signed(amount, data.get("status")),
            currency=currency,
            raw={key: _json_safe(value) for key, value in data.items()},
            booking_date=_date(data.get("entry_date")),
            counterparty_name=_text(data.get("applicant_name")),
            counterparty_account=_first(
                data.get("applicant_iban"),
                data.get("gvc_applicant_iban"),
                data.get("applicant_bin"),
            ),
            reference=_first(data.get("customer_reference"), data.get("end_to_end_reference")),
            purpose=_first(data.get("purpose"), data.get("transaction_details")),
            bank_reference=_text(data.get("bank_reference")),
            type_code=type_code,
            # MT940 has no cheque number. A mapping that fills the field from a neighbouring
            # one is a mapping that lies, and the schema allows null.
            check_number=None,
        ),
        warnings,
    )


def _signed(amount: Decimal, status: object) -> Decimal:
    """The sign of an entry, taken from its debit/credit mark rather than from the parser.

    `mt940` negates the amount when the mark is `D` and leaves it alone otherwise, which is
    right for `C` and `RD` and WRONG for `RC`, a reversed credit: the money went out.
    `betterplace/sepa_mt9401.sta` settles it by arithmetic rather than by reading the standard,
    its `:60F:` and `:62F:` only balance if its 204,88 `RC` entry is negative.
    """
    return -abs(amount) if (_text(status) or "").upper() in _DEBIT_MARKS else abs(amount)


def _balance(
    blocks: list[Transactions], keys: tuple[str, ...], *, last: bool
) -> tuple[Decimal | None, ReadWarning | None]:
    """The first, or the last, block that carries one of these balances.

    Not "the last block's balance": in `jejik/abnamro.sta` only the first block closes, and
    reading the closing balance off the last block would report none.

    The tags are tried in order of authority, so a `:60F:` anywhere in the file always beats a
    `:60M:`. A file that only ever carries the continuation form is a page of a longer
    statement; its balance is a real figure and reporting null instead would lose it, so it is
    used and the warning says which tag it came from.
    """
    ordered = list(reversed(blocks)) if last else list(blocks)
    for key in keys:
        for block in ordered:
            amount = _decimal(getattr(block.data.get(key), "amount", None))
            if amount is None:
                continue
            if key == keys[0]:
                return amount, None
            return amount, ReadWarning(
                rule="tag",
                field=key,
                value=str(amount),
                message=(
                    f"no {_BALANCE_TAG[keys[0]]} in this file, the balance is the "
                    f"{_BALANCE_TAG[key]} of a continuation page and not the statement's own"
                ),
            )
    return None, None


def _distinct(values: Iterable[str | None]) -> list[str]:
    """Distinct, in file order: a set would reorder the warning message between runs."""
    return list(dict.fromkeys(value for value in values if value is not None))


def _first(*values: object) -> str | None:
    """The first of the mt940 fields that carries anything, the `else` of the mapping table."""
    return next((text for text in map(_text, values) if text is not None), None)


def _text(value: object) -> str | None:
    """Reading rules section 4: a tag that is present but empty means ABSENT, not an empty
    string, so a caller never has to tell the two apart."""
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _currency(value: object) -> str | None:
    """Three letters or nothing. The model rejects anything else, and it is right to: a
    currency field holding "EU" or a bank code is a field nobody can convert with."""
    text = _text(value)
    if text is None:
        return None
    code = text.upper()
    return code if len(code) == 3 and code.isalpha() else None


def _date(value: object) -> datetime.date | None:
    """mt940 returns its own `Date`, a subclass of `datetime.date`. It is rebuilt as a plain
    date so that nothing of the parser leaks into the model the schema mirrors."""
    if not isinstance(value, datetime.date):
        return None
    return datetime.date(value.year, value.month, value.day)


def _decimal(value: object) -> Decimal | None:
    """The Decimal inside an mt940 `Amount`, already exact. Never re-parsed through a float."""
    amount = getattr(value, "amount", None)
    return amount if isinstance(amount, Decimal) else None


def _json_safe(value: object) -> object:
    """`raw` is a promise: the whole source record, serialisable.

    mt940 stores Decimal, its own Date and its own Amount in there, and none of the three
    survives `json.dumps`. They become strings rather than disappearing, because once the file
    is gone `raw` is the only copy of what the bank actually sent.
    """
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value)
