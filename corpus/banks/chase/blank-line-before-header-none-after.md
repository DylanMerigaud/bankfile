# Chase: a blank line before the header block, and none between the last header and `<OFX>`

- Bank: Chase
- Format: QFX (OFX 1.0.2 SGML)
- Fixture: `blank-line-before-header-none-after.qfx`
- Sources: jseutter/ofxparse #160 (PR, opened 2020-09-29)
- Provenance: the source quotes the whole header block of a QFX exported from the Chase website, with the leading blank line and with `<OFX>` following `NEWFILEUID:NONE` directly. Those two layout facts, and nothing else, are what this fixture carries. Everything else (signon block, account identifiers, the single transaction, the amounts, the dates, both balance blocks) comes from the shared template `../../template/ofx-1.0.2.ofx` and says nothing about Chase. The diff against the template is exactly two lines: one blank line added at the top of the file, one blank line removed before `<OFX>`. The PR also attaches a Chase credit card file with a non-ASCII payee; that byte is a separate deviation and lives in `non-ascii-byte-declared-usascii.qfx`, so this fixture measures the header layout alone.

## The deviation

The file opens with an empty line, before `OFXHEADER:100`, and then runs straight from the last header line into the SGML body with no empty line in between. Both are layout facts about whitespace, not about the data. Leading whitespace ahead of the header block is not forbidden by anything the source cites, so a reader that stops at the first blank line is making an assumption the file never agreed to. The missing separator line is the point where a reasonable argument for "the bank is at fault" exists, but no source in this corpus quotes the OFX 1.0.2 text that would require the separator, so this note does not assert it (see Caveats). Practically, the fault that costs money here is on the parser side: `ofxparse` used the blank line as the end of the header block, so a file that begins with one loses every header.

What the source says:

```

OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
<OFX>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parses, 1 transaction, DEBIT -10.00 on 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO`, but **0 headers read** instead of 9 |
| `ofxparse` 0.21, file opened in binary | parses, 1 transaction, DEBIT -10.00 on 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO`, **0 headers read** instead of 9 |
| `ofxtools` 1.1.1 | parses, 1 transaction, `STMTTRN(trntype='DEBIT', dtposted=2026-01-15 UTC, trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT')` |

Nothing raises here, and that is the problem. In both `ofxparse` modes the header dictionary comes back empty: `VERSION`, `ENCODING` and `CHARSET` are all gone, with no exception and no warning. On this deliberately ASCII-only fixture the transaction still comes out correct, so the loss is invisible. On a real Chase export the same loss lands elsewhere: the declared `CHARSET:1252` is no longer available when a payee carries a high byte, and the failure surfaces far from its cause. Silent loss of the whole header block is worse than a crash, because nothing in the import report says the encoding decision was made without evidence.

## The rule

Fully covered by the shared rules, section 2, "Where the header block ends (OFX 1.x)": skip blank lines at the start of the file and between headers, end the block at the first `<` or at the first line without a `:`, and never require the blank separator line. See `../../reading-rules.md`. Nothing specific to Chase is needed beyond that; this fixture is the measurement that section 2 cites. Decoding once the headers are recovered follows section 1 of the same file.

## Caveats

- The fixture is a reconstruction. Only the ten header lines quoted above come from the PR; the body is the shared template, transposed into a bank statement (`STMTRS`) while the file attached to the PR is a credit card statement (`CCSTMTRS`). No claim about Chase's credit card aggregates should be read into it.
- The audit asked this note to charge Chase with a spec violation for the missing blank line between `NEWFILEUID:NONE` and `<OFX>`. That correction is not applied as written. No source gathered here quotes the OFX 1.0.2 text, and section 2 of the shared rules says a reader must never require that separator. Calling it a violation would rest on a spec line nobody in this project has read, which is the exact failure mode the corpus README warns about. The classification of the leading blank line as a parser-side expectation, the other half of the correction, is applied.
- The country is not stated. The PR says the files were exported "from the Chase website" and nothing more, so no country is claimed here.
- One reporter, one report, 2020. The behaviour is attested by our own measurement of 2026-08-05, not by the PR text, which describes the fix and not the symptom.
- The measurement covers two parsers in three modes of invocation, not three parsers.
- `headers_read: 0` is what the measurement file records for both `ofxparse` modes. Nine is the count the same harness returns on the unmodified template.
