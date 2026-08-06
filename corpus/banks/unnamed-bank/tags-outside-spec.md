# Unnamed bank: four vendor tags inside `STMTTRN` that the OFX 1.0.2 specification does not define

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `tags-outside-spec.ofx`
- Sources: jseutter/ofxparse #81 (issue, opened 2015-06-11), specifically the comment by bruny of 2018-08-09
- Provenance: from #81 come the four element names and their values, `<VALUEDATE>20180801</VALUEDATE>`, `<TRANSACTIONSPLIT>No</TRANSACTIONSPLIT>`, `<CATEGORY>Uncategorised</CATEGORY>` and `<ACCTBAL>-400.52</ACCTBAL>`, together with their position inside the transaction aggregate. The reporter states the file is version 1.02 SGML and that the two statements he works from come from Australian banks, without naming either. Everything else in the fixture (the nine header lines, the signon block, the account identifiers, the transaction amount and dates, both balance blocks) comes from the shared template `corpus/template/ofx-1.0.2.ofx`. The diff against the template is exactly four added lines, 48 and 50 to 52, inserted between `<FITID>T0001` and `<MEMO>ANON MEMO`. The dates in the fixture are the template's, not the source's; only the four names and the three literal values `No`, `Uncategorised`, `-400.52` are the source's.

## The deviation

The transaction aggregate carries four child elements that the OFX 1.0.2 specification does not define for `STMTTRN`: `VALUEDATE`, `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL`. They sit between the standard fields, before `MEMO`, so a standard element follows them and a reader that mishandles them can shift its reading of what comes after. Adding vendor elements to a standard aggregate is a departure on the bank's side, and here it is established on bytes the source quotes rather than inferred from the template. The failure it can cause, though, is a parser failure: reading `ACCTBAL` (a running account balance carried per transaction) as if it were a transaction amount, or letting an unknown name interrupt the walk over the aggregate, both produce a wrong figure out of a file that is otherwise readable.

What the source says:

```
<STMTTRN>
 <TRNTYPE>Credit</TRNTYPE>
 <DTPOSTED>20180801</DTPOSTED>
 <TRNAMT>0.0</TRNAMT>
 <FITID></FITID>
 <VALUEDATE>20180801</VALUEDATE>
 <NAME></NAME>
 <TRANSACTIONSPLIT>No</TRANSACTIONSPLIT>
 <CATEGORY>Uncategorised</CATEGORY>
 <ACCTBAL>-400.52</ACCTBAL>
...
 <MEMO>NEW INTEREST RATE  3.870%</MEMO>
...
</STMTTRN>
```

The lines replaced by the ellipses are `<CHECKNUM></CHECKNUM>`, `<REFNUM></REFNUM>` and the `CURRENCY` aggregate. They carry the empty-tag deviation of the same issue, which is the subject of `empty-tags-curdef-fitid-name.md`, not of this note. The fixture here keeps every standard field filled so that the vendor tags are the only variable.

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | reads, 9 headers, 1 transaction: type `debit`, amount `-10.00`, date `2026-01-15 00:00:00`, payee `ANON MERCHANT`, memo `ANON MEMO`, checknum `` (empty) |
| `ofxparse` 0.21, file opened in binary | identical: reads, 9 headers, 1 transaction, amount `-10.00`, memo `ANON MEMO` |
| `ofxtools` 1.1.1 | reads, 1 transaction: `<STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT', memo='ANON` |

Neither parser fails, and neither shifts a field: the amount stays `-10.00` and does not pick up the `-400.52` of `ACCTBAL`, the date stays the `DTPOSTED`, and the nine headers are read in both call modes. So on this construct the tolerant behaviour is already there in both parsers today. What the measurement does not show is the four values coming back out: nothing in either result carries `No`, `Uncategorised` or `-400.52`, so they are dropped silently. That is a loss without an alarm, small here because the fields are informational, but it is the same silence that would hide a bank putting a fee or a value date into a name of its own.

## The rule

Covered by [`../../reading-rules.md`](../../reading-rules.md), section 4 (Tags): an unknown tag inside a known aggregate is read, skipped, and stored in an extension bag (name, raw value) attached to that aggregate; it never interrupts the reading of its siblings and never shifts the standard fields that follow it. Specific to this case, and worth naming because the name invites the mistake: `ACCTBAL` is not a transaction amount and must never feed `TRNAMT`, nor a balance field. `VALUEDATE` is not `DTPOSTED` and must not be promoted into a date field either, even though OFX has `DTAVAIL` for a comparable notion. All four go into the extension bag under their raw names, and nothing is guessed from a name that merely looks familiar.

## Caveats

- The bank is not named. The source says only that the two files he holds come from Australian banks, both OFX version 1.02 SGML, and this extract is one of the two. Which of the two banks produced this transaction is not stated, so no country is claimed in the header of this note.
- The source does not claim these four tags are out of specification. bruny writes about the empty fields and says he is "new to OFX file formats" and unsure "whether the bank is at fault". The out-of-specification reading of `VALUEDATE`, `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL` is ours, from the OFX 1.0.2 list of `STMTTRN` children, not something the issue asserts.
- The measurement contradicts the source's framing. Issue #81 exists because a file fails to parse, and the traceback it carries, `IndexError: list index out of range` at `account.curdef = act_curdef.contents[0].strip()`, is raised by an empty `CURDEF` element, not by any of these four tags. On our fixture, which isolates the vendor tags from the empty tags, `ofxparse` 0.21 does not raise at all. Nothing in the issue attributes a failure to these tags; they are recorded here as an attested file property whose current cost is silent loss rather than a crash.
- The four values are not merely absent from the parsed objects, they are absent from what the run recorded. The `ofxtools` repr in the measurement file is truncated mid-`memo`, so we cannot tell from it whether `ofxtools` retains the unknown elements anywhere on the parsed object; what is established is that it did not fail and returned the standard fields intact.
- The empty `checknum` returned by `ofxparse` is not a loss here: the fixture carries no `CHECKNUM` element at all. It is worth recording because it means an absent tag and an empty tag are indistinguishable in that output, which is the point shared rule 4 addresses.
- The values are the source's but the transaction around them is ours: the template's `DEBIT`, `-10.00` and January 2026 dates replace the source's `Credit`, `0.0` and August 2018. The `-400.52` of `ACCTBAL` is therefore inconsistent with the `90.00` balances of the template. That is an artefact of reconstruction, not a property of the bank's file.
- Per the audit of the previous pass, the four lines sit before `MEMO`, as the source shows, so a standard element follows them and the field-shift risk is actually testable on the fixture. The earlier version of this note placed them after `MEMO` and omitted `ACCTBAL`; both are corrected here.
- The measurement covers two parsers in three call modes, not three parsers.
