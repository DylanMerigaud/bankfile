# Unnamed bank: OFX 2.x file whose encoding lives in the XML declaration

- Bank: unnamed
- Format: OFX 2.x XML (`OFXHEADER="200" VERSION="202"`)
- Fixture: `xml-declaration-ofx-2.ofx` (utf-8)
- Sources: jseutter/ofxparse #133 (issue, opened 2017-11-28), with confirming comments from alexis-via (2021-05-17), dev590t (2023-07-06) and kbauer (2025-08-23)
- Provenance: the two head lines of the fixture are an illustrative header written by the reporter ("However, a typical header is:"), not bytes extracted from a bank file, and nim-odoo attaches no file to the issue. The only real file byte quoted anywhere in the issue is the accented payee `<NAME>Direction Générale des Finances </NAME>` from the 2021 comment, which is the single file-in-hand testimony in the thread. Everything else in the fixture (tree, amounts, dates, account identifiers, balance blocks) is the shared corpus template mechanically transposed to XML. The only two departures from that template are the XML and OFX processing instructions on lines 1 and 2, and the accented payee `ANON ÉNERGIE`, which stands in for the accented name of the 2021 comment.

## The deviation

The file is a well formed OFX 2.x document. Its encoding is declared where the OFX 2.2 specification says it must be declared, in the standard XML declaration on the first line, and the OFX processing instruction that follows carries only `OFXHEADER`, `VERSION`, `SECURITY`, `OLDFILEUID` and `NEWFILEUID`, with no `ENCODING` and no `CHARSET` attribute. Nothing here is a bank departing from a spec. The departure is on the parser side: `ofxparse` looks for the OFX 1.x `key:value` header block, finds none in an XML document, and falls back to ASCII. The reader who patches this must not record it against the issuing institution.

What the source says:

```
<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
```

and, from the 2021 comment, the real payee that broke a real file:

```
<NAME>Direction Générale des Finances </NAME>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc9 in position 992: ordinal not in range(128)` |
| `ofxparse` 0.21, file opened in binary | `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 992: ordinal not in range(128)` |
| `ofxtools` 1.1.1 | 1 transaction, `trntype='DEBIT'`, `dtposted=2026-01-15`, `trnamt=Decimal('-10.00')`, `fitid='T0001'`, `name='ANON ÉNERGIE'` |

Both `ofxparse` paths fail at the same offset, on the first byte of the accented payee, and both fail as ASCII: opening the file in binary does not save this case, because the declared utf-8 never reaches the codec selection at all. The differing byte between the two rows is the only trace of the path taken: in text mode the decoded character is re-encoded to latin-1 before the ASCII decode (`0xc9`), in binary the raw utf-8 lead byte survives (`0xc3`). `ofxtools` reads the same file and returns the payee with its accent intact, which establishes that the file itself is sound.

## The rule

Fully covered by the shared rules, [Encoding](../../reading-rules.md#1-encoding), branch 1: for an OFX 2.x document the encoding comes from the XML declaration, not from a `key:value` header block. The one point specific to this case: the absence of an OFX 1.x header block in such a file is normal and must never trigger the untrusted-header path of section 2, nor an ASCII fallback. Detect the XML document on the leading `<?xml` (the OFX processing instruction may also carry `OFXHEADER="200"`), take the encoding from the declaration, and default to utf-8 when the declaration omits it, as XML itself requires.

## Caveats

- The bank is not named and no country is attested. The 2021 comment quotes a French language payee, which suggests a French issuer for THAT reporter's file, but that file is not this fixture and the inference is not carried into the note.
- The fixture's two head lines are reconstructed from an illustrative header, so `VERSION="202"` is the reporter's example value, not a version observed in the wild. alexis-via reports `VERSION="220"` with the same failure, so the deviation does not depend on the minor version.
- No measurement in `corpus/measurements/2026-08-05.json` records a header count for this fixture, so the note does not assert one. The claim that `read_headers()` ends with an empty `OrderedDict` on an OFX 2.x file comes from alexis-via's reading of the code in the issue, not from our replay.
- Source and measurement agree on the symptom class (an ASCII `UnicodeDecodeError` on an accented byte) but not literally: the message quoted in 2021 names byte `0xe9` at position 3636 in that reporter's own file, ours names `0xc9`/`0xc3` at position 992 in this fixture. The offsets and bytes are properties of the respective files, not of the bug.
- The issue was open at the time of writing and the proposed lxml patch was never merged, so a future `ofxparse` release may change these results. The dates in the fixture (January 2026) are template values and carry no meaning.
