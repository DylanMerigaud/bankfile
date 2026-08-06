"""Sections 3 (Amounts) and 5 (Dates) of `corpus/reading-rules.md`, checked against real bytes.

Every value that the corpus holds as a file is READ FROM THAT FILE here, never retyped. A
fixture edited by hand then breaks this suite instead of quietly leaving it to test a string no
bank ever shipped, which is the failure mode that makes a parser suite look green while the
format drifts underneath it. The handful of literals left are the forms attested in a note or in
`corpus/fixtures.json` rather than in a fixture, and each one names its source above the test.
"""

from __future__ import annotations

import datetime
import itertools
import re
from decimal import Decimal
from pathlib import Path

import pytest

from bankfile.normalize import parse_amount, parse_date

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def decode_any(path: Path) -> str:
    """Decode a fixture with the ONE codec that maps all 256 byte values.

    Not cp1252, despite what is the obvious choice here and what `reading-rules.md` says about
    it: Python's cp1252 codec leaves 0x81, 0x8D, 0x8F, 0x90 and 0x9D undefined and raises
    `UnicodeDecodeError` on them, and `banks/unnamed-bank/character-outside-latin1.ofx` carries
    a 0x8D. iso-8859-1 is the only total one. Amounts and dates are ASCII in every fixture, so
    the codec cannot change the digits this file reads; it only decides whether the sweep below
    can open every fixture or blows up on one.
    """
    return path.read_bytes().decode("iso-8859-1")


def tag_values(fixture: str, tag: str) -> list[str]:
    """Pull one tag's raw text straight out of a corpus file, without the OFX reader.

    These tests judge the value rules alone. Routing them through the SGML reader would make
    them fail for reasons owned by another module, and a red test that accuses the wrong file
    costs more than the coupling saves.
    """
    pattern = re.compile(rf"<{re.escape(tag)}>([^<\r\n]*)")
    return [match.group(1) for match in pattern.finditer(decode_any(CORPUS / fixture))]


# --------------------------------------------------------------------------------------------
# The whole corpus, swept
# --------------------------------------------------------------------------------------------

# Every amount and every date the corpus actually contains, and what these two readers make of
# it. Written from the bank notes, not from a run: `00000000` is null with a warning because
# `zero-date.md` says the date is absent, `010126` is 1 January 2026 with a warning because
# `dtstart-ddmmyy.md` says the reporter read `%d%m%y`, `-2000,00` is minus two thousand because
# all three measured parsers agree on it, `+1 006,60` is 1006.60 with no warning because the
# group after its comma is two digits and `amount-plus-sign-and-space.md` says so in as many
# words. The tests below examine five fixtures closely; this table is all nineteen, and
# it is what turns "a value moved" into a red suite instead of a silent change in an export.
CORPUS_READINGS: dict[tuple[str, str], tuple[str | None, int]] = {
    ("ACCTBAL", "-400.52"): ("-400.52", 0),
    ("BALAMT", "2000,00"): ("2000.00", 0),
    ("BALAMT", "90.00"): ("90.00", 0),
    ("DTASOF", "00000000"): (None, 1),
    ("DTASOF", "20260131"): ("2026-01-31", 0),
    ("DTEND", "20260131"): ("2026-01-31", 0),
    ("DTPOSTED", "20260115"): ("2026-01-15", 0),
    ("DTSERVER", "20260115"): ("2026-01-15", 0),
    ("DTSTART", "010126"): ("2026-01-01", 1),
    ("DTSTART", "20260101"): ("2026-01-01", 0),
    ("TRNAMT", "+1 006,60"): ("1006.60", 0),
    ("TRNAMT", "-10.00"): ("-10.00", 0),
    ("TRNAMT", "-2000,00"): ("-2000.00", 0),
    ("VALUEDATE", "20260115"): ("2026-01-15", 0),
}

