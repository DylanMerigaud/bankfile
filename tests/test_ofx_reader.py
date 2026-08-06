"""Every documented deviation in the corpus, read end to end.

This is the file where the corpus stops being documentation. Each fixture under `corpus/banks/`
is a real deviation with a measured baseline in `corpus/measurements/2026-08-05.json`, and the
baseline is not flattering to the incumbents: `ofxparse` 0.21 raises on six of these eighteen
files and silently returns zero headers on two more, `ofxtools` 1.1.1 raises on six.

The bar here is therefore not "it works". The bar is: none of the eighteen raises, and the
fields those two parsers lose come out.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from bankfile.model import Statement
from bankfile.ofx.reader import read_ofx

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "banks"
MEASUREMENTS = (
    Path(__file__).resolve().parent.parent / "corpus" / "measurements" / "2026-08-05.json"
)
FIXTURES = sorted(p for p in CORPUS.rglob("*") if p.is_file() and p.suffix != ".md")


def read(name: str) -> Statement:
    path = CORPUS / name
    return read_ofx(path.read_bytes(), path=str(path))


def test_the_corpus_is_actually_there() -> None:
    """A parametrised test over an empty list passes and proves nothing."""
    assert len(FIXTURES) >= 18


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: str(p.relative_to(CORPUS)))
def test_no_documented_deviation_raises(fixture: Path) -> None:
    """Section 0 of the reading rules: a file that can be read is never rejected over one
    field. Every one of these files broke at least one existing parser."""
    statement = read_ofx(fixture.read_bytes(), path=str(fixture))
    assert statement.source.format == "OFX"
    assert statement.source.encoding


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: str(p.relative_to(CORPUS)))
def test_every_documented_deviation_still_yields_its_transaction(fixture: Path) -> None:
    """Not raising is not enough: a parser that returns an empty statement has not read the
    file, it has only failed quietly, which the corpus calls the worse outcome."""
    statement = read_ofx(fixture.read_bytes(), path=str(fixture))
    assert len(statement.transactions) == 1
    transaction = statement.transactions[0]
    assert transaction.amount is not None
    assert transaction.date is not None


def test_we_do_better_than_both_existing_parsers_on_the_files_they_reject() -> None:
    """The measured claim of this project, asserted rather than told.

    If a future change starts raising on one of these, this test names it. The measurement file
    is read rather than hard coded so that replacing it with a newer one re-aims the test at
    whatever those parsers do then.
    """
    measured = json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
    rejected_by_someone = [
        name
        for name, results in measured.items()
        if not results["ofxparse_0_21_text_mode"]["ok"] or not results["ofxtools_1_1_1"]["ok"]
    ]
    assert len(rejected_by_someone) >= 10, "the baseline should be far from clean"
    for name in rejected_by_someone:
        statement = read(name)
        assert len(statement.transactions) == 1, f"{name} came back empty"


def test_the_headers_survive_a_blank_first_line() -> None:
    """`ofxparse` returns ZERO headers on these two files instead of nine, and raises nothing
    at all. The declared encoding disappears and the file breaks much later, far from the
    cause. This assertion is the reason the project exists, so it is explicit."""
    for name in (
        "chase/blank-line-before-header-none-after.qfx",
        "unnamed-bank/blank-line-before-header.ofx",
    ):
        statement = read(name)
        assert statement.currency == "USD", name
        assert statement.transactions[0].counterparty_name == "ANON MERCHANT", name


def test_the_cheque_number_comes_out_under_both_spellings() -> None:
    """`CHECKNUM` and `CHKNUM` are the same field at two different banks. `ofxparse` 0.21 knows
    one of them, so on the other it returns an empty string and the number is gone with no
    warning: a silent loss, which is worse than a crash."""
    assert read("lcl/check-without-payee.ofx").transactions[0].check_number == "1090381"
    assert (
        read("unnamed-bank/chknum-instead-of-checknum.ofx").transactions[0].check_number == "1932"
    )


def test_vendor_tags_do_not_shift_the_standard_fields_after_them() -> None:
    """The whole point of the `tags-outside-spec` case: an Australian file puts `VALUEDATE`,
    `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL` between the standard fields."""
    transaction = read("unnamed-bank/tags-outside-spec.ofx").transactions[0]
    assert transaction.counterparty_name == "ANON MERCHANT"
    assert transaction.purpose == "ANON MEMO"
    # Kept, not dropped: a caller who needs them can still find them.
    assert transaction.raw["VALUEDATE"] == "20260115"
    assert transaction.raw["ACCTBAL"] == "-400.52"


def test_an_empty_tag_means_absent_and_never_an_empty_string() -> None:
    """Reading rules, section 4. `ofxparse` raises `IndexError` on this file and `ofxtools`
    rejects it outright, so the entry is lost by both."""
    statement = read("unnamed-bank/empty-tags-curdef-fitid-name.ofx")
    transaction = statement.transactions[0]
    assert transaction.counterparty_name is None
    assert transaction.bank_reference is None
    # No currency anywhere in the file, so none is invented, and the report says so.
    assert transaction.currency is None
    assert any(w.field == "CURDEF" for w in statement.warnings)


def test_a_mixed_case_transaction_type_is_the_same_type() -> None:
    """`Credit` and `CREDIT` are one value. `ofxtools` rejects the file over the case alone."""
    assert read("unnamed-bank/mixed-case-trntype.ofx").transactions[0].type_code == "CREDIT"


def test_the_ofx_2_xml_document_reads_like_any_other() -> None:
    """No key:value header block at all: the encoding lives in the XML declaration, which
    `ofxparse` never looks at, so it defaults to ASCII and dies on the first accented byte."""
    statement = read("unnamed-bank/xml-declaration-ofx-2.ofx")
    assert statement.account == "0000123456"
    assert statement.transactions[0].counterparty_name == "ANON ÉNERGIE"


def test_a_comma_decimal_amount_is_not_off_by_a_factor_of_a_hundred() -> None:
    """The failure this project cares about most. `2000,00` is two thousand, not two."""
    assert read("unnamed-bank/amount-comma-decimal.ofx").transactions[0].amount == Decimal(
        "-2000.00"
    )
    assert read("unnamed-bank/amount-plus-sign-and-space.ofx").transactions[0].amount == Decimal(
        "1006.60"
    )
