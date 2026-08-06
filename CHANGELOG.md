# Changelog

This file exists because of what this library does. For an eslint preset a changelog is a
courtesy; here, a change to how a debit sign or a `:86:` purpose is normalised moves numbers
inside somebody's reconciliation. Anything that can change a figure gets its own line, and says
which figure.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning:
[semantic](https://semver.org/spec/v2.0.0.html), where a **breaking** change includes any change
to a normalised value that a caller could already have been relying on.

## [Unreleased]

Nothing released yet. Everything below is what the first release will contain.

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
