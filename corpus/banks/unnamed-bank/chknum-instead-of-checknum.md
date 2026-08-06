# Unnamed bank: writes the check number in `<CHKNUM>`, not in `<CHECKNUM>`

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `chknum-instead-of-checknum.ofx`
- Sources: jseutter/ofxparse #173 (PR, opened 2023-11-27)
- Provenance: one line comes from the source, `<CHKNUM>1932`, taken from the unit test the PR adds (`testThatParseTransactionWithFieldChkNum`). Everything else (header block, signon, account block, amount, dates, payee, memo, balances) comes from the shared corpus template, and the diff between template and fixture is that single inserted line. No bank is named anywhere in the PR, no country is stated, and the PR contributes no bank file: the value `1932` is the author's own test data, not bytes read out of a statement.

## The deviation

Inside `<STMTTRN>`, the check number is carried by an element named `CHKNUM` instead of `CHECKNUM`, the name `ofxparse` looks for. The two are the same field: the PR author states it plainly and adds that he does not know why two names exist. Nothing else in the transaction is unusual, so a parser that only knows `CHECKNUM` reads the transaction end to end, finds every other field, and simply never sees the check number. Whose fault this is cannot be settled from this source: the PR does not quote the OFX specification, does not name the institution, and does not say which of the two spellings the format prescribes, so this note records `CHKNUM` as an observed alternate spelling and not as a violation by a bank. What can be said without a specification reading is that `ofxparse` supported exactly one of the two names before this PR, and that the PR was still open when the corpus was assembled.

What the source says:

```
+    def testThatParseTransactionWithFieldChkNum(self):
+        input = '''
+<STMTTRN>
+    <TRNTYPE>CHECK
+    <DTPOSTED>20231121
+    <TRNAMT>-113.71
+    <FITID>0000489
+    <CHKNUM>1932
+</STMTTRN>
```

The code change the PR proposes is a loop over both names:

```
+        for check_field in ('checknum', 'chknum'):
+            checknum_tag = txn_ofx.find(check_field)
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parses, 9 headers read, 1 transaction, type `debit`, amount `-10.00`, date `2026-01-15`, payee `ANON MERCHANT`, memo `ANON MEMO`, **checknum `` (empty)** |
| `ofxparse` 0.21, file opened in binary | identical: 9 headers read, 1 transaction, same fields, **checknum `` (empty)** |
| `ofxtools` 1.1.1 | parses, 1 transaction, recorded as `<STMTTRN(trntype='DEBIT', dtposted=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=<UTC>), trnamt=Decimal('-10.00'), fitid='T0001', name='ANON MERCHANT', memo='ANON` |

None of the three readings raises, and that is the problem. `ofxparse` 0.21 returns a complete-looking transaction whose `checknum` attribute is the empty string it was initialised with, so the check number is dropped with no exception, no warning, and no missing-field marker: a reconciliation that keys a check payment on its number gets nothing back and cannot tell an absent number from a lost one. Silent loss is worse than a crash here, because the statement still balances and nobody looks. The `ofxtools` result recorded in the measurement file is truncated at `memo=`, so this measurement establishes only that `ofxtools` 1.1.1 parses the file and returns one transaction; it establishes nothing about what `ofxtools` does with the `CHKNUM` element itself.

## The rule

This case is covered by the shared rules: an element name unknown to the reader is handled by the tag rule in [../../reading-rules.md](../../reading-rules.md), section 4 (Tags), which requires the unknown tag to be read, kept in the extension bag with its raw value, and never to disturb its siblings. What is specific here is only the mapping: `CHKNUM` is read as an alias of `CHECKNUM` and populates the same normalised check-number field, the comparison being made on the uppercased name as section 4 requires. If both `CHECKNUM` and `CHKNUM` appear in the same `<STMTTRN>`, take `CHECKNUM`, keep the other value in the extension bag, and warn; that combination is not attested by any source and the PR author explicitly doubts a file can carry both. An empty check number follows the shared rule that a present-but-empty tag means absent, never an empty string, which is precisely the value `ofxparse` returns today for a check number it failed to find.

## Caveats

- The bank is not named and no country is attested. The PR gives no statement file at all.
- The bytes are not bank bytes: `<CHKNUM>1932` is the author's unit-test input, so the fixture reproduces a spelling reported by a contributor rather than a file captured from an institution. `1932` is a plausible check number and is treated as non-personal test data.
- The claim that `CHKNUM` deviates from the OFX 1.0.2 element name is not supported by any specification text quoted in this note or in the source. The PR author writes "It's the same than `checknum`, I don't know why there are two names for the same thing", which is an admission of uncertainty, not an attribution of fault. This note therefore does not classify the case as bank-at-fault or parser-at-fault.
- The measurement contradicts nothing in the source, but it also confirms less than the source suggests: the PR describes adding support, and what we measure is only the before state, `ofxparse` 0.21 silently returning an empty `checknum`. Whether the merged form of the PR behaves as advertised is not measured here.
- The `ofxtools` entry is truncated in the measurement file, so the check-number behaviour of the second parser is unknown for this fixture and should be re-measured with the full repr before anyone cites it.
- The three table rows are two parsers in three call modes, not three parsers.