# A tag is an amount or a date by the shape of its NAME, so a fixture that arrives tomorrow with
# a tag nobody listed here is still swept. `VALUEDATE` and `ACCTBAL`, which no OFX spec defines,
# are picked up by exactly this rule.
AMOUNT_SUFFIXES = ("AMT", "BAL")
DATE_PREFIX = "DT"
DATE_SUFFIX = "DATE"

TAG_WITH_VALUE = re.compile(r"<([A-Za-z0-9]+)>([^<\r\n]*)")


def corpus_fixtures() -> list[Path]:
    return sorted(path for path in CORPUS.rglob("*") if path.suffix in {".ofx", ".qfx"})


def amount_and_date_tags(path: Path) -> list[tuple[str, str]]:
    """The (tag, raw) pairs in one fixture that these two readers are responsible for."""
    found = []
    for match in TAG_WITH_VALUE.finditer(decode_any(path)):
        tag, raw = match.group(1).upper(), match.group(2).strip()
        # An empty capture is an aggregate opener (`<LEDGERBAL>` on its own line), not a tag
        # holding a value, and section 4 already says an empty tag means absent.
        if not raw:
            continue
        if (
            tag.endswith(AMOUNT_SUFFIXES)
            or tag.startswith(DATE_PREFIX)
            or tag.endswith(DATE_SUFFIX)
        ):
            found.append((tag, raw))
    return found


def test_every_amount_and_date_in_the_corpus_reads_the_way_the_bank_notes_say() -> None:
    """The regression net over all nineteen fixtures at once.

    A parser change that moves any documented value, and a fixture edited by hand, both come out
    here as a diff against the table above instead of as an export nobody re-reads. A value the
    corpus gains later also lands here, unpinned, and has to be decided on rather than absorbed.
    """
    fixtures = corpus_fixtures()
    # Nineteen on 2026-08-05. A glob that silently matches nothing would otherwise make every
    # assertion below vacuously true, which is the way a sweep test rots.
    assert len(fixtures) >= 19

    readings: dict[tuple[str, str], tuple[str | None, int]] = {}
    for path in fixtures:
        pairs = amount_and_date_tags(path)
        assert pairs, f"{path.name} yielded no amount and no date, so it is not being read"
        for tag, raw in pairs:
            if tag.endswith(AMOUNT_SUFFIXES):
                amount, warnings = parse_amount(raw, field=tag)
                reading = None if amount is None else str(amount)
            else:
                date, warnings = parse_date(raw, field=tag)
                reading = None if date is None else date.isoformat()
            # A null is never allowed to be silent, whatever the field.
            assert reading is not None or warnings, (path.name, tag, raw)
            readings[(tag, raw)] = (reading, len(warnings))

    assert readings == CORPUS_READINGS


# --------------------------------------------------------------------------------------------
# Amounts, reading rules section 3
# --------------------------------------------------------------------------------------------


def test_a_comma_decimal_reads_as_two_thousand() -> None:
    """`corpus/banks/unnamed-bank/amount-comma-decimal.md`: the comma is the decimal separator,
    and all three measured parsers agree the value is two thousand."""
    (trnamt,) = tag_values("banks/unnamed-bank/amount-comma-decimal.ofx", "TRNAMT")
    assert trnamt == "-2000,00"

    value, warnings = parse_amount(trnamt, field="TRNAMT")

    assert value == Decimal("-2000.00")
    assert warnings == []


def test_the_separator_convention_is_decided_per_value_never_per_file() -> None:
    """The same file carries `2000,00` and `90.00`. An implementation that sniffs the first
    amount and applies that convention to the rest returns a wrong figure for the other one,
    which is the one failure this project exists to prevent."""
    ledger, available = tag_values("banks/unnamed-bank/amount-comma-decimal.ofx", "BALAMT")
    assert (ledger, available) == ("2000,00", "90.00")

    assert parse_amount(ledger, field="BALAMT") == (Decimal("2000.00"), [])
    assert parse_amount(available, field="BALAMT") == (Decimal("90.00"), [])


