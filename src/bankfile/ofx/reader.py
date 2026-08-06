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
ACCOUNT_FROM_TAGS = ("BANKACCTFROM", "CCACCTFROM")
ACCOUNT_TO_TAGS = ("BANKACCTTO", "CCACCTTO")


def _first(node: Node, tags: tuple[str, ...]) -> Node | None:
    for tag in tags:
        found = node.find(tag)
        if found is not None:
            return found
    return None


def _text(node: Node, *tags: str) -> str | None:
    """First non-empty value among several spellings of the same field.

    The several spellings are not hypothetical. `CHECKNUM` and `CHKNUM` are the same field at
    two different banks, attested in ofxparse PR #173, and a reader that knows only one of them
    drops a cheque number without a word. That is the failure mode the corpus calls worse than
    a crash.
    """
    for tag in tags:
        value = node.text(tag)
        if value:
            return value
    return None


def _transaction_currency(node: Node, default: str | None) -> str | None:
    """`CURRENCY` on a transaction overrides the statement default, per OFX."""
    currency = node.find("CURRENCY")
    if currency is not None:
        symbol = currency.text("CURSYM")
        if symbol:
            return symbol
    return default


def _raw_fields(node: Node) -> dict[str, str | None]:
    """Every direct child, known or not.

    Keeping the unknown ones is the whole point of the `tags-outside-spec` case: a real
    Australian file carries `VALUEDATE`, `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL` inside a
    transaction, and both existing parsers drop them in silence.
    """
    return {child.tag: child.value for child in node.children}


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
                value=str(_raw_fields(node)),
                message=(
                    f"transaction dropped, it has no {', '.join(missing)}. Its raw fields are "
                    f"kept in this warning: a line without one of these cannot be reconciled, "
                    f"and filling one in would invent a figure."
                ),
            )
        )
        return None

    booking_date = None
    booking_raw = _text(node, "DTAVAIL", "DTUSER")
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
    payee = node.find("PAYEE")
    return Transaction(
        date=date,
        amount=amount,
        currency=currency,
        raw=_raw_fields(node),
        booking_date=booking_date,
        counterparty_name=_text(node, "NAME") or (payee.text("NAME") if payee else None),
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

    statements = [node for tag in STATEMENT_TAGS for node in root.find_all(tag)]
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
    currency = _text(statement, "CURDEF")
    closing: Decimal | None = None
    ledger = statement.find("LEDGERBAL")
    if ledger is not None:
        balance_raw = ledger.text("BALAMT")
        if balance_raw:
            closing, balance_warnings = parse_amount(balance_raw, field="BALAMT")
            warnings.extend(balance_warnings)

    transactions = []
    for node in statement.find_all("STMTTRN"):
        transaction = _read_transaction(node, default_currency=currency, warnings=warnings)
        if transaction is not None:
            transactions.append(transaction)

    return Statement(
        source=Source(format="OFX", path=path, encoding=header.encoding),
        account=account_node.text("ACCTID") if account_node else None,
        currency=currency,
        # OFX 1.x has LEDGERBAL and AVAILBAL and no opening balance element at all. We could
        # subtract the transactions from the closing balance; we do not, because on a filtered
        # window of transactions that arithmetic produces a wrong balance that looks right.
        opening_balance=None,
        closing_balance=closing,
        transactions=transactions,
        warnings=dedupe(warnings),
    )
