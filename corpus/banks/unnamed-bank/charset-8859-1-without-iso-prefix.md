# Unnamed bank: CHARSET declared as "8859-1", without the "ISO-" prefix

- Bank: unnamed
- Format: QFX, OFX 1.0.2 SGML header
- Fixture: `charset-8859-1-without-iso-prefix.qfx` (pure ASCII bytes)
- Sources: jseutter/ofxparse #148 (issue, opened 2019-03-07)
- Provenance: the two header lines `ENCODING:USASCII` and `CHARSET:8859-1` come from the bytes quoted in the issue. Everything else (the statement body, the amounts, the dates, the labels, `SECURITY:NONE`) comes from the shared corpus template and says nothing about this bank. The issue shows `SECURITY:TYPE1` where the fixture carries the template's `SECURITY:NONE`: that field is not the deviation and was deliberately left at the template value. The only line where this fixture differs from `corpus/template/ofx-1.0.2.ofx` is `CHARSET:8859-1` in place of `CHARSET:1252`.

## The deviation

The file writes the charset as `8859-1`, dropping the `ISO-` prefix. `ofxtools` 1.1.1 rejects that value against an enumeration of three, `('ISO-8859-1', '1252', 'NONE')`, so the value is at least outside what the maintained strict parser accepts. The trap on the reader side is that `8859-1` is not a Python codec name: `iso-8859-1` and `latin-1` are aliases, the bare `8859-1` is not, so a parser that hands the raw header value to the codec layer fails on a lookup rather than on the data. The reporter describes exactly that, writing that ofxparse tries to parse it as `cp8859-1` instead of `iso-8859-1`. Which side is at fault depends on whether OFX 1.x really restricts `CHARSET` to those three spellings, and no source gathered here quotes the specification text, so this note does not settle it.

What the source says:

```
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:TYPE1
ENCODING:USASCII
CHARSET:8859-1
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | read: 9 headers, 1 transaction, debit -10.00 dated 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxparse` 0.21, file opened in binary | read: 9 headers, 1 transaction, debit -10.00 dated 2026-01-15, payee `ANON MERCHANT`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | failure: `OFXHeaderError: Invalid OFX header - '8859-1' is not OneOf ('ISO-8859-1', '1252', 'NONE')` |

`ofxtools` refuses the file at the header and names both the offending value and the expected set, which is the useful failure: it points at the cause. `ofxparse` 0.21 accepts the file in both call modes, reads all nine headers, and returns the transaction with no field lost or truncated. Read that acceptance narrowly: this fixture holds only ASCII bytes, so the codec named by `CHARSET` never had to decode anything, and the measurement therefore says nothing about what happens once a high byte appears.

## The rule

This case is covered by the shared rule, [Encoding](../../reading-rules.md#1-encoding), step 3: `8859-1` and `ISO-8859-1` both map to `iso-8859-1`. What is specific here is the mechanism to avoid: never build a codec name by string concatenation and never pass a raw header value to `codecs.lookup`. Match the normalised value against the table, and treat an unknown one as an unknown value, not as a codec error, so the failure names the header instead of the codec.

## Caveats

The bank is not named and the country is unknown, so nothing here says whether the spelling is one issuer's habit or a widespread one. Only the header block is sourced; the statement body is reconstructed from the shared template, the issue providing no transaction bytes. The three-value enumeration cited above is read off the `ofxtools` 1.1.1 error message, not off the OFX 1.0.2 specification, which nobody quotes in this corpus, so calling `8859-1` out of specification remains unconfirmed and the fault is not assigned to the bank.

Above all, the measurement does not reproduce what the source reports. The reporter says ofxparse tries `cp8859-1`; `ofxparse` 0.21 replayed today reads this fixture without complaint in both modes. Two explanations are open and neither is established: the behaviour may have changed since the 2019 report, or the failure may need a byte the fixture does not carry, since a pure ASCII payload never exercises the codec. The header deviation is attested by the quoted bytes; the downstream crash is not attested by this fixture, and isolating it would require a variant carrying a non-ASCII byte, which the source does not supply.
