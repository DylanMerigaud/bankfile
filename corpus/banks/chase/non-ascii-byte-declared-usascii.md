# Chase: a cp1252 byte in a file that declares `ENCODING:USASCII`

- Bank: Chase
- Format: QFX (OFX 1.0.2 SGML)
- Fixture: `non-ascii-byte-declared-usascii.qfx` (cp1252, one byte `0xA6` at offset 620)
- Sources: jseutter/ofxparse #160 (PR, opened 2020-09-29), jseutter/ofxparse #179 (PR, opened 2024-11-04)
- Provenance: the deviation comes from the fixture `tests/fixtures/chase_cc.qfx` added by PR #160, which quotes both the header pair `ENCODING:USASCII` / `CHARSET:1252` and the payee line `<NAME>SQ *ECCO UN POCO ¦ NATURA`, where `¦` is the cp1252 byte `0xA6`. Only that byte is carried into our fixture: `<NAME>ANON MERCHANT` becomes `<NAME>ANON ¦ MERCHANT`, and the diff against the shared template is that one line and nothing else. The header block, the signon, the account, the amounts, the dates and the balances all come from the shared template and say nothing about Chase. PR #179 is listed as a second source because it reports the same pairing (a file declaring `ENCODING:USASCII` carrying a non-ASCII payload), but its quoted bytes belong to a Brazilian file from another institution, not to Chase.

## The deviation

The file declares `ENCODING:USASCII` in its header block and then carries a byte outside ASCII in a transaction label. Taken alone, the `ENCODING` line contradicts the payload. Taken with the `CHARSET:1252` line that sits right under it, the file is self-consistent under the usual reading of OFX 1.x, where `ENCODING` states that the payload is single-byte and `CHARSET` names the code page to interpret those bytes with. Under that reading the bank is not at fault: a reader that honours `CHARSET:1252` decodes `0xA6` as the broken bar `¦` and loses nothing. The fault sits with any reader that ignores `CHARSET` and treats `ENCODING:USASCII` (or the platform default) as the codec, which is what makes a single label byte cost the whole statement.

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
...
<NAME>SQ *ECCO UN POCO ¦ NATURA
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa6 in position 620: invalid start byte` |
| `ofxparse` 0.21, file opened in binary | ok, 9 headers read, 1 transaction, payee `ANON ¦ MERCHANT`, amount `-10.00`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | ok, 1 transaction, `name='ANON ¦ MERCHANT'`, `trnamt=Decimal('-10.00')` |

Only the documented usage fails, and it fails on the byte itself (position 620 is the `0xA6` of the payee), not on the header block: the nine headers are read intact as soon as the file is opened in binary. The failure is loud, and no read here returns a truncated label or a silently dropped transaction, which is the better of the two outcomes: a mangled payee entering a reconciliation without an alarm would be worse than this crash. The declared `CHARSET:1252` is enough on its own to decode the file, and both binary reads recover the exact character.

## The rule

Fully covered by the shared rules: open in binary and pick the codec by the table in [Encoding](../../reading-rules.md#1-encoding), which sends `CHARSET:1252` to cp1252. Specific to this case, and worth stating once: `ENCODING:USASCII` must never be turned into a codec name. It is not a contradiction to be resolved against the payload, it is a statement about byte width, and `CHARSET` is what names the code page. No decode attempt on this file may end in `errors='ignore'` or `errors='replace'`, which would drop the byte and hand back a payee that reads as correct.

## Caveats

- The country of Chase is not attested by either source. #160 says only that the file was exported from the Chase website.
- The reading of `ENCODING` as byte width and `CHARSET` as code page, on which the "the bank is not at fault" verdict rests, is not backed by any specification line quoted here. No source in this corpus cites the OFX 1.0.2 text on that point. The verdict stands or falls with that reading.
- The `utf-8` in the text-mode error is the platform default of the Python that ran the measurement, not a codec chosen by `ofxparse` from the file headers. The same read on a machine with another default locale can produce a different message, or no error at all.
- Everything in the fixture except the single `0xA6` byte is the shared template. The payee `ANON ¦ MERCHANT` is our own construction, not a Chase label; only the byte is real. The original label from #160 and the byte offset 620 are properties of our reconstruction, not of any file Chase ever emitted.
- #179 is a second attestation of the pattern, not a second attestation about Chase.
- The header deviation reported by #160 (a leading blank line and no blank separator before `<OFX>`) is deliberately absent from this fixture. It lives in `blank-line-before-header-none-after.qfx`, so that each file carries one deviation and each measurement means one thing.
