# Shared reading rules

Each note under `banks/` describes ONE deviation. Several of them are handled at the same
place in a parser, and if every note writes its own version of the rule you end up with
eighteen rules, some of which contradict each other. That happened, and an audit found it:
three notes gave three incompatible treatments of `CHARSET`, two gave two different ends of
the header block, and two normalised the same amount into two different values.

So the cross-cutting rules live HERE, once. A note only restates a shared rule when it
departs from it, and then it says why.

## 0. The failure doctrine

**A file that can be read is never rejected over the value of a single field.**

An unexpected value is kept verbatim, the normalised field stays null, and a named warning
(file, tag, raw value, rule that fired) goes into the import report. We only fail when the
structure is unreadable, meaning no usable statement block comes out of the file at all.

Two reasons, and the second is the real one:

1. A statement rejected in full because a balance date was zeros is a statement nobody can
   reconcile, when every one of its entries was sound.
2. **A wrong but plausible amount is the worst possible failure in finance.** It enters a
   reconciliation and nobody sees it. So: never an invented value, never a fallback date,
   never `errors='ignore'`. What we cannot read stays null and says so.

## 1. Encoding

Open the file in binary, ALWAYS. The usage ofxparse documents, opening in text mode, is
measured as the only path that breaks on a character outside latin-1.

Pick the codec in this order:

1. OFX 2.x (an XML document): the encoding comes from the XML declaration, not from a
   `key:value` header block.
2. `ENCODING:UTF-8`: decode as utf-8, whatever `CHARSET` says.
3. Otherwise, table on `CHARSET`: `1252` to cp1252, `8859-1` and `ISO-8859-1` to iso-8859-1,
   `NONE` to cp1252, absent to cp1252, anything else to cp1252 with a warning.
4. If decoding still fails, retry cp1252 then iso-8859-1. Neither can fail on a single byte.
   Report which codec was finally used.

Never fall back to ASCII, never `errors='ignore'` or `errors='replace'`: both truncate a
payee name without saying so.

`CHARSET:NONE` is not a file anomaly. It is one of the three values OFX 1.x allows, alongside
`1252` and `ISO-8859-1`. Note that `ofxtools` maps `NONE` to utf-8 where the patches proposed
to `ofxparse` map it to cp1252. This corpus picks cp1252, an ASCII superset that cannot raise
on any byte, and records that as a choice rather than as a reading of the standard.

## 2. Where the header block ends (OFX 1.x)

The header block is the bytes before the first `<` in the file.

- Skip blank lines, at the start of the file and between headers, instead of treating them as
  the end of the block. **Never require the blank separator line**: real files omit it.
- The block ends at the first `<`, or at the first line without a `:`.
- An unreadable header does not fail the read: mark it untrusted, apply the format defaults
  (`VERSION` 102, `DATA` OFXSGML, `CHARSET` 1252) and report it.

The measurement behind this rule: on both fixtures that begin with a blank line, `ofxparse`
0.21 does not crash, it returns **zero headers** instead of nine. The declared encoding
disappears, and the file breaks much later, on the first accented byte, far from the cause.

## 3. Amounts

In order, on the raw string:

1. strip spaces, including U+00A0 and the narrow U+202F;
2. strip a leading `+`, the positive sign being implicit;
3. if both `.` and `,` are present, the LAST of the two is the decimal separator and the
   other is a thousands separator to remove;
4. if only `,` is present it is the decimal separator, so replace it with `.`. When the group
   after it is exactly three digits the value is ambiguous (`2,000` can mean two or two
   thousand): keep the decimal reading, which matches the OFX amount type since it has no
   thousands separator, and WARN;
5. build a `Decimal`, never a float.

## 4. Tags

- Compare tag names uppercased: `<TRNTYPE>Credit` and `<TRNTYPE>CREDIT` are the same tag and
  the same value.
- The self-closing form `<TAG/>` is normalised into an empty tag BEFORE extraction, so it
  never reaches the value rules.
- A tag that is present but empty means ABSENT, never an empty string, and never a crash.
- An unknown tag inside a known aggregate is read, skipped, and stored in an extension bag
  (name, raw value) attached to that aggregate. It never interrupts the reading of its
  siblings, and above all it never shifts the standard fields that follow it.
- A value outside an enumeration (an unknown `TRNTYPE`) follows the failure doctrine: raw
  value kept, normalised type set to `OTHER`, warning. The enumeration is open.

## 5. Dates

- Eight digits or more: `YYYYMMDD`, the rest being time and zone.
- Exactly six digits: it depends on the format, and conflating the two was a mistake in the
  first version of this document.
  - In **MT940**, six digits IS the format. SWIFT fixes the value date of `:61:` as `6!n`
    `YYMMDD`, so reading `110722` as 22 July 2011 is not a guess and must NOT warn. Warning on
    every date of every MT940 file would bury the warnings that mean something.
  - In **OFX**, eight digits are the norm and six are an anomaly. `DDMMYY` is attested there
    (HSBC Brasil, ofxparse #58) and `YYMMDD` is not, so read `DDMMYY` and WARN: a two-digit
    year in a format that does not ask for one is never certain.
- All zeros: date absent. Never the epoch, never today.
- Any other length, or empty: date absent, with a warning.

None of these branches fails. An unreadable balance date must not cost you the transactions.
