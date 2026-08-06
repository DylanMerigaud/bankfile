# LCL: a check transaction with no payee and no memo

- Bank: LCL (France)
- Format: OFX 1.0.2 SGML
- Fixture: `check-without-payee.ofx`
- Sources: jseutter/ofxparse #162 (issue, opened 2020-12-11)
- Provenance: from the source come the `<TRNTYPE>CHECK` value, the presence of a `<CHECKNUM>`
  child with no `<NAME>` and no `<MEMO>` alongside it, and the check number `1090381` quoted
  in the issue body. Everything else comes from the shared template
  (`../../template/ofx-1.0.2.ofx`): the nine header lines, the signon block, the account
  identifiers, the amount, the dates, the two balance blocks, and the `FITID` value `T0001`.
  The reporter's own `FITID` (`003 1090381`) was not carried over, so the fixture keeps the
  template one and the check number is the only value in the transaction that traces back to
  the bank. The diff against the template is exactly three lines: `DEBIT` becomes `CHECK`, and
  the `<NAME>` and `<MEMO>` pair is replaced by a single `<CHECKNUM>`.

## The deviation

The transaction carries `TRNTYPE` `CHECK` and identifies itself by check number only: no
`<NAME>`, no `<MEMO>`, nothing a consumer can print as a counterparty. The reporter reads this
as a file the parser mishandles ("its field payee is empty"), and a second participant answers
in the same thread that `CHECK` is a valid `TRNTYPE` and that the payee is optional, so the
file is fine and the parser should cope. Nothing in the quoted bytes violates the format, so
the deviation is on the expectation side: code written around `DEBIT` and `CREDIT` with a
human readable label attached assumes a shape that OFX never guaranteed. Neither participant
cites a line of the specification, so the "CHECK is valid, PAYEE is optional" reading rests on
one commenter's assertion, not on a text quoted here.

What the source says:

```
<STMTTRN>
<TRNTYPE>CHECK
<DTPOSTED>20190221
<TRNAMT>-19.87
<FITID>003 1090381
<CHECKNUM>1090381
</STMTTRN>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | reads, 9 headers, 1 transaction: type `check`, amount `-10.00`, date `2026-01-15`, payee `` (empty), memo `` (empty), checknum `1090381` |
| `ofxparse` 0.21, file opened in binary | identical: 9 headers, 1 transaction, payee `` (empty), memo `` (empty), checknum `1090381` |
| `ofxtools` 1.1.1 | reads, 1 transaction: `<STMTTRN(trntype='CHECK', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', checknum='1090381')>` |

None of the three readings raises. `ofxparse` accepts `CHECK` as a transaction type and reads
the check number back correctly, so the crash the issue title suggests does not happen on
these bytes today. What does happen is quieter: absent `<NAME>` and `<MEMO>` come back as
empty strings rather than as absent fields, so an importer that tests truthiness sees the same
thing as a tag present and blank, and a ledger line lands with no label and no signal that
anything is missing. `ofxtools` does not fabricate the fields at all, which is the behaviour to
copy.

## The rule

Nothing here needs a rule of its own on the type value: `TRNTYPE` is an open enumeration and an
unexpected value follows the failure doctrine, both written once in
[the shared reading rules](../../reading-rules.md), section 4 "Tags". `CHECK` is inside the
enumeration anyway, so it normalises straight through.

What is specific to this case is the label. When `NAME` and `MEMO` are both absent, the
normalised payee and memo must be null, never the empty string, per the same section 4 ("a tag
that is present but empty means ABSENT"), and the transaction must not be dropped for lacking
a counterparty. A renderer that needs something to show may derive a display label from
`CHECKNUM` when `TRNTYPE` is `CHECK` (for example `CHECK 1090381`), but that label belongs to
presentation and must not be written into the normalised payee field: a derived string that
looks like bank data is exactly the kind of plausible-but-invented value the doctrine forbids.

## Caveats

- The only bytes attested by the source are the six lines of the `STMTTRN` block quoted above.
  The rest of the fixture is the shared template, so the headers, the account, the currency,
  the amount, the dates and the balances say nothing about LCL.
- The source contradicts the measurement on the symptom. The issue is filed as a handling
  failure, and `ofxparse` 0.21 handles the file without error in both call modes; the only
  defect left is the empty string standing in for an absent field. If a real failure existed in
  2020, it is not reproducible on these bytes with this version, and the reporter never gave a
  traceback.
- "CHECK is a valid TRNTYPE and PAYEE is optional" comes from one commenter (fdinel,
  2020-12-14) pointing at the spec download page without quoting it. The classification of this
  file as conformant depends on that claim and has not been checked against the specification
  text.
- The country comes from the reporter naming his bank "LCL.FR" in the issue body. Nothing else
  in the sources attests it.
- `FITID` in the fixture is the template value `T0001`, not the reporter's `003 1090381`, so
  this fixture establishes nothing about identifiers that contain a space.