def test_a_leading_plus_and_a_space_grouping_are_stripped() -> None:
    """`corpus/banks/unnamed-bank/amount-plus-sign-and-space.md`: three departures stacked in
    one field, and the group after the comma is two digits so nothing is in doubt."""
    (trnamt,) = tag_values("banks/unnamed-bank/amount-plus-sign-and-space.ofx", "TRNAMT")
    assert trnamt == "+1 006,60"

    value, warnings = parse_amount(trnamt, field="TRNAMT")

    assert value == Decimal("1006.60")
    assert warnings == []


def test_a_plain_dot_amount_is_left_alone() -> None:
    (trnamt,) = tag_values("template/ofx-1.0.2.ofx", "TRNAMT")
    assert trnamt == "-10.00"

    assert parse_amount(trnamt, field="TRNAMT") == (Decimal("-10.00"), [])


# `+1,006.60` is quoted for this case in `corpus/fixtures.json`; the fixture on disk carries the
# space-and-comma form instead, so this one stays a literal.
def test_when_both_separators_are_present_the_last_one_is_the_decimal_one() -> None:
    assert parse_amount("+1,006.60", field="TRNAMT") == (Decimal("1006.60"), [])
    assert parse_amount("1.006,60", field="TRNAMT") == (Decimal("1006.60"), [])
    assert parse_amount("-1.234.567,89", field="TRNAMT") == (Decimal("-1234567.89"), [])
    assert parse_amount("-1,234,567.89", field="TRNAMT") == (Decimal("-1234567.89"), [])


# `1 025,53` is the form the ofxparse patch names in its own comment, quoted in
# `corpus/banks/unnamed-bank/amount-plus-sign-and-space.md`. The note asks for U+00A0 and U+202F
# explicitly: the corpus fixture only exercises the ASCII space.
# Written as escapes and not as the characters themselves: a literal U+00A0 in a source file
# is invisible, which is exactly how it survives all the way into an amount field.
@pytest.mark.parametrize("space", [" ", "\u00a0", "\u202f"])
def test_a_thousands_space_is_stripped_whichever_space_character_it_is(space: str) -> None:
    value, warnings = parse_amount(f"1{space}025,53", field="TRNAMT")

    assert value == Decimal("1025.53")
    assert warnings == []


# `10000,50`: named by the module contract, not present in any corpus file.
def test_a_comma_followed_by_two_digits_is_not_ambiguous() -> None:
    assert parse_amount("10000,50", field="TRNAMT") == (Decimal("10000.50"), [])


def test_a_comma_followed_by_exactly_three_digits_is_ambiguous_and_says_so() -> None:
    """The hardest case in section 3. `2,000` is two under the decimal reading and two thousand
    under the thousands reading. The rule keeps the decimal reading, because the OFX amount type
    has no thousands separator, and the ambiguity travels with the value instead of being
    swallowed."""
    value, warnings = parse_amount("2,000", field="TRNAMT")

    assert value == Decimal("2.000")
    assert value == Decimal("2")
    assert value != Decimal("2000")

    (warning,) = warnings
    assert warning.rule == "amount"
    assert warning.field == "TRNAMT"
    assert warning.value == "2,000"
    assert "ambiguous" in warning.message


def test_a_dot_followed_by_exactly_three_digits_is_read_without_a_warning() -> None:
    """PINNED, AND IT PINS A GAP IN SECTION 3, not a decision this module made.

    Step 4 scopes its ambiguity warning to the comma. A lone dot never reaches it, so `2.000`
    comes back as two with nothing said, while `2,000` comes back as two WITH the warning. The
    two strings carry the same doubt: a European exporter writes `2.000` for two thousand just
    as an American one writes `2,000`, and the reason step 4 gives for keeping the decimal
    reading (the OFX amount type has no thousands separator) argues for the dot exactly as
    loudly. This test asserts the rule as written, so that widening the warning to the dot
    becomes a deliberate amendment to `reading-rules.md` that lands here first, and not a
    silent change of reading in a module the rule does not cover.
    """
    assert parse_amount("2.000", field="TRNAMT") == (Decimal("2.000"), [])
    assert parse_amount("1.234", field="BALAMT") == (Decimal("1.234"), [])

    value, warnings = parse_amount("2,000", field="TRNAMT")
    assert (value, len(warnings)) == (Decimal("2.000"), 1)


