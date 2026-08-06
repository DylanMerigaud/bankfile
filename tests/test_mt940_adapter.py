"""What 54 real MT940 files from 16 banks require of the adapter.

The parametrised walk over `tests/fixtures/mt940/` is the test that matters. Five hand-picked
files prove five mappings; a walk over the whole directory proves that no bank in the corpus
raises, and it is the only thing that keeps proving it when the next bank lands.

The expectations are read from the FILES, never from the library: a `:61:` line says
`D25,03`, so the transaction owes -25.03, whatever `mt940` chose to call its fields. A test
written from the parser's output only ever asserts that the parser has not changed.
"""

from __future__ import annotations

import datetime
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from bankfile.model import Statement
from bankfile.mt940_adapter import read_mt940

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mt940"
CORPUS = sorted(p for p in FIXTURES.rglob("*") if p.suffix in {".sta", ".txt"})


def load(name: str) -> Statement:
    """Read a fixture the way a caller would: bytes in, statement out."""
    return read_mt940((FIXTURES / name).read_bytes(), path=name)


@pytest.mark.parametrize("fixture", CORPUS, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_every_real_file_yields_transactions_that_can_be_reconciled(fixture: Path) -> None:
    """The done criterion of this phase: 54 files, 16 banks, no exception, and every entry
    carrying the three fields a reconciliation cannot work without."""
    result = read_mt940(fixture.read_bytes(), path=str(fixture))

    assert result.source.format == "MT940"
    assert result.source.path == str(fixture)
    for transaction in result.transactions:
        assert isinstance(transaction.date, datetime.date)
        assert isinstance(transaction.amount, Decimal)
        # Nullable since the corpus asked for it (an empty CURDEF is a real file). Null means
        # "the file does not say", and it must stay distinct from a value.
        assert transaction.currency is None or (
            len(transaction.currency) == 3 and transaction.currency.isalpha()
        )
        # `raw` is a promise to the caller, so it is verified as one.
        json.dumps(transaction.raw)

    # And null is never silent, on any file in the corpus: that is the whole difference between
    # a tolerant reader and a reader that loses data quietly.
    if any(transaction.currency is None for transaction in result.transactions):
        assert [w for w in result.warnings if w.field == "currency"]


@pytest.mark.parametrize("fixture", CORPUS, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_every_statement_line_in_the_file_becomes_a_transaction(fixture: Path) -> None:
    """`:61:` is the statement line. One per transaction, so the count is derivable from the
    file itself and no entry can go missing without this failing.

    The optional newline after the colon is part of the tag syntax: a bank that wraps a line
    there (Sparkasse does) still opens a statement line.
    """
    text = fixture.read_bytes().decode("iso-8859-1")
    expected = len(re.findall(r"(?m)^:\n?61:", text))

    assert len(read_mt940(fixture.read_bytes()).transactions) == expected


def test_the_corpus_covers_more_than_twenty_files_from_different_banks() -> None:
    assert len(CORPUS) >= 20
    assert len({p.parent.name for p in CORPUS}) >= 8


def test_the_ing_statement_maps_onto_the_model() -> None:
    """jejik/ing.sta, read line by line: `:25:` is the account, `:60F:`/`:62F:` the balances,
    seven `:61:` lines the entries."""
    result = load("jejik/ing.sta")

    assert result.account == "0001234567"
    assert result.currency == "EUR"
    assert result.opening_balance == Decimal("0.00")
    assert result.closing_balance == Decimal("3.47")
    assert len(result.transactions) == 7

    first = result.transactions[0]
    assert first.date == datetime.date(2010, 7, 22)
    # `:61:100722D25,03NTRFNONREF`: D is a debit, so the amount is negative.
    assert first.amount == Decimal("-25.03")
    assert first.currency == "EUR"
    # `NTRF` is the SWIFT code in the file; `TRANSFER` is our shared vocabulary. The original
    # is never destroyed, it stays in `raw`, which is what lets a caller disagree with us.
    assert first.type_code == "TRANSFER"
    assert first.raw["id"] == "NTRF"
    assert first.reference == "NONREF"
    assert first.purpose is not None
    assert "RC AFREKENING BETALINGSVERKEER" in first.purpose
    assert "BETREFT REKENING 0000000" in first.purpose
    # MT940 has no cheque number. Inventing one from another field is how a mapping lies.
    assert first.check_number is None

    last = result.transactions[-1]
    assert last.date == datetime.date(2010, 7, 23)
    # `:61:100723C1,00NTRFNONREF`: C is a credit, so the amount is positive.
    assert last.amount == Decimal("1.00")


def test_the_entry_date_becomes_the_booking_date() -> None:
    """jejik/abnamro.sta, `:61:1105240524D9,N192NONREF`: value date 24-05-2011, entry date
    24-05. The two are different fields and a reconciliation uses both."""
    result = load("jejik/abnamro.sta")

    first = result.transactions[0]
    assert first.date == datetime.date(2011, 5, 24)
    assert first.booking_date == datetime.date(2011, 5, 24)
    assert first.amount == Decimal("-9")


def test_an_entry_date_of_spaces_leaves_the_booking_date_empty() -> None:
    """citi/mt940.txt, `:61:240312    DD212,39NMSCNONREF//`: four spaces where the entry date
    belongs. Absent, not zero, and above all not the value date copied over."""
    result = load("citi/mt940.txt")

    assert result.currency == "USD"
    assert result.opening_balance == Decimal("17376.67")
    assert len(result.transactions) == 5
    assert result.transactions[0].date == datetime.date(2024, 3, 12)
    assert result.transactions[0].booking_date is None
    assert result.transactions[0].amount == Decimal("-212.39")


def test_the_german_structured_field_fills_the_counterparty_and_the_reference() -> None:
    """self-provided/gv_codes.sta. The `:86:` field carries `?20`..`?32` subfields: `?32` is
    the applicant name, `EREF+` the end to end reference, and the `:61:` line has no customer
    reference, so the reference falls back to that end to end reference.
    """
    result = load("self-provided/gv_codes.sta")

    first = result.transactions[0]
    # `835` is the German GVC, a national code with no cross-format meaning: it stays in `raw`.
    # The SWIFT code on this line is `NMSC`, "miscellaneous", which maps to OTHER.
    assert first.type_code == "OTHER"
    assert first.raw["transaction_code"] == "835"
    assert first.raw["id"] == "NMSC"
    assert first.counterparty_name is not None
    assert "PayPal (Europe)" in first.counterparty_name
    assert first.reference is not None
    assert "1234567890123 PAYPAL" in first.reference
    assert first.purpose is not None
    assert "SPOTIFY" in first.purpose


def test_the_raw_dictionary_keeps_every_field_and_stays_json_safe() -> None:
    """The parser hands back `Decimal`, `date` and its own `Amount`. None of the three
    survives `json.dumps`, and dropping them would mean re-parsing the file to answer the
    first question the schema does not cover."""
    result = load("self-provided/gv_codes.sta")

    raw = result.transactions[0].raw
    assert raw["date"] == "2017-09-14"
    assert raw["amount"] == "-233.15 EUR"
    assert raw["status"] == "D"
    assert json.loads(json.dumps(raw)) == raw


def test_the_balances_span_the_file_and_not_only_its_last_block() -> None:
    """jejik/generic.sta holds two `:20:` blocks for one account: 100,00 opening in the first,
    80,00 closing in the second. Merging the blocks into one collection, which is what the
    parser does by default, reports the SECOND block's opening balance, 90,00: a plausible
    number that no longer matches the entries it is shown next to.
    """
    result = load("jejik/generic.sta")

    assert result.account == "11111111"
    assert result.opening_balance == Decimal("100.00")
    assert result.closing_balance == Decimal("80.00")
    assert len(result.transactions) == 2


def test_a_file_holding_several_accounts_keeps_the_entries_and_drops_the_balances() -> None:
    """jejik/rabobank.sta: four blocks, two accounts (1291.99.348EUR and 1526.89.184EUR).
    One statement cannot carry two accounts, and an opening balance taken from one account
    with a closing balance taken from the other is the wrong but plausible number the failure
    doctrine exists to prevent. The entries are all sound, so they stay.
    """
    result = load("jejik/rabobank.sta")

    assert len(result.transactions) == 5
    assert result.account is None
    assert result.opening_balance is None
    assert result.closing_balance is None
    warnings = [w for w in result.warnings if w.field == "account_identification"]
    assert len(warnings) == 1
    assert warnings[0].rule == "tag"
    assert warnings[0].value is not None
    assert "1291.99.348EUR" in warnings[0].value
    assert "1526.89.184EUR" in warnings[0].value


def test_a_transaction_with_no_currency_anywhere_is_kept_without_one() -> None:
    """self-provided/sparkassen.sta has neither `:60F:` nor a funds code, so nothing in the
    file names a currency. The entry itself is sound, so it is kept with a null currency and a
    warning. Dropping it would lose 30,00 of movement over a missing label, and filling in a
    placeholder would make "we could not read it" indistinguishable from a value the file
    actually stated.
    """
    result = load("self-provided/sparkassen.sta")

    assert len(result.transactions) == 1
    first = result.transactions[0]
    assert first.currency is None
    assert first.amount == Decimal("30.00")
    assert first.date == datetime.date(2018, 11, 26)

    warnings = [w for w in result.warnings if w.field == "currency"]
    assert len(warnings) == 1
    assert warnings[0].rule == "tag"
    assert warnings[0].value is None


def test_a_transaction_takes_the_currency_of_the_statement_balance() -> None:
    """The `:61:` line never repeats the currency: it is declared once, on `:60F:`. So the
    balance is where the currency of every entry comes from."""
    result = load("jejik/postfinance.sta")

    assert result.currency == "CHF"
    assert {t.currency for t in result.transactions} == {"CHF"}


def test_the_asnb_dialect_is_read_by_falling_back_to_its_tag() -> None:
    """ASNB puts a full IBAN in the customer reference of `:61:`, which the standard tag caps
    at 16 characters: the line does not match at all and the parser raises. The library ships
    a tag for that bank, so the reader retries with it instead of losing the file, and says
    which dialect it ended up using.
    """
    result = load("ASNB/mt940.txt")

    assert result.account == "NL81ASNB9999999999"
    assert result.currency == "EUR"
    assert result.opening_balance == Decimal("444.29")
    assert result.closing_balance == Decimal("501.23")
    assert len(result.transactions) == 8
    assert result.transactions[0].amount == Decimal("-65.00")
    assert result.transactions[0].reference == "NL47INGB9999999999"
    assert [w.rule for w in result.warnings if "ASNB" in w.message] == ["tag"]


def test_a_file_that_is_not_utf8_is_read_anyway_and_names_the_codec() -> None:
    """self-provided/raiffeisen-cmi.sta is a DOS code page export: byte 0xa0 is not valid
    utf-8 and byte 0x81 is not assigned in cp1252, so both raise. iso-8859-1 cannot fail on
    any byte, and the codec that was finally used is reported rather than assumed.
    """
    result = load("self-provided/raiffeisen-cmi.sta")

    assert result.source.encoding == "iso-8859-1"
    assert [w.rule for w in result.warnings if w.rule == "encoding"] == ["encoding"]
    assert result.currency == "HUF"
    assert len(result.transactions) == 7


def test_a_utf8_file_is_read_as_utf8_and_says_nothing() -> None:
    result = load("jejik/ing.sta")

    assert result.source.encoding == "utf-8"
    assert [w for w in result.warnings if w.rule == "encoding"] == []


def test_input_that_is_not_mt940_at_all_yields_an_empty_statement_that_says_so() -> None:
    """Never an exception, never a half-built statement passed off as read. Nothing came out
    of the file, and the report says exactly that."""
    result = read_mt940(b"<OFX>\n<BANKMSGSRSV1>\nthis is not an MT940 file\n</OFX>\n")

    assert result.transactions == []
    assert result.account is None
    assert result.opening_balance is None
    assert [w.rule for w in result.warnings] == ["tag"]
    assert "no MT940 tag was recognised" in result.warnings[0].message


def test_a_block_that_no_dialect_can_read_does_not_cost_the_other_blocks() -> None:
    """The second block dates an entry to month 13. The doctrine only allows failing when
    NOTHING can be read, so the first block's entry survives and the loss is named."""
    data = (
        b":20:GOOD\n:25:11111111\n:60F:C110101EUR100,00\n"
        b":61:110101D10,00N000NONREF\n:86:paid\n:62F:C110201EUR90,00\n\n"
        b":20:BAD\n:25:11111111\n:61:181330D1,00NTRF\n"
    )

    result = read_mt940(data)

    assert len(result.transactions) == 1
    assert result.transactions[0].amount == Decimal("-10.00")
    assert result.opening_balance == Decimal("100.00")
    # Two named losses, not one: the block nobody could read, and the `N000` type code that is
    # outside the mapped vocabulary. Both are "tag" warnings and both have to stay visible.
    assert [w.rule for w in result.warnings] == ["tag", "tag"]
    lost = [w for w in result.warnings if "could not be read" in w.message]
    assert len(lost) == 1
    assert "month" in lost[0].message
    assert any("N000" in (w.value or "") + w.message for w in result.warnings)


def test_the_source_carries_the_path_it_was_given_and_nothing_else() -> None:
    result = read_mt940(b":20:X\n:25:11111111\n:60F:C110101EUR1,00\n")

    assert result.source.path is None
