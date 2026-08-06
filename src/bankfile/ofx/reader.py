"""OFX and QFX to the normalised statement.

This is the module where the corpus stops being documentation and starts being a
specification. Every branch below exists because a real file made an existing parser fail, and
the note beside that file says which one.

We do NOT build on `ofxparse`. It is the abandoned incumbent this project inherits from, and
its failures are measured in `corpus/measurements/2026-08-05.json`: it dies on a collapsed
header, it dies on `CHARSET:NONE`, and on a file that merely starts with a blank line it
silently returns zero headers instead of nine. We do not build on `ofxtools` either: it is
maintained and strict, which is the right call for validating a file you emit and the wrong one
for reading a file a bank sent you. It rejects `CHARSET:8859-1`, `Credit`, `010126` and a zero
balance date, all of which are real files somebody has to reconcile today.
"""

from __future__ import annotations

from decimal import Decimal

from bankfile.model import ReadWarning, Source, Statement, Transaction
from bankfile.normalize import parse_amount, parse_date
from bankfile.ofx.header import read_header
from bankfile.ofx.sgml import Node, parse_tags
from bankfile.report import dedupe
from bankfile.transaction_types import normalise as normalise_type

# A bank statement and a credit card statement carry the same shape under different tags.
STATEMENT_TAGS = ("STMTRS", "CCSTMTRS")
# Walking into a nested statement is how one account's money ends up under another's.
STATEMENT_BOUNDARY = frozenset(STATEMENT_TAGS)
ACCOUNT_FROM_TAGS = ("BANKACCTFROM", "CCACCTFROM")
ACCOUNT_TO_TAGS = ("BANKACCTTO", "CCACCTTO")


def _first(node: Node, tags: tuple[str, ...]) -> Node | None:
    for tag in tags:
        for found in node.find_all(tag, stop_at=STATEMENT_BOUNDARY):
            return found
    return None


def _statements(root: Node) -> list[Node]:
    """Every statement aggregate, in the order the DOCUMENT writes them.

    The order is the whole point, and one walk gives both things that depend on it.

    We return the FIRST, and the warning below promises the caller exactly that, so "first" has
    to mean first in the file. Asking `find_all` for STMTRS and then for CCSTMTRS answers with
    every bank statement before every credit card one, so a file that opens on a card statement
    and carries a current account further down would be read as the current account while being
    reported as the first: a plausible set of figures under the wrong account, which is the
    failure this library exists to prevent.

    The walk is depth first and yields a statement BEFORE anything nested inside it, which is
    what keeps the first one outermost. A statement nested in another is the second half of a
    file whose `</STMTRS>` was omitted, and reading that inner one as the file's first statement
    would put one account's money under another's number and currency.

    Nested ones are still counted, because the count is what decides the warning. Leaving them
    out would drop a statement in SILENCE, which the reading rules call worse than a crash.
    """
    found: list[Node] = []
    # Iterative, like the walk in sgml.py and for the same reason: a corrupt file nests as deep
    # as it likes, and a lookup that answers RecursionError is a lookup that failed.
    stack = list(reversed(root.children))
    while stack:
        node = stack.pop()
        if node.tag in STATEMENT_BOUNDARY:
            found.append(node)
        stack.extend(reversed(node.children))
    return found


def _text(node: Node, *tags: str) -> str | None:
    """First non-empty value among several spellings of the same field.

    The several spellings are not hypothetical. `CHECKNUM` and `CHKNUM` are the same field at
    two different banks, attested in ofxparse PR #173, and a reader that knows only one of them
    drops a cheque number without a word. That is the failure mode the corpus calls worse than
    a crash.
    """
    for tag in tags:
        value = node.child_text(tag)
        if value:
            return value
    return None


def _statement_text(node: Node, tag: str) -> str | None:
    """A statement level field, looked up without crossing into a nested statement."""
    for found in node.find_all(tag, stop_at=STATEMENT_BOUNDARY):
        return found.value
    return None


def _transaction_currency(node: Node, default: str | None) -> str | None:
    """`CURRENCY` on a transaction overrides the statement default, per OFX."""
    currency = node.child("CURRENCY")
    if currency is not None:
        symbol = currency.child_text("CURSYM")
        if symbol:
            return symbol
    return default


def _raw_fields(node: Node, warnings: list[ReadWarning]) -> dict[str, str | None]:
    """Every direct child, known or not.

    Keeping the unknown ones is the whole point of the `tags-outside-spec` case: a real
    Australian file carries `VALUEDATE`, `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL` inside a
    transaction, and both existing parsers drop them in silence.

    A repeated tag keeps the FIRST value, which is what every normalised field above reads, and
    warns. Built as a plain dict comprehension this took the LAST, so a transaction carrying
    `TRNAMT` twice reported -10.00 as its amount while its own `raw` said -9999.00, with
    nothing to say the two disagreed. A caller auditing the normalised figure against the raw
    one would have found a different number and no explanation.
    """
    fields: dict[str, str | None] = {}
    for child in node.children:
        if child.tag in fields:
            warnings.append(
                ReadWarning(
                    rule="tag",
                    field=child.tag,
                    value=child.value,
                    message=(
                        f"{child.tag} appears more than once in this transaction. The first "
                        f"value is the one used everywhere; this later one is reported here "
                        f"and not merged, because picking silently between two values of the "
                        f"same field is how a wrong figure gets in."
                    ),
                )
            )
            continue
        fields[child.tag] = child.value
    return fields


