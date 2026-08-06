# Unnamed bank: a UTF-8 file whose payee name carries a character outside latin-1

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `character-outside-latin1.ofx` (utf-8)
- Sources: jseutter/ofxparse #169 (issue, opened 2022-05-31)
- Provenance: the two header lines `ENCODING:UTF-8` and `CHARSET:NONE`, and the payee name `Finančna uprava RS`, are quoted verbatim in the issue. Everything else (the SGML tree, the account block, the amounts, the dates, the balances) comes from the shared template `corpus/template/ofx-1.0.2.ofx`. The fixture carries the deviation with the anonymised payee `ANON UPRAVA č`, which keeps the U+010D of the source and drops the rest. Two things in the source file are NOT reproduced in the fixture: the header block wrapped in an XML comment (`<!--` … `-->`), and the one-tag-per-open/close-pair layout. The diff against the template is three lines: the two header lines and the `<NAME>` line.

## The deviation

The file declares `ENCODING:UTF-8` in its header and then puts a character outside latin-1, `č` (U+010D), inside a payee name. That is a legal OFX 1.x file: the header announces the encoding, and the bytes match the announcement. The failure is on the parser side. `ofxparse` 0.21, used the way its documentation shows (a file opened in text mode), re-encodes the decoded text to latin-1 inside `six.b()` before it ever looks at the declared encoding, so any code point above U+00FF raises. Nothing here can be charged to the bank: the two header lines and the accented name are the only bank-attested bytes, and all three are consistent with each other.

What the source says:

```
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:NONE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
...
<NAME>Finančna uprava RS</NAME>
```

In the source these nine header lines sit between `<!--` and `-->`, and the `<NAME>` element is one field among several on a single long line.

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | fails: `UnicodeEncodeError: 'latin-1' codec can't encode character 'č' in position 625: ordinal not in range(256)` |
| `ofxparse` 0.21, file opened in binary | reads, nine headers read, 1 transaction, payee `ANON UPRAVA č` intact |
| `ofxtools` 1.1.1 | reads, 1 transaction, `name='ANON UPRAVA č'` |

Text mode is the only failing path, and it fails on the encode step, not on the header block: nine headers are read in binary mode, so nothing is lost silently here. No reading truncates the payee name, and no reading returns a wrong amount. The exception is loud, which makes this one of the safer cases in the corpus: an import that crashes is an import somebody fixes.

## The rule

Fully covered by the shared rules: `../../reading-rules.md`, section 1 (Encoding). Open in binary, then pick the codec, and `ENCODING:UTF-8` decides on its own whatever `CHARSET` says. The specific point this fixture contributes is the measurement behind the first sentence of that section: text mode is the path that breaks, binary mode is the path that works, on the same bytes, on the same day.

## Caveats

- The bank is not named anywhere in the issue and no country is attested. Slovenia is deducible from the Slovenian payee name and from the account identifier prefix in the source, but the reporter never states it, so the note claims neither.
- **The measurement contradicts the source.** The reporter writes "This file can't be parsed whether read as text or as a binary" and shows a second traceback, `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc4 in position 751`, for binary mode. On our fixture, binary mode succeeds and reads all nine headers. The difference between the two files is that the source wraps its header block in an XML comment while the fixture leaves the headers bare; that is the plausible cause of the divergence, but it has NOT been measured, and it is the reason this fixture is not evidence for the binary-mode half of the report. Anyone who wants that half needs a separate fixture with a comment-wrapped header.
- The byte offset also differs, 625 in the measurement against 751 in the issue, which is expected: the fixture body is not the source body.
- The audit on the previous pass asked for `CHARSET:1252` in this fixture, on the grounds that `CHARSET:NONE` duplicates the E*Trade case. Not applied, and here is why. The pair `ENCODING:UTF-8` / `CHARSET:NONE` is quoted verbatim in #169, so writing `1252` would put a byte in the fixture that no source attests, which is worse than a shared property. The E*Trade fixture carries a different pair, `ENCODING:USASCII` / `CHARSET:NONE`, and the conflict the audit was really pointing at (three notes giving three treatments of `CHARSET:NONE`) is now settled once in `../../reading-rules.md` section 1. What remains true is that the diff against the template is not the single deviation the corpus asks for: two of its three lines are the header pair, and `CHARSET:NONE` is incidental to the case this fixture is named for.
- Both parser versions and the reading date are the ones in `corpus/measurements/2026-08-05.json`. Nothing here says how any other version behaves.
