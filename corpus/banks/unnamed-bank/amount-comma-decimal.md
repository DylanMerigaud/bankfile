# Unnamed bank: amounts written with a comma as the decimal separator

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `amount-comma-decimal.ofx` (pure ASCII)
- Sources: jseutter/ofxparse #179 (pull request by rennerocha, opened 2024-11-04)
- Provenance: only the two amount strings come from the source. The PR adds a test fixture whose transaction carries `<TRNAMT>2000,00` and whose single `<LEDGERBAL>` carries `<BALAMT>2000,00`. Our fixture substitutes those two digit strings into the shared template, and nothing else: the diff against `../../template/ofx-1.0.2.ofx` is exactly two lines. The leading minus sign on `TRNAMT` is the template's, not the source's (the source amount is positive under a `DEBIT` type). The `<AVAILBAL><BALAMT>90.00` that still uses a dot is the template's too. The source fixture has no `AVAILBAL` block at all. Everything else (header block, signon, account identifiers, dates, labels) is template and says nothing about this bank.

## The deviation

The file writes monetary values with a comma where OFX files usually carry a dot: `2000,00` instead of `2000.00`. The source puts that form both in the transaction amount and in the ledger balance, so the comma is the file's convention and not a one-off typo in a single field. Assigning fault is not possible from the bytes available here: none of the sources gathered for this corpus quotes the OFX 1.0.2 text on the `amount` type, so we cannot say whether a comma decimal is permitted or is a departure by the bank. What the source does establish is that a real exporter ships this form, and that the PR author considered the file worth fixing the library for, though for a different reason (see Caveats).

What the source says:

```
+<TRNAMT>2000,00
+<FITID>N10235
...
+<LEDGERBAL>
+<BALAMT>2000,00
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parsed, 9 headers read, 1 transaction, amount `-2000.00` |
| `ofxparse` 0.21, file opened in binary | parsed, 9 headers read, 1 transaction, amount `-2000.00` |
| `ofxtools` 1.1.1 | parsed, 1 transaction, `trnamt=Decimal('-2000.00')` |

No parser fails on this file, and no parser loses the value: all three read the comma as a decimal separator and return two thousand, not two. The comma decimal on `TRNAMT` is therefore a solved case in both libraries as measured today, which makes this fixture a regression guard rather than a bug report. The ledger balance is not covered by the measurement, which reports transactions only.

## The rule

This case is fully covered by the shared rule, `../../reading-rules.md` section 3 "Amounts", step 4: a value containing only `,` reads that comma as the decimal separator. Nothing here departs from it. One point specific to this file: the separator decision is made per value, never once per file. Our fixture holds `2000,00` and `90.00` side by side, so any implementation that sniffs the first amount and applies its convention to the rest of the document returns a wrong figure for the other one.

## Caveats

- The PR is not about amounts. #179 is titled "Fix import OFX file with linebreak before headers and not ASCII content" and its one-line change makes `read_headers` skip blank lines instead of stopping at them. The comma amounts are incidental in the fixture it adds, and the author never claims they are a problem. The measurement agrees with that silence: nothing breaks on the comma. Treat this note as a catalogue entry for a form that exists in the wild, not as a defect report.
- The claim that the OFX 1.0.2 `amount` type accepts a comma decimal is not supported by any source cited here and has not been checked against the specification text. Any classification of this file as compliant, and so any assignment of fault to the parser rather than the bank, depends on that unverified claim and remains to be confirmed.
- The two decimal notations sitting in the same file is an artefact of our reconstruction, not an attested property of the original. The source fixture has a single `BALAMT` and no `AVAILBAL`; the dot notation survives only because the template's `AVAILBAL` block was kept.
- The bank is not named. The source fixture carries `CURDEF` BRL, `LANGUAGE` POR and a Portuguese memo, which points to Brazil, but that is a deduction from the file's own contents and no reporter names a country or an institution.
- The source fixture also begins with a blank line before the header block and carries `<DTASOF>00000000`. Both are catalogued as their own fixtures (`blank-line-before-header.ofx`, `zero-date.ofx`) and are deliberately absent here, so that the diff against the template carries this deviation and no other.
- The measurement is a single run on 2026-08-05, on `ofxparse` 0.21 and `ofxtools` 1.1.1. It says nothing about other versions, and nothing about how either library treats the comma inside `BALAMT`.