def _read_transaction(
    node: Node, *, default_currency: str | None, warnings: list[ReadWarning]
) -> Transaction | None:
    amount, amount_warnings = parse_amount(_text(node, "TRNAMT") or "", field="TRNAMT")
    warnings.extend(amount_warnings)
    date, date_warnings = parse_date(_text(node, "DTPOSTED") or "", field="DTPOSTED")
    warnings.extend(date_warnings)
    currency = _transaction_currency(node, default_currency)

    # A date and an amount are the two things without which an entry cannot be reconciled at
    # all, so a transaction missing either is dropped, loudly. Substituting a zero or today's
    # date would produce exactly the wrong but plausible line this project exists to prevent.
    #
    # A missing CURRENCY is deliberately NOT in that list. Real files leave CURDEF empty
    # (ofxparse #81), and dropping the entry there would reject a whole statement over one
    # empty tag. The currency stays null and the warning below says so.
    missing = [name for name, value in (("DTPOSTED", date), ("TRNAMT", amount)) if value is None]
    if missing or amount is None or date is None:
        warnings.append(
            ReadWarning(
                rule="tag",
                field="STMTTRN",
                value=",".join(sorted(_raw_fields(node, []))),
                message=(
                    f"transaction dropped, it has no {', '.join(missing)}. A line without one "
                    f"of those cannot be reconciled, and filling one in would invent a figure. "
                    f"The tags it did carry are listed above; their VALUES are deliberately not "
                    f"repeated here, because warnings end up in logs and in an MCP client's "
                    f"server log, and a counterparty name does not belong in either."
                ),
            )
        )
        return None

    booking_date = None
    # DTAVAIL only. DTUSER was in this fallback and it does not belong: it is the date the
    # CUSTOMER initiated the transaction, when the cheque was written or the transfer
    # scheduled, which can precede the posting by weeks. Putting it here produced a plausible
    # date whose meaning nothing recorded, the exact output the reading rules forbid. Nothing
    # is lost: `raw` keeps DTUSER for any caller who wants it.
    booking_raw = _text(node, "DTAVAIL")
    if booking_raw:
        booking_date, booking_warnings = parse_date(booking_raw, field="DTAVAIL")
        warnings.extend(booking_warnings)

    type_code, type_warnings = normalise_type(_text(node, "TRNTYPE"), source_format="OFX")
    warnings.extend(type_warnings)

    if currency is None:
        warnings.append(
            ReadWarning(
                rule="tag",
                field="CURDEF",
                value=None,
                message=(
                    "no currency on this transaction and none on the statement, so the amount "
                    "is kept without one. Guessing from the country or the bank identifier "
                    "would invent a figure's meaning."
                ),
            )
        )

    account_to = _first(node, ACCOUNT_TO_TAGS)
    payee = node.child("PAYEE")
    return Transaction(
        date=date,
        amount=amount,
        currency=currency,
        raw=_raw_fields(node, warnings),
        booking_date=booking_date,
        counterparty_name=_text(node, "NAME") or (payee.child_text("NAME") if payee else None),
        counterparty_account=account_to.text("ACCTID") if account_to else None,
        reference=_text(node, "REFNUM"),
        purpose=_text(node, "MEMO"),
        bank_reference=_text(node, "FITID"),
        type_code=type_code,
        # Both spellings, because both exist in the wild. See ofxparse #173 and #162.
        check_number=_text(node, "CHECKNUM", "CHKNUM"),
    )


def read_ofx(data: bytes, *, path: str | None = None) -> Statement:
    header = read_header(data)
    root, tag_warnings = parse_tags(header.body)
    warnings: list[ReadWarning] = [*header.warnings, *tag_warnings]

    # Found in document order, and both uses below depend on that: the one we read is the first
    # of the file, and the count that decides the warning includes the nested ones, so no
    # statement is ever left out of the report in silence. See _statements.
    statements = _statements(root)
    if not statements:
        return Statement(
            source=Source(format="OFX", path=path, encoding=header.encoding),
            warnings=dedupe(
                [
                    *warnings,
                    ReadWarning(
                        rule="tag",
                        field=None,
                        value=None,
                        message=(
                            "no STMTRS or CCSTMTRS aggregate in this document, so it carries no "
                            "statement to read"
                        ),
                    ),
                ]
            ),
        )
    if len(statements) > 1:
        # Phase 1 reads one statement per file. Saying so is better than quietly returning the
        # first of several and letting a caller reconcile a third of an account.
        warnings.append(
            ReadWarning(
                rule="tag",
                field="STMTRS",
                value=str(len(statements)),
                message=(
                    f"{len(statements)} statements in this file, only the first is returned. "
                    f"Multi statement files are not handled yet."
                ),
            )
        )
    statement = statements[0]

    account_node = _first(statement, ACCOUNT_FROM_TAGS)
    currency = _statement_text(statement, "CURDEF")
    closing: Decimal | None = None
    ledger = _first(statement, ("LEDGERBAL",))
    if ledger is not None:
        balance_raw = ledger.child_text("BALAMT")
        if balance_raw:
            closing, balance_warnings = parse_amount(balance_raw, field="BALAMT")
            warnings.extend(balance_warnings)

    transactions = []
    for node in statement.find_all("STMTTRN", stop_at=STATEMENT_BOUNDARY):
        transaction = _read_transaction(node, default_currency=currency, warnings=warnings)
        if transaction is not None:
            transactions.append(transaction)

    return Statement(
        source=Source(format="OFX", path=path, encoding=header.encoding),
        account=account_node.child_text("ACCTID") if account_node else None,
        currency=currency,
        # OFX 1.x has LEDGERBAL and AVAILBAL and no opening balance element at all. We could
        # subtract the transactions from the closing balance; we do not, because on a filtered
        # window of transactions that arithmetic produces a wrong balance that looks right.
        opening_balance=None,
        closing_balance=closing,
        transactions=transactions,
        warnings=dedupe(warnings),
    )