def test_the_ambiguity_survives_a_sign_and_a_space() -> None:
    """The ambiguity test runs on the cleaned string, so a form that reaches it through the
    other steps of the rule is reported the same way."""
    value, warnings = parse_amount("+2 000", field="TRNAMT")
    assert value == Decimal("2000")
    assert warnings == []

    value, warnings = parse_amount("-2,000", field="TRNAMT")
    assert value == Decimal("-2.000")
    assert [warning.rule for warning in warnings] == ["amount"]


def test_an_empty_amount_stays_null_and_warns() -> None:
    """A tag present but empty means absent (section 4), and absent is not zero: a transaction
    silently worth nothing reconciles to a wrong total."""
    value, warnings = parse_amount("", field="TRNAMT")

    assert value is None
    (warning,) = warnings
    assert warning.rule == "amount"
    assert warning.field == "TRNAMT"
    assert warning.value == ""
    assert warning.message.startswith("amount is empty")


@pytest.mark.parametrize("raw", ["+", " ", "\u00a0", "\u202f", "\t", "+\u202f"])
def test_an_amount_that_holds_no_digit_is_not_reported_as_an_empty_one(raw: str) -> None:
    """The tag was NOT blank, and the report has to say so. A lone `+`, and a non-breaking space
    on its own, both come out of steps 1 and 2 with nothing left; calling them empty would send
    whoever reads the warning looking for a missing tag rather than for the character the bank
    actually shipped, which is invisible in every viewer they will open the file with."""
    value, warnings = parse_amount(raw, field="TRNAMT")

    assert value is None
    (warning,) = warnings
    assert warning.value == raw
    assert "holds no digit" in warning.message
    assert repr(raw) in warning.message


@pytest.mark.parametrize("raw", ["abc", "1.2.3", "1,234,567", "--5", "10.00-", "-", "USD 10.00"])
def test_an_unreadable_amount_stays_null_and_never_guesses(raw: str) -> None:
    value, warnings = parse_amount(raw, field="TRNAMT")

    assert value is None
    (warning,) = warnings
    assert warning.rule == "amount"
    assert warning.value == raw


def test_what_decimal_would_have_accepted_and_a_bank_never_writes_is_refused() -> None:
    """Python's `Decimal` is more permissive than the OFX amount type, in three ways that all
    produce a plausible number out of a string no exporter wrote. Each of them would enter a
    reconciliation and never be looked at again, so the reading is gated on an explicit grammar
    rather than on whatever `Decimal` happens to swallow."""
    assert Decimal("1_000") == Decimal("1000")
    assert Decimal("1e5") == Decimal("100000")
    assert Decimal("٣") == Decimal("3")
    assert Decimal("NaN").is_nan()

    for raw in ("1_000", "1e5", "٣", "NaN", "Infinity", "-inf"):
        value, warnings = parse_amount(raw, field="TRNAMT")
        assert value is None, raw
        assert [warning.rule for warning in warnings] == ["amount"], raw


def test_the_amount_is_a_decimal_and_keeps_the_scale_the_file_wrote() -> None:
    """Two cents written `0.10` and `0.20` add up to exactly `0.30`, which is the whole reason
    the model refuses floats. The scale is kept as well: `10,00` is not the same claim as `10`
    when you are comparing against a bank total."""
    ten_cents, _ = parse_amount("0,10", field="TRNAMT")
    twenty_cents, _ = parse_amount("0,20", field="TRNAMT")
    assert ten_cents is not None
    assert twenty_cents is not None
    assert isinstance(ten_cents, Decimal)
    assert ten_cents + twenty_cents == Decimal("0.30")
    assert str(parse_amount("10,00", field="TRNAMT")[0]) == "10.00"


