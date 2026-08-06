# Unnamed bank: a ledger balance dated `00000000`

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `zero-date.ofx`
- Sources: jseutter/ofxparse #179 (PR, opened 2024-11-04)
- Provenance: one line comes from the source, `<DTASOF>00000000` inside `<LEDGERBAL>`, taken from
  the fixture added by the PR. Everything else (header block, signon, account block, the single
  transaction, both balance amounts) comes from the shared template `corpus/template/ofx-1.0.2.ofx`.
  The diff against the template is exactly one line, the `DTASOF` of `LEDGERBAL`. The `AVAILBAL`
  block that follows it, with a real date, is the template's: the source file has no `AVAILBAL` at
  all, so the coexistence of a zero date and a real date in this fixture is a reconstruction
  artifact, not an attested property of the original file.

## The deviation

The bank fills the balance date with eight zeros instead of a date. `00000000` is not a
`YYYYMMDD` value: month `00` and day `00` do not exist, so no calendar date can be built from it.
The intent is legible, the bank has no as-of date to give for that balance and writes a filler
rather than omitting the tag, but the value it writes is not a member of the OFX date type. On
this point the file is the one at fault, and the fault is confined to a single field: the
transaction, the amounts and the statement window in the same file are all well formed.

Note what the source does NOT establish. PR #179 is about a blank line before the header block and
non-ASCII content, and it never mentions the zero date. The `00000000` is simply present in the
fixture it adds, and no reporter comments on it. So the deviation is attested by bytes, not by a
bug report.

What the source says:

```
+<LEDGERBAL>
+<BALAMT>2000,00
+<DTASOF>00000000
+</LEDGERBAL>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | reads, 9 headers read, 1 transaction (debit, `-10.00`, 2026-01-15) |
| `ofxparse` 0.21, file opened in binary | reads, 9 headers read, 1 transaction (debit, `-10.00`, 2026-01-15) |
| `ofxtools` 1.1.1 | fails: `OFXSpecError: Can't set LEDGERBAL.dtasof to 00000000: '00000000' does not conform to OFX formats for <class 'datetime.datetime'>` |

The two parsers split on this file. `ofxparse` returns the statement in both modes, with all nine
headers and the transaction intact. `ofxtools` refuses the whole document over one field: a
statement whose single transaction is sound becomes unreadable because a balance has no as-of
date. That is the outcome the failure doctrine in [the shared reading rules](../../reading-rules.md)
exists to prevent.

## The rule

Fully covered by the shared rules: section 5, "Dates", all-zeros means the date is absent, never
the epoch and never today; and section 0, "The failure doctrine", a file that can be read is never
rejected over the value of a single field. Concretely here: `LEDGERBAL.dtasof` stays null, the
amount `90.00` is kept, a named warning carries the raw value `00000000`, and the transactions are
returned. Nothing specific to this case is added.

## Caveats

- The bank is not named, and no country is attested. The source fixture carries `CURDEF` BRL and
  `LANGUAGE` POR, which points at Brazil, but that is a deduction from the file's own indicia and
  no reporter names a country. Our fixture keeps the template's `USD` and `ENG`, so it carries no
  country signal at all.
- Only the `<DTASOF>00000000` line is real bytes from the source. The surrounding statement is the
  corpus template.
- The source file has no `AVAILBAL`. The `AVAILBAL` with a valid `DTASOF` in this fixture comes
  from the template, so "the same file mixes a zero date and a real date" is true of the fixture
  and unverified of the original.
- The PR never discusses the zero date. It is incidental to the change it proposes, so nothing is
  known about how this bank behaves beyond this one line.
- The measurement records headers read, transaction count and transaction fields. It does not
  record what `ofxparse` produced for the ledger balance date, so this note asserts nothing about
  the value `ofxparse` returns for that field, only that the read succeeded.
- The measurement was replayed on 2026-08-05 against `ofxparse` 0.21 and `ofxtools` 1.1.1. Two
  parsers in three call modes, not three parsers.
