"""Amounts and dates: sections 3 and 5 of `corpus/reading-rules.md`, and nothing else.

This is where a wrong but plausible value would be born. A payee name read badly is visible to
anyone who looks at the statement; an amount read as two instead of two thousand enters a
reconciliation, balances against nothing, and is found weeks later by a human counting by hand.
So the two readers here answer with a value OR with a null and a named warning, never with a
guess, never with a fallback, and never with an exception that would cost the caller the rest of
a file it could otherwise read (the failure doctrine, section 0).

Both take the raw string exactly as the file wrote it and return it in the warning, because a
null field says something is missing while the raw value says what the bank actually sent, which
is what you need to write the next rule.
"""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

from bankfile.model import ReadWarning

# What we accept as an amount ONCE the separators have been normalised. Deliberately narrower
# than what `Decimal()` swallows, and that gap is the point: `Decimal("NaN")` returns a value
# that compares false against every total it meets, `Decimal("1_000")` turns an underscore into
# a thousands separator nobody wrote, `Decimal("1e5")` reads a hundred thousand out of three
# characters, and `Decimal("٣")` reads an Arabic-Indic digit as a 3. Each of those is a
# plausible number produced from a string no bank exporter writes, so each one stays null here.
_AMOUNT = re.compile(r"-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")

# ASCII digits only. `str.isdigit()` would also accept the Arabic-Indic and superscript forms,
# and `int()` would happily turn them into a date nobody wrote.
_LEADING_DIGITS = re.compile(r"[0-9]+")

# The century a two digit year lands in. This is the POSIX pivot that `strptime("%y")` applies,
# and the local patch in ofxparse issue #58, the only source that attests the DDMMYY form, used
# strptime. Choosing another pivot would silently disagree with the source of the rule by a
# hundred years, on the exact case where the rule already says the year is not certain.
_TWO_DIGIT_YEAR_PIVOT = 68


def parse_amount(raw: str, *, field: str) -> tuple[Decimal | None, list[ReadWarning]]:
    """Read a monetary value the way section 3 says, or return null and say why.

    `field` is the tag the value came from, so a warning can name it: a report saying "an amount
    was unreadable" sends you looking through the file, one saying `BALAMT` does not.
    """
    # Spaces first, and every kind of space. U+00A0 and U+202F are what a locale-aware exporter
    # emits between the thousands, they are indistinguishable from an ordinary space on screen
    # and in a diff, and one of them left in place makes the whole amount unreadable.
    cleaned = "".join(character for character in raw if not character.isspace())
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    if not cleaned:
        # A lone `+`, or a non-breaking space on its own, reaches here with nothing left. Calling
        # that "empty" would tell whoever reads the report that the tag was blank, when the file
        # actually shipped a character; settling that question is what the raw value is for.
        reason = "amount is empty" if not raw else f"{raw!r} holds no digit"
        return None, [ReadWarning("amount", field, raw, f"{reason}, so it is absent, not zero")]

    ambiguous = False
    if "." in cleaned and "," in cleaned:
        # Both present: the LAST of the two is the decimal separator, whichever it is, and the
        # other one groups the thousands. Two separators disambiguate each other, so no reading
        # is in doubt here.
        if cleaned.rindex(",") > cleaned.rindex("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # A lone comma is the decimal separator. When the group behind it is exactly three
        # digits, that is also what a thousands separator looks like: `2,000` is two under one
        # reading and two thousand under the other. The rule keeps the decimal reading, because
        # the OFX amount type has no thousands separator, and the doubt goes into a warning
        # rather than into a value nobody will question later.
        group = cleaned.rsplit(",", 1)[1]
        ambiguous = len(group) == 3 and group.isascii() and group.isdigit()
        cleaned = cleaned.replace(",", ".")

    if not _AMOUNT.fullmatch(cleaned):
        return None, [
            ReadWarning("amount", field, raw, f"{raw!r} is not a decimal amount, left null")
        ]

    # The scale of the file is kept: `10,00` stays `10.00`, because a balance compared against a
    # bank total is read by a human who expects the cents to still be there.
    value = Decimal(cleaned)
    if not ambiguous:
        return value, []
    message = (
        f"{raw!r} is ambiguous: a comma followed by exactly three digits reads as a decimal "
        f"separator or as a thousands separator. Kept the decimal reading, {value}, because the "
        f"OFX amount type has no thousands separator. If the file means the thousands, this "
        f"value is wrong by a factor of a thousand."
    )
    return value, [ReadWarning("amount", field, raw, message)]


def parse_date(raw: str, *, field: str) -> tuple[datetime.date | None, list[ReadWarning]]:
    """Read a date the way section 5 says, or return null and say why.

    Never the epoch and never today when the value is unreadable. A default date is the same
    class of mistake as a default amount: it survives every sanity check and it is wrong.
    """
    stripped = raw.strip()
    match = _LEADING_DIGITS.match(stripped)
    digits = match.group() if match else ""

    if not digits:
        reason = "date is empty" if not stripped else f"{raw!r} does not start with a digit"
        return None, [ReadWarning("date", field, raw, f"{reason}, left null")]

    if digits.strip("0") == "":
        # The bank has no date to give for this field and writes a filler rather than dropping
        # the tag. Legible intent, and no calendar date: month 00 and day 00 do not exist.
        return None, [ReadWarning("date", field, raw, "date is written as zeros, so it is absent")]

    warnings: list[ReadWarning] = []
    if len(digits) >= 8:
        # Eight digits then anything: YYYYMMDD, the rest is the time and the zone. No warning,
        # on purpose. Nearly every OFX date carries a zone, so one warning per date would bury
        # the warnings that mean something under one line per transaction.
        year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
    elif len(digits) == 6:
        day, month, year = int(digits[:2]), int(digits[2:4]), int(digits[4:6])
        year += 2000 if year <= _TWO_DIGIT_YEAR_PIVOT else 1900
        warnings.append(
            ReadWarning(
                "date",
                field,
                raw,
                f"six digits are ambiguous: read as DDMMYY (attested at HSBC Brasil), giving "
                f"{year:04d}-{month:02d}-{day:02d}. YYMMDD would give another date, and a two "
                f"digit year never says its century.",
            )
        )
    else:
        return None, [
            ReadWarning(
                "date",
                field,
                raw,
                f"expected eight digits (YYYYMMDD) or six (DDMMYY), got {len(digits)}, left null",
            )
        ]

    try:
        value = datetime.date(year, month, day)
    except ValueError:
        # The right shape and no such day: month 13, 30 February, year 0000. Nothing is rounded
        # to the nearest real date, that would be an invented value.
        return None, [ReadWarning("date", field, raw, f"{raw!r} is not a calendar date, left null")]
    return value, warnings
