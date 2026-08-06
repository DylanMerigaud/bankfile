# Unnamed bank: the file starts with a blank line, before the first header

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `blank-line-before-header.ofx`
- Sources: jseutter/ofxparse #161 (PR, opened 2020-11-22), jseutter/ofxparse #179 (PR, opened 2024-11-04)
- Provenance: one single byte comes from the sources, the newline that precedes `OFXHEADER:100`. It is attested in prose by #161 ("My bank OFX files start with empty lines") and in bytes by the test fixture added by #179, whose first line is empty. Everything else in our fixture (the nine header lines, the signon block, the account identifiers, the transaction, both balance blocks) comes from the shared template `corpus/template/ofx-1.0.2.ofx`. The diff between the template and this fixture is exactly one added blank line at position zero, nothing else. In particular `VERSION:102`, `ENCODING:USASCII` and `CHARSET:1252` are template values and say nothing about this bank.

## The deviation

The file begins with an empty line, then the nine `KEY:VALUE` header lines, then the usual blank separator line, then `<OFX>`. Nothing in the OFX 1.x header block requires the file to start on a non-empty line, and a tolerant reader is expected to skip leading whitespace. So this one is on the parser: `ofxparse` cuts the header region at the first `<`, then iterates over its lines and treats the FIRST empty line as the end of the header block. When that empty line is line one, the loop stops before reading a single header. Both PRs propose the same one-word repair in `read_headers`, `break` becoming `continue`, four years apart, which is itself the evidence that the first one was never merged.

What the source says:

```
+
+OFXHEADER:100
+DATA:OFXSGML
+VERSION:102
+SECURITY:NONE
...
+<OFX>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parses, 1 transaction, `headers_read` 0 instead of 9 |
| `ofxparse` 0.21, file opened in binary | parses, 1 transaction, `headers_read` 0 instead of 9 |
| `ofxtools` 1.1.1 | parses, 1 transaction, `trntype='DEBIT'`, `trnamt=Decimal('-10.00')` |

None of the three readings raises, and the transaction comes out intact in all three. The damage is silent: on both `ofxparse` readings the header count drops from nine to zero, so `ENCODING`, `CHARSET` and `VERSION` are simply gone. On a pure ASCII file like this fixture that costs nothing visible, which is precisely why it is dangerous: the same loss on a file carrying an accented payee name makes the read fail later, on the first high byte, far from the blank line that caused it. `ofxtools` 1.1.1 is unaffected.

## The rule

Fully covered by the shared rules: see [Where the header block ends (OFX 1.x)](../../reading-rules.md#2-where-the-header-block-ends-ofx-1x). Specific to this case, and the reason that section exists: blank and whitespace-only lines BEFORE the first `KEY:VALUE` line are stripped, never treated as the end of the block. Combined with section 1, losing the header block also loses the declared codec, so a reader that silently ends up with zero headers must report it rather than fall through to a default in silence.

## Caveats

- The bank is not named and no country is attested. #161 says only "My bank OFX files start with empty lines". The fixture added by #179 carries `CURDEF` BRL and `LANGUAGE` POR, which points at Brazil, but that is a deduction from the file contents, not a statement by any reporter, and our fixture keeps the template's USD anyway.
- The source claims more than the measurement shows. #161 says its patch "fixes parsing of those files", which reads as though such files fail to parse. Measured today on the blank line alone, `ofxparse` 0.21 does not fail: it returns the transaction and drops the headers without a word. The failures reported in #179 involve a second and a third deviation present in the same file (a non-ASCII memo, comma decimal amounts), each catalogued here in its own fixture.
- An earlier version of this fixture carried an accented memo, so the recorded measurement was about decoding and established nothing about the header. That byte was removed and the measurement replayed; the table above is the replay. The non-ASCII case is kept once, in `chase/non-ascii-byte-declared-usascii.qfx`, rather than duplicated under this bank.
- Both PRs were open at the dates given. Whether either has since been merged upstream was not rechecked on 2026-08-05; what was measured is the released `ofxparse` 0.21, which still loses the headers.
- The line "nine headers" is a property of the shared template, not of the bank's real file. Only the leading newline is attested.
