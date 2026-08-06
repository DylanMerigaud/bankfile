# HSBC Brasil: a statement whose DTSTART carries a six digit day-month-year date

- Bank: HSBC Brasil (Brazil, named by the reporter in the first line of the issue)
- Format: OFX 1.0.2 SGML
- Fixture: `dtstart-ddmmyy.ofx`
- Sources: jseutter/ofxparse #58 (issue, opened 2013-10-10), one comment from the maintainer jseutter (2016-07-07)
- Provenance: the source quotes NO bytes from the HSBC Brasil file. It states in prose that the
  `BANKTRANLIST :: DTSTART` tag is in `%d%m%y` format, and it quotes the local patch its author
  applied to `ofxparse.py`. The value `010126` in our fixture is therefore a reconstruction: it is
  the template's `20260101` rewritten in the format the reporter describes, not a byte taken from a
  bank file. Everything else in the fixture, header block, signon, account block, the transaction,
  `DTEND`, both balance blocks, comes from the shared template `corpus/template/ofx-1.0.2.ofx`, and
  says nothing about HSBC Brasil.

## The deviation

The statement period start is written on six digits, day then month then two digit year, where the
OFX date type used everywhere else in the same file is `YYYYMMDD`. In the fixture, `DTSTART` reads
`010126` while `DTEND` two lines below reads `20260131`, so the two bounds of the same period are
written in two different formats inside one aggregate. Six digits are ambiguous on their own: read
as `DDMMYY` the value is 1 January 2026, read as `YYMMDD` it is 26 January 2001, and nothing in the
bytes decides between the two. Only the reporter's sentence does. Whether this is a spec violation
by the bank is not established here: no source in this corpus quotes the OFX 1.0.2 text on the date
type, and the only machine judgement we have is `ofxtools` refusing the value (see Caveats).

What the source says:

```
The HSBC Brasil ofx file parse fail because BANKTRANLIST :: DTSTART tag is in %d%m%y format.

The error happens on ofxparse.py line 396. I fixed locally by changing to this code:

        try:
            return datetime.datetime.strptime(
                ofxDateTime[:8], '%Y%m%d') - timeZoneOffset
        except:
            return datetime.datetime.strptime(
                ofxDateTime[:6], '%d%m%y') - timeZoneOffset
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | ok, 9 headers read, 1 transaction, first transaction debit -10.00 dated 2026-01-15, payee `ANON MERCHANT` |
| `ofxparse` 0.21, file opened in binary | ok, 9 headers read, 1 transaction, identical to the text mode result |
| `ofxtools` 1.1.1 | `OFXSpecError: Can't set BANKTRANLIST.dtstart to 010126: '010126' does not conform to OFX formats for <class 'datetime.datetime'>` |

The two parsers split. `ofxtools` rejects the whole statement over one date bound, which is exactly
the disproportionate failure the corpus argues against: every entry in the file is sound and none of
them is returned. `ofxparse` 0.21 does not raise today, thirteen years after the report, and still
returns the transaction. What our harness does NOT record is the value `ofxparse` gave to the
statement start date, so this measurement establishes that no exception is raised, and nothing about
whether the period start came out right, wrong, or absent.

## The rule

Fully covered by the shared rules: see [Dates](../../reading-rules.md#5-dates) in
`corpus/reading-rules.md`. Exactly six digits is the `DDMMYY` branch, read that way because this
fixture is the one attested case, with a warning attached because a two digit year is never certain.
Nothing here is specific enough to justify a local rule, and in particular the exception based
fallback proposed in the issue is not the rule this corpus adopts: it guesses silently, where the
shared rule requires the warning to travel with the value. Any other length, and an empty value,
falls in the same section: bound left null, named warning, transactions still parsed, no hard
failure.

## Caveats

- The bytes are reconstructed. No fragment of the HSBC Brasil file appears in the issue, so the
  fixture illustrates a described property, not a captured one. The specific value `010126` is ours.
- The source and the measurement disagree. The reporter says the file fails to parse at
  `ofxparse.py` line 396; on 2026-08-05, `ofxparse` 0.21 parses this fixture without raising, in both
  text and binary mode. Either the line the report points at has changed since 2013, or the real
  file carried something our reconstruction does not. The failure described in the issue is not
  reproduced here.
- The measurement does not expose the parsed statement start date, so `ofxparse` may well be
  producing a wrong or missing period start in silence. That case would be worse than the crash the
  issue reports, and this corpus has not measured it. A harness that records `DTSTART` after parsing
  would settle it.
- `DDMMYY` is attested by one person, once, in 2013, and the maintainer left the issue open in 2016
  without confirming it on a file of his own.
- The claim that six digits violate the OFX date type rests on the `ofxtools` error message and on
  the reporter's framing. The OFX 1.0.2 specification text has not been read for this note, so the
  bank is not formally established to be at fault.