# --------------------------------------------------------------------------------------------
# Dates, reading rules section 5
# --------------------------------------------------------------------------------------------


def test_eight_digits_read_as_year_month_day() -> None:
    (dtposted,) = tag_values("template/ofx-1.0.2.ofx", "DTPOSTED")
    assert dtposted == "20260115"

    assert parse_date(dtposted, field="DTPOSTED") == (datetime.date(2026, 1, 15), [])


# The `YYYYMMDDHHMMSS[offset:zone]` form belongs to the OFX date type. No corpus fixture carries
# it, so the value below is written from the format and not read from a bank file.
@pytest.mark.parametrize(
    "raw",
    ["20260115120000[-5:EST]", "20260115120000.000[-5:EST]", "20260115120000", "20260115[0:GMT]"],
)
def test_what_follows_the_eighth_digit_is_time_and_zone_and_does_not_move_the_day(
    raw: str,
) -> None:
    """No warning here on purpose. Nearly every OFX date carries a zone, so warning on each one
    would bury the warnings that mean something under one per transaction."""
    assert parse_date(raw, field="DTPOSTED") == (datetime.date(2026, 1, 15), [])


def test_all_zeros_means_the_date_is_absent() -> None:
    """`corpus/banks/unnamed-bank/zero-date.md`: the bank has no as-of date and writes a filler.
    `ofxtools` 1.1.1 refuses the whole document over this one field. We keep the statement, the
    date stays null, and the raw value travels in the warning: never the epoch, never today."""
    zero, real = tag_values("banks/unnamed-bank/zero-date.ofx", "DTASOF")
    assert (zero, real) == ("00000000", "20260131")

    value, warnings = parse_date(zero, field="DTASOF")

    assert value is None
    assert value != datetime.date(1970, 1, 1)
    (warning,) = warnings
    assert warning.rule == "date"
    assert warning.field == "DTASOF"
    assert warning.value == "00000000"

    assert parse_date(real, field="DTASOF") == (datetime.date(2026, 1, 31), [])


def test_six_digits_are_read_as_day_month_year_and_warn() -> None:
    """`corpus/banks/hsbc-brasil/dtstart-ddmmyy.md`: `DDMMYY` is attested once, `YYMMDD` never,
    so the value is read and the doubt is reported. The issue's own fix guessed silently, which
    is the half of it this corpus refuses."""
    (dtstart,) = tag_values("banks/hsbc-brasil/dtstart-ddmmyy.ofx", "DTSTART")
    (dtend,) = tag_values("banks/hsbc-brasil/dtstart-ddmmyy.ofx", "DTEND")
    assert (dtstart, dtend) == ("010126", "20260131")

    value, warnings = parse_date(dtstart, field="DTSTART")

    assert value == datetime.date(2026, 1, 1)
    (warning,) = warnings
    assert warning.rule == "date"
    assert warning.field == "DTSTART"
    assert warning.value == "010126"
    assert "DDMMYY" in warning.message

    # The two bounds of the same period, in two formats, inside one aggregate.
    assert parse_date(dtend, field="DTEND") == (datetime.date(2026, 1, 31), [])


def test_a_two_digit_year_lands_where_strptime_would_put_it() -> None:
    """The century pivot is the POSIX one that `strptime('%y')` applies, which is what the
    reporter's own patch used. Picking a different pivot would silently disagree with the source
    of the rule by a hundred years."""
    assert parse_date("311268", field="DTSTART")[0] == datetime.date(2068, 12, 31)
    assert parse_date("010169", field="DTSTART")[0] == datetime.date(1969, 1, 1)


