# The deviation corpus, one file per bank

This is the ASSET of the project. The code is not.

A model writes an MT940 parser that matches the specification in thirty seconds, because the
specification is public. It cannot know that Wells Fargo drops the newlines from a QFX header,
that Chase writes twisted headers, or that a file declaring `CHARSET:NONE` makes `ofxparse`
build a codec name that does not exist. Those are facts about the world, not about the
standard: they are observed, not derived.

Those three examples are not invented. They come from open, never-merged pull requests on
`jseutter/ofxparse` (#172, #160, #163), a package whose last release is dated 31 May 2021.

## The rule

One file per deviation, anonymised, with an `.md` beside it stating the bank, the format, what
departs from the norm, and the source reference (issue, user report).

Anonymisation: amounts, names and account numbers replaced. **The structure is the data, the
content never is.**

Two limits `scripts/validate_corpus.py` enforces, because they are easy to miss in an excerpt
pasted from a real file: no run of 13 digits or more (a full OFX timestamp is 14, use the date
alone), and no IBAN shape. The rule applies to the NOTES as well: they quote public issues, and
a public issue sometimes contains a real account number.

A third limit, learned from `ofxparse` issue #29: their maintainers anonymised their own
fixtures until the `FITID` values stopped being unique, which destroyed the property the
fixture was testing. **Anonymisation stops before the property under test.** The first pass of
this corpus made that exact mistake, giving the LCL fixture a `CHECKNUM` equal to its `FITID`,
so the measurement could no longer tell which field the parser had read.

## A fixture is the template plus one deviation

Every OFX fixture is generated from the same minimal document, `corpus/template/ofx-1.0.2.ofx`,
and differs from it only by the deviation it carries. That is deliberate: a corpus fixture is
worth something because its diff against the template IS the deviation, and nothing else.
Hand-written one at a time, fixtures drift (a space here, a date there) and the diff stops
saying anything.

```bash
python3 scripts/build_fixtures.py --check   # fails if a fixture drifted from the template
```

## Two categories, and they have to be told apart

Not every entry is the bank's fault, and getting that wrong turns against the corpus the moment
someone opens the specification.

- **The file is out of spec.** Wells Fargo runs its whole header onto one line, Chase drops the
  blank separator line. The bank is at fault.
- **The file conforms and the parser fails anyway.** `CHARSET:NONE` is one of the three values
  OFX 1.x allows, `CHECK` is a legitimate `TRNTYPE`, `NAME` is optional. Here it is the consumer
  assuming what the standard never promised.

Both matter equally: in both cases a real file breaks real code.

## The cases

Every note carries a dated measurement: what `ofxparse` 0.21 and `ofxtools` 1.1.1 actually do
with the fixture, executed rather than assumed. The raw results are in
[`../measurements/2026-08-05.json`](../measurements/2026-08-05.json), and the cross-cutting
rules they feed are in [`../reading-rules.md`](../reading-rules.md).

| bank | case | what the file does |
|---|---|---|
| Wells Fargo | [header-on-one-line](wells-fargo/header-on-one-line.md) | the whole header on a single line |
| Chase | [blank-line-before-header-none-after](chase/blank-line-before-header-none-after.md) | a blank line before the header, none after |
| Chase | [non-ascii-byte-declared-usascii](chase/non-ascii-byte-declared-usascii.md) | a cp1252 byte in a file declaring `USASCII` |
| E*Trade | [charset-none-with-encoding-usascii](etrade/charset-none-with-encoding-usascii.md) | `CHARSET:NONE` with `ENCODING:USASCII` |
| HSBC Brasil | [dtstart-ddmmyy](hsbc-brasil/dtstart-ddmmyy.md) | `DTSTART` on six digits, `DDMMYY` |
| LCL | [check-without-payee](lcl/check-without-payee.md) | a `CHECK` with no `NAME` and no `MEMO` |
| OnPoint Community Credit Union | [self-closing-memo-tag](onpoint-community-credit-union/self-closing-memo-tag.md) | `<MEMO/>` self-closing inside SGML |
| unnamed | [character-outside-latin1](unnamed-bank/character-outside-latin1.md) | a payee name outside latin-1 |
| unnamed | [charset-8859-1-without-iso-prefix](unnamed-bank/charset-8859-1-without-iso-prefix.md) | `CHARSET:8859-1`, without the `ISO-` prefix |
| unnamed | [xml-declaration-ofx-2](unnamed-bank/xml-declaration-ofx-2.md) | OFX 2.x, encoding in the XML declaration |
| unnamed | [blank-line-before-header](unnamed-bank/blank-line-before-header.md) | a blank line precedes the header |
| unnamed | [amount-comma-decimal](unnamed-bank/amount-comma-decimal.md) | `2000,00` |
| unnamed | [amount-plus-sign-and-space](unnamed-bank/amount-plus-sign-and-space.md) | `+1 006,60` |
| unnamed | [zero-date](unnamed-bank/zero-date.md) | `DTASOF` filled with zeros |
| unnamed | [chknum-instead-of-checknum](unnamed-bank/chknum-instead-of-checknum.md) | `CHKNUM` instead of `CHECKNUM` |
| unnamed | [empty-tags-curdef-fitid-name](unnamed-bank/empty-tags-curdef-fitid-name.md) | tags present and empty |
| unnamed | [mixed-case-trntype](unnamed-bank/mixed-case-trntype.md) | `Credit` instead of `CREDIT` |
| unnamed | [tags-outside-spec](unnamed-bank/tags-outside-spec.md) | vendor tags inside a `STMTTRN` |

Six named banks out of eighteen cases: that is what the sources allow, the other reporters
write "my bank" and nothing more. The full triage of the 43 upstream entries is in
[docs/PHASE0-TRIAGE.md](../../docs/PHASE0-TRIAGE.md).

**There is still no MT940, CAMT.053 or BAI2 deviation here.** The source triaged was an OFX
parser, it could not produce anything else.
