# E*Trade: declares CHARSET:NONE, on which ofxparse builds a codec name that does not exist

- Bank: E*Trade
- Format: OFX 1.0.2 SGML
- Fixture: `charset-none-with-encoding-usascii.ofx`
- Sources: jseutter/ofxparse #171 (issue, opened 2023-02-26), jseutter/ofxparse #154 (issue, opened 2019-11-15), jseutter/ofxparse #163 (PR, opened 2021-02-07)
- Provenance: the pair `ENCODING:USASCII` / `CHARSET:NONE` is given approximately by #171 ("ETrade gives me an OFX file which has a line like"), which is the only source naming E*Trade, and literally by #154 ("The first few lines of the file are:"), which does not name its institution. Everything else in the fixture (the rest of the header block, the signon, the account block, the transaction, both balances) comes from the shared template `corpus/template/ofx-1.0.2.ofx`. The diff against the template is one line: `CHARSET:1252` becomes `CHARSET:NONE`. `VERSION:102` is the template's value; the file quoted in #154 carries `VERSION:160`, and no source states E*Trade's version.

## The deviation

The file declares `ENCODING:USASCII` and `CHARSET:NONE`. No bank emits a codec called `cpNONE`: the string `NONE` is a header value, and `ofxparse` turns it into a codec name by mechanical concatenation, `"cp%s" % cp`. The result, `cpNONE`, is not a Python codec, so `codecs.lookup` raises before a single byte of the statement body is read. The fault here is on the parser side: the fixture is pure ASCII, its body is exactly the template's, and the shared rules treat `NONE` as an expected value of `CHARSET` (see [../../reading-rules.md](../../reading-rules.md), section 1). Three separate reporters hit the same line over four years, which makes this a parser assumption rather than a bank quirk.

What the source says:

```
ENCODING:USASCII
CHARSET:NONE
```

And the traceback quoted in #154:

```
  File "/home/yates/.local/lib/python3.7/site-packages/ofxparse/ofxparse.py", line 125, in handle_encoding
    codec = codecs.lookup(encoding)
LookupError: unknown encoding: cpNONE
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | `LookupError: unknown encoding: cpNONE` |
| `ofxparse` 0.21, file opened in binary | `LookupError: unknown encoding: cpNONE` |
| `ofxtools` 1.1.1 | reads the file, 1 transaction, `TRNTYPE` `DEBIT`, `TRNAMT` `Decimal('-10.00')`, `FITID` `T0001` |

The failure is identical in both call modes, so opening the file in binary does not help here: the crash happens on the header value, before any decoding of the body. Neither of the two parsers loses data silently on this fixture, `ofxparse` fails loudly and `ofxtools` reads the statement in full. A hard failure is the least harmful of the two outcomes, but it still costs the whole statement over one header field, which is what the failure doctrine in [../../reading-rules.md](../../reading-rules.md) (section 0) rules out.

## The rule

Fully covered by the shared rule: [../../reading-rules.md](../../reading-rules.md), section 1 "Encoding", which maps `CHARSET:NONE` to cp1252 and forbids building a codec name by string concatenation on an unvalidated header value. Nothing in this case is specific enough to add to it. Worth recording for whoever implements that section: the two fixes proposed upstream do not agree on the codec string, #171 suggests `cp1252` and #163 suggests `1252`; Python resolves both to the same codec (`codecs.lookup("1252").name` is `cp1252`), so the disagreement is cosmetic.

## Caveats

- The bank name rests on #171 alone, and #171 introduces its two lines with "a line like", so the bytes it gives are an approximation. The literal bytes come from #154, which does not name its institution, and #163 says only "I've seen this in files from two different institutions". So "E*Trade" and "these exact bytes" are attested by two different sources, not by one.
- No country is asserted: no source states one.
- Whether `NONE` is a legal value of `CHARSET` in the OFX 1.x specification is not settled by the sources gathered here. None of the three quotes the specification text. The shared rules treat `NONE` as one of the three allowed values; that list is attested by the `ofxtools` error message (`is not OneOf ('ISO-8859-1', '1252', 'NONE')`), not by a reading of the specification. The classification of this case as "parser at fault" depends on it, and it stays to be confirmed against the specification text.
- The measurement does not contradict the sources: #154 reports `LookupError: unknown encoding: cpNONE` and that is word for word what `ofxparse` 0.21 raises today, in both call modes.
- The choice of cp1252 for `NONE` is a corpus decision, not a reading of the standard. `ofxtools` maps `NONE` to utf-8. The two only diverge on bytes above 0x7F, which this fixture does not contain, so this fixture cannot arbitrate between them.
- Only the `CHARSET` line comes from the sources. Any statement about E*Trade's version, account structure, amounts or dates would be a statement about the shared template, and none is made here.