def test_an_empty_date_stays_null_and_warns() -> None:
    value, warnings = parse_date("", field="DTASOF")

    assert value is None
    (warning,) = warnings
    assert warning.rule == "date"
    assert warning.field == "DTASOF"
    assert warning.value == ""


@pytest.mark.parametrize("raw", ["2026", "2026011", "26/01/15", "not a date", "-20260115", "٣"])
def test_an_unexpected_date_stays_null_and_warns(raw: str) -> None:
    value, warnings = parse_date(raw, field="DTSTART")

    assert value is None
    (warning,) = warnings
    assert warning.rule == "date"
    assert warning.value == raw


@pytest.mark.parametrize("raw", ["20261301", "20260230", "00000001", "20260100", "999999"])
def test_a_value_that_is_not_a_calendar_date_stays_null_and_warns(raw: str) -> None:
    """Month 13 and 30 February are digits in the right shape and no date at all. Nothing here
    is rounded into the nearest real day: the field stays null and says why."""
    value, warnings = parse_date(raw, field="DTPOSTED")

    assert value is None
    (warning,) = warnings
    assert warning.rule == "date"
    assert warning.value == raw


@pytest.mark.parametrize("raw", ["", " ", "\x00", "-", "+", ",", ".", "٣", "0" * 40, "9" * 40])
def test_neither_reader_ever_raises(raw: str) -> None:
    """The failure doctrine, mechanically: a single field never costs the whole file. Whatever
    comes in, the answer is a value or a null plus a warning, never an exception."""
    amount, amount_warnings = parse_amount(raw, field="TRNAMT")
    date, date_warnings = parse_date(raw, field="DTPOSTED")

    assert amount is None or isinstance(amount, Decimal)
    assert date is None or isinstance(date, datetime.date)
    # A null answer is never silent: something unreadable always leaves a trace behind it.
    assert amount is not None or amount_warnings
    assert date is not None or date_warnings


# Every character that decides a branch in either reader, plus the two invisible spaces and one
# non-ASCII digit. Escapes rather than the characters themselves: a literal U+00A0 in a source
# file looks exactly like a space, which is how it survives into an amount field in the first
# place. Kept small on purpose, because the point below is exhaustiveness over the SHAPES these
# characters can form, not a long alphabet.
BRANCH_ALPHABET = ("0", "9", "+", "-", ".", ",", " ", "\u00a0", "[", "\u0663")


def test_neither_reader_raises_on_any_arrangement_of_the_characters_that_matter() -> None:
    """The same doctrine, but proved over every string of length four the alphabet can build,
    not over ten strings a human thought of.

    Ten hand-picked inputs prove that ten inputs are safe. The failure this guards against is a
    combination nobody pictured: a sign after a separator, a comma with nothing behind it, two
    dots around one digit, a bracket where the time should start. There are 11110 of those here
    and they run in well under a second, so there is no reason to be sampling instead.
    """
    checked = 0
    for length in range(5):
        for characters in itertools.product(BRANCH_ALPHABET, repeat=length):
            raw = "".join(characters)
            amount, amount_warnings = parse_amount(raw, field="TRNAMT")
            date, date_warnings = parse_date(raw, field="DTPOSTED")
            # Not an exception, and never a null that says nothing. Those are the only two ways
            # this module can cost a caller data it could otherwise have read.
            assert amount is not None or amount_warnings, raw
            assert date is not None or date_warnings, raw
            # And a warning is only worth the name if it can be acted on. Section 0 asks for the
            # tag, the raw value and the rule that fired; an entry with a blank message is a line
            # in the report that sends its reader back to the file with nothing to look for.
            for warning, rule, tag in (
                *((entry, "amount", "TRNAMT") for entry in amount_warnings),
                *((entry, "date", "DTPOSTED") for entry in date_warnings),
            ):
                assert (warning.rule, warning.field, warning.value) == (rule, tag, raw)
                assert warning.message.strip(), raw
            checked += 1

    assert checked == sum(len(BRANCH_ALPHABET) ** length for length in range(5))
