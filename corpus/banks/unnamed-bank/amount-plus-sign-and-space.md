# Unnamed bank: an amount with a leading plus sign and a space between the thousands

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `amount-plus-sign-and-space.ofx` (pure ASCII)
- Sources: jseutter/ofxparse #173 (pull request by ludo-c, opened 2023-11-27)
- Provenance: one digit string comes from the source, `+1 006,60`, and it is a unit test input written by the PR author, not bytes quoted from a bank file. The PR quotes no bank file at all. Our fixture substitutes that string into the `TRNAMT` of the shared template and changes nothing else: the diff against `../../template/ofx-1.0.2.ofx` is exactly one line. The space in it is an ordinary ASCII space (0x20), not U+00A0. Everything else (the header block, the signon, the account identifiers, the dates, the `DEBIT` type, both balance blocks) is template and says nothing about any bank.

## The deviation

The amount is written `+1 006,60`: an explicit positive sign, a space grouping the thousands, and a comma as the decimal separator. Three departures from the plain `1006.60` that a parser expects, stacked in one field. Fault cannot be assigned here. The source is a patch to the library plus the tests that cover it, so there are no bank bytes to weigh, and no source cited in this corpus quotes the OFX 1.0.2 text on the `amount` type. What the PR does establish is that its author met the form in practice: the two lines he adds to `toDecimal` carry the comments `# Handle 1 025,53 formatted numbers` and `# Handle +1058,53 formatted numbers`, which are not the values of any test in the diff.

What the source says, from `testThatParseTransactionWithSpaces`:

```
+    def testThatParseTransactionWithSpaces(self):
+        " Parse numbers with a space separating the thousands. "
...
+ <TRNAMT>+1 006,60
...
+        self.assertEqual(Decimal('1006.60'), transaction.amount)
```

and from the patch to `OfxParser.toDecimal`:

```
+        # Handle 1 025,53 formatted numbers
+        d = d.replace(' ', '')
+        # Handle +1058,53 formatted numbers
+        d = d.replace('+', '')
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parsed, 9 headers read, 1 transaction, amount `1006.60` |
| `ofxparse` 0.21, file opened in binary | parsed, 9 headers read, 1 transaction, amount `1006.60` |
| `ofxtools` 1.1.1 | fails, `InvalidOperation: [<class 'decimal.ConversionSyntax'>]` |

The two readings of `ofxparse` agree and lose nothing: the space and the plus are stripped, the comma is read as the decimal separator, and the value comes out as one thousand and six point six, not as one or as 1006 60. `ofxtools` 1.1.1 does not degrade the value, it refuses the whole file: one unparsable amount costs every transaction and both balances. That is a loud failure, so it is the better of the two failure shapes, but a statement that cannot be read at all is still a statement nobody can reconcile.

## The rule

This case is fully covered by the shared rule, `../../reading-rules.md` section 3 "Amounts": step 1 strips the spaces, step 2 strips the leading `+`, step 4 reads the lone comma as the decimal separator. Nothing here departs from it. Two points specific to this file. First, the group after the comma is two digits, so the ambiguity warning of step 4 (which fires on a group of exactly three, like `2,000`) does not apply and the value is not in doubt. Second, the space stripping must cover U+00A0 and U+202F as well as the ASCII space, since a thousands separator typed in a locale-aware exporter is often one of those: our fixture only exercises the ASCII one.

## Caveats

- No bank file is quoted by the source. `+1 006,60` is a value the PR author wrote inside a unit test to describe a form he says he met, and the corpus has no bytes from the exporter that produced it. Nothing in this note attributes anything to a named institution, and no country can be inferred: the space-and-comma grouping is used across much of continental Europe and beyond.
- The PR is not primarily about amounts. #173 is titled "Handle `chknum` in transaction field" and its stated purpose is the `chknum` alias for `checknum`, catalogued separately as `chknum-instead-of-checknum.ofx`. The amount handling rides along in the same diff.
- Measurement against source: `ofxparse` 0.21 as installed today already returns `1006.60` on this file, so the behaviour the PR asks for is present in the version we measure. Whether that is because this patch landed, because an equivalent change landed, or for another reason is not established by the sources gathered here. The PR's own diff bumps `__version__` from `0.18` to `0.21`, so its base is older than the release we measure and the two `0.21` labels do not designate the same code.
- The transaction carries `TRNTYPE` `DEBIT` while the measured amount is positive. That combination is an artefact of our reconstruction: the type is the template's and the amount is the source's. It is not an attested property of any file.
- The measurement is a single run on 2026-08-05, on `ofxparse` 0.21 and `ofxtools` 1.1.1. It says nothing about other versions, and nothing about how either library treats the same notation inside `BALAMT`, which the harness does not report.
