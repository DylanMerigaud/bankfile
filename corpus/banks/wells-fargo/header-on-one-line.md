# Wells Fargo: the nine OFX headers are written on a single line, with no newline between them

- Bank: Wells Fargo
- Format: QFX (the header declares `DATA:OFXSGML` and `VERSION:102`, so OFX 1.0.2 SGML)
- Fixture: `header-on-one-line.qfx`
- Sources: jseutter/ofxparse #172 (PR, opened 2023-08-04), comment by jeanralphaviles on the same PR (2024-02-08)
- Provenance: the header line is the deviation and it comes straight from the source. The PR body quotes it, and the code comment inside the PR diff repeats it byte for byte. Everything else in the fixture (the `<OFX>` body, the signon block, the account identifiers, the single transaction, both balance blocks) comes from the shared corpus template `corpus/template/ofx-1.0.2.ofx` and says nothing about Wells Fargo. The diff between the template and this fixture is exactly nine lines becoming one, nothing else. The wording "Wells Fargo checking .qfx" is the reporter's, and it is the only thing that attaches these bytes to a named bank.

## The deviation

An OFX 1.x file starts with a block of `KEY:VALUE` headers, one per line, before the first `<`. This file puts all nine of them on one physical line: `OFXHEADER:100` is immediately followed by `DATA:OFXSGML`, which is immediately followed by `VERSION:102`, and so on to `NEWFILEUID:NONE`. Nothing separates the value of one header from the key of the next, so a reader splitting the block line by line gets a single line carrying nine colons instead of one. Recovering the pairs is only possible by knowing the key names in advance, and the PR author says so himself: his fix inserts a newline before each known key, and he warns that an unknown key would be swallowed into the preceding value. The file is the outlier here, since it destroys the separator the format uses to delimit its own headers. The crash is on the parser's side: losing the header block should downgrade what is known about the file, not kill the read.

What the source says:

```
OFXHEADER:100DATA:OFXSGMLVERSION:102SECURITY:NONEENCODING:USASCIICHARSET:1252COMPRESSION:NONEOLDFILEUID:NONENEWFILEUID:NONE
```

The PR's own comment on the fix:

```
When such a header is found, insert a newline before each known key. If unknown key:values
are added, they will end up appended to the preceding value and throw "ValueError: too many
values to unpack" on the line.split() a few lines down.
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | `ValueError: too many values to unpack (expected 2)` |
| `ofxparse` 0.21, file opened in binary | `ValueError: too many values to unpack (expected 2)` |
| `ofxtools` 1.1.1 | reads the file, 1 transaction, `trntype='DEBIT'`, `trnamt=Decimal('-10.00')`, `fitid='T0001'` |

The two `ofxparse` calls fail identically, so opening in binary buys nothing here: the failure is in the header split, not in decoding. This is a loud failure, not a silent one, which makes it less dangerous than the header cases in this corpus where `ofxparse` returns zero headers instead of nine and the file only breaks much later. `ofxtools` 1.1.1 reads the same bytes without complaint, which shows the body is sound and that "unreadable" is a property of one parser on this file, not of the file.

## The rule

The end of the header block, the tolerance for blank lines, and the untrusted-header fallback are the shared rule: see [reading rules, section 2, "Where the header block ends (OFX 1.x)"](../../reading-rules.md) and section 0 for the failure doctrine. What this case adds: inside that block, do not assume a newline separates headers. Cut the block on the known OFX 1.x key names (`OFXHEADER`, `DATA`, `VERSION`, `SECURITY`, `ENCODING`, `CHARSET`, `COMPRESSION`, `OLDFILEUID`, `NEWFILEUID`) whenever a physical line carries more colons than it carries keys, then parse each fragment as `KEY:VALUE`. If a fragment does not fit its expected domain after the re-cut, do not fail: mark the header as untrusted, drop the suspect value, apply the format defaults (`VERSION` 102, `DATA` OFXSGML, `CHARSET` 1252) and report the reconstructed header in the import report. The SGML body is still parsed. An unknown key in a collapsed header is precisely the case the PR cannot handle, so it must degrade to the untrusted-header path rather than raise.

## Caveats

- The source does not describe the symptom of the unpatched parser on this file. The `ValueError: too many values to unpack` it mentions is the residual behaviour of the proposed fix when facing an unknown key. Our measurement establishes independently that `ofxparse` 0.21 raises that same exception on the collapsed header, which is consistent with the PR's diagnosis without being a confirmation of its text.
- "Wells Fargo" and "checking account" rest on one reporter's sentence. No account statement, no file, and no country is attested by the source, and the bytes themselves carry no bank identity.
- The `<OFX>` body of the fixture is the corpus template, not Wells Fargo bytes. Any claim about the body of a real Wells Fargo file would be unfounded.
- Whether OFX 1.0.2 explicitly requires one header per line is not established here: no line of the specification is quoted in the source or in this note. What is established is that both parsers and the PR author treat the block as line-oriented.
- The PR is dated 2023-08-04 and a commenter was still recommending a `sed` pre-processing workaround on 2024-02-08, which suggests it was not merged by then. Its current merge status was not checked on 2026-08-05.
