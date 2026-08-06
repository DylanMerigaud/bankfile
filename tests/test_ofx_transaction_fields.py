"""Three fields of a transaction that coverage called executed and nothing actually checked.

A mutation pass over the reader removed each of these three branches and the whole suite stayed
green: the per-transaction currency override, the counterparty name written inside `PAYEE`, and
the account a transfer went to. Every one of them is a field the corpus files carry and a
caller reads, so losing one is a silent loss, which section 0 of the reading rules calls worse
than a crash.

Each test below fails if its branch is removed. That is the only property that makes them worth
having: a test that passes with the code deleted tests nothing.
"""

from __future__ import annotations

import pytest

from bankfile.ofx.reader import read_ofx

HEADER = (
    "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\n"
    "CHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n<OFX>\n"
    "<BANKMSGSRSV1>\n<STMTTRNRS>\n<STMTRS>\n<CURDEF>EUR\n<BANKACCTFROM>\n<ACCTID>1111\n"
    "</BANKACCTFROM>\n<BANKTRANLIST>\n"
)
FOOTER = "</BANKTRANLIST>\n</STMTRS>\n</STMTTRNRS>\n</BANKMSGSRSV1>\n</OFX>\n"


def one(*inner: str) -> bytes:
    """A statement in EUR carrying a single transaction, plus whatever tags a test needs in it."""
    body = (
        "<STMTTRN>\n<TRNTYPE>XFER\n<DTPOSTED>20260115\n<TRNAMT>-10.00\n<FITID>T1\n"
        + "".join(inner)
        + "</STMTTRN>\n"
    )
    return (HEADER + body + FOOTER).encode()


def test_a_currency_on_the_transaction_overrides_the_statement_default() -> None:
    """OFX lets one entry of a EUR statement settle in another currency, and it says so in
    `CURRENCY`. Ignoring it stamps the statement's currency on an amount that is not in it,
    which is a wrong figure carrying the right number."""
    transaction = read_ofx(
        one("<CURRENCY>\n<CURRATE>1.0857\n<CURSYM>USD\n</CURRENCY>\n")
    ).transactions[0]
    assert transaction.currency == "USD"


def test_a_transaction_with_no_currency_of_its_own_keeps_the_statement_one() -> None:
    """The other side of the same branch: the override must not become a requirement, because
    almost every entry of almost every file has no `CURRENCY` at all."""
    assert read_ofx(one()).transactions[0].currency == "EUR"


def test_an_empty_currency_aggregate_falls_back_instead_of_emptying_the_field() -> None:
    """A `CURRENCY` block whose `CURSYM` is empty says nothing, so the statement default stands.
    Taking the empty value would drop the currency of an entry that had one all along."""
    read = read_ofx(one("<CURRENCY>\n<CURRATE>1.0857\n<CURSYM>\n</CURRENCY>\n"))
    assert read.transactions[0].currency == "EUR"


def test_a_statement_carrying_no_curdef_at_all_invents_none() -> None:
    """`CURDEF` absent, not merely empty. The amount keeps its exact value and no currency is
    guessed from the account number or the bank identifier, because a figure whose meaning was
    invented is the one output this project refuses to produce."""
    without_curdef = HEADER.replace("<CURDEF>EUR\n", "")
    body = "<STMTTRN>\n<DTPOSTED>20260115\n<TRNAMT>-10.00\n<FITID>T1\n</STMTTRN>\n"
    read = read_ofx((without_curdef + body + FOOTER).encode())
    assert read.currency is None
    assert read.transactions[0].currency is None
    assert any(w.field == "CURDEF" for w in read.warnings)


def test_the_counterparty_name_is_read_from_payee_when_there_is_no_flat_name() -> None:
    """A bank writes the counterparty either as a flat `NAME` or as a `PAYEE` aggregate, and
    both are the same fact. `lcl/check-without-payee.ofx` is in the corpus because of the split:
    a reader that knows only the flat spelling returns an unnamed transaction, and an unnamed
    line is a line nobody can reconcile against an invoice."""
    transaction = read_ofx(
        one("<PAYEE>\n<NAME>ANON PAYEE\n<ADDR1>1 ANON STREET\n<CITY>ANONVILLE\n</PAYEE>\n")
    ).transactions[0]
    assert transaction.counterparty_name == "ANON PAYEE"


def test_a_flat_name_wins_over_the_one_inside_payee() -> None:
    """When a file carries both, the flat one is the transaction's own field and the `PAYEE`
    one belongs to an address block. Picking the other way round would change the answer on
    files that name the merchant twice, in two different forms."""
    transaction = read_ofx(
        one("<NAME>ANON MERCHANT\n<PAYEE>\n<NAME>ANON PAYEE\n</PAYEE>\n")
    ).transactions[0]
    assert transaction.counterparty_name == "ANON MERCHANT"


def test_a_transaction_naming_no_counterparty_at_all_stays_null() -> None:
    assert read_ofx(one()).transactions[0].counterparty_name is None


@pytest.mark.parametrize("tag", ["BANKACCTTO", "CCACCTTO"], ids=["bank account", "credit card"])
def test_the_account_a_transfer_went_to_comes_out(tag: str) -> None:
    """A transfer names the account on the other side, in `BANKACCTTO` or in `CCACCTTO` for a
    card. It is the field that turns a line into a reconciled movement between two accounts, and
    dropping it leaves the caller with an amount and no counterparty."""
    transaction = read_ofx(
        one(f"<{tag}>\n<BANKID>000000002\n<ACCTID>2222\n<ACCTTYPE>SAVINGS\n</{tag}>\n")
    ).transactions[0]
    assert transaction.counterparty_account == "2222"


def test_a_transaction_that_names_no_other_account_stays_null() -> None:
    """Null and never an empty string: "the file said nothing" and "the file said nothing much"
    are two different facts, and only one of them is worth investigating."""
    assert read_ofx(one()).transactions[0].counterparty_account is None
