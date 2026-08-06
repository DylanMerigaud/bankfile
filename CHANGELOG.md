# Changelog

This file exists because of what this library does. For an eslint preset a changelog is a
courtesy; here, a change to how a debit sign or a `:86:` purpose is normalised moves numbers
inside somebody's reconciliation. Anything that can change a figure gets its own line, and says
which figure.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning:
[semantic](https://semver.org/spec/v2.0.0.html), where a **breaking** change includes any change
to a normalised value that a caller could already have been relying on.

## [0.2.0] - 2026-08-06

### Fixed

- **A German counterparty no longer comes back with their account number welded to the front of
  their name.** `mt-940` 5.0.0 maps `:86:` subfield `?31` to `applicant_name`, where 4.30.0
  mapped it to `applicant_iban`, so `?31` and `?32` are joined into one string and the IBAN
  field stops existing. Measured on the vendored corpus: **59 transactions across 5 files**
  returned a `counterparty_name` such as `DE42100100100043921105Richter Renate`, while
  `counterparty_account` fell through to the BIC. Per the DFUe-Abkommen Anlage 3 subfield table
  `?31` is the Kontonummer and `?32` with `?33` are the name, and all 69 occurrences of `?31` in
  the corpus are account numbers, none a name.

  Both fields now carry what the file says. The repair reads `?31` off the raw `:86:` before the
  parser consumes it and only acts when the name literally starts with that value, so it becomes
  a no-op the day upstream fixes it rather than a second bug.

  **This changes two normalised values a caller could have relied on**, which is breaking by the
  rule at the top of this file. It is a correction, not a redefinition: the old values were the
  wrong-but-plausible kind that a reconciliation matches a payer by and never flags.

## [0.1.1] - 2026-08-06

### Fixed

- **Reading a statement no longer writes statement content to your log.** `mt940.tags` logs the
  raw `:61:` line at ERROR level when it fails to match, and with no handler configured Python's
  last resort handler prints it, so `parse()` on a real file wrote 3737 bytes to stderr
  including eight fragments of statement content, counterparty names among them. The upstream
  logger is now silenced for the duration of our own parse, scoped and restored, never disabled
  globally. Everything we could not read is still reported, in the returned object where it
  belongs. A library whose pitch is that the statement never leaves your machine cannot put the
  payee in your logs.

## [0.1.0] - 2026-08-06

First release. Reads MT940 and OFX/QFX; MT942, CAMT.053 and BAI2 are not written yet.

### Added

- Reads MT940 and OFX/QFX (OFX 1.x SGML and OFX 2.x XML) into one normalised schema, defined as
  data in `corpus/schema/`, not as code.
- `bankfile <file> --json` on the command line.
- A local MCP server over stdio, `bankfile-mcp`, with three read-only tools that return
  filtered and paginated slices and never a whole file.
- A corpus of 18 documented bank deviations, each with the source it came from and a dated
  measurement of what `ofxparse` 0.21 and `ofxtools` 1.1.1 do with it.
- An import report on every statement: everything that could not be read, and everything
  ambiguous, is reported rather than dropped.
- A reconciliation check. If opening plus the entries does not make the closing balance, the
  report says so with the difference. No other parser tells you that your file contradicts
  itself.

### Decided, and worth knowing before you depend on it

- `date` is the date the statement line carries, and the field to sort and reconcile by. Its
  provenance differs by format and the schema now says so: MT940 `:61:` value date, OFX
  `DTPOSTED`. It was documented as "value date", which is wrong for OFX.
- `booking_date` only ever holds a date the BANK set: MT940 entry date, OFX `DTAVAIL`. It used
  to fall back to OFX `DTUSER`, which is the date the CUSTOMER initiated the transaction and
  can precede the posting by weeks. A date whose meaning is not recorded is a plausible wrong
  answer, so it is gone from that fallback and stays available in `raw`.

### Fixed before the first release

These never reached anyone, and they are listed because each one is a figure that would have
been wrong.

- **A reversed credit came back positive.** SWIFT marks an entry `RC` when it reverses a credit,
  which takes money out. `mt-940` negates only for `D`, so those entries arrived as income.
  Found by balance arithmetic, not by a test.
- **Two statements in one OFX file merged.** With `</STMTRS>` omitted, which SGML allows, the
  second account's entries were returned under the first account's number and currency.
- **A repeated tag made the normalised field and `raw` disagree.** A transaction carrying
  `TRNAMT` twice reported one amount and stored the other, silently.
- **A transaction missing its amount could reach the output.** It is dropped and reported now,
  because an entry with no amount cannot be reconciled and a zero would be an invented figure.
