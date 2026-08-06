# Unnamed bank: a transaction type written in mixed case, with an explicit end tag

- Bank: unnamed
- Format: OFX 1.0.2 SGML
- Fixture: `mixed-case-trntype.ofx` (pure ASCII)
- Sources: jseutter/ofxparse #81 (issue by sanderkruger, opened 2015-06-11), specifically the comment by bruny of 2018-08-09 quoting two `STMTTRN` blocks from his own bank files
- Provenance: one line comes from the source, `<TRNTYPE>Credit</TRNTYPE>`, quoted literally by bruny inside a full `STMTTRN` block that he says comes from an Australian bank exporting OFX 1.02 SGML. Our fixture substitutes that single line for the template's `<TRNTYPE>DEBIT`, and nothing else: the diff against `../../template/ofx-1.0.2.ofx` is exactly one line. Everything else (the header block, the signon, `VERSION:102`, the account identifiers, the amount, the dates, the two balance blocks) is template and says nothing about this bank. In particular, the negative sign on `<TRNAMT>-10.00` is the template's, and it contradicts the `Credit` type: that mismatch is our artefact, not something the source shows.

## The deviation

The source file writes the transaction type as `Credit`, mixed case, where every other file in this corpus writes an all-caps token such as `DEBIT` or `CREDIT`. The same line also closes the element explicitly, `</TRNTYPE>`, instead of leaving it open in the SGML style that OFX 1.x files usually use. Fault cannot be assigned from the bytes available here: no source gathered for this corpus quotes the OFX 1.0.2 text on whether the `TRNTYPE` enumeration is case sensitive, and the reporter himself declines to decide, writing "I'm not sure whether this is actually valid, and whether the bank is at fault, or ofxparse should handle the case more gracefully". What is established is that a real exporter ships this form and that the two libraries disagree about it, which is the reason the case belongs in the corpus at all.

What the source says:

```
<STMTTRN>
 <TRNTYPE>Credit</TRNTYPE>
 <DTPOSTED>20180801</DTPOSTED>
 <TRNAMT>0.0</TRNAMT>
...
 <MEMO>NEW INTEREST RATE  3.870%</MEMO>
</STMTTRN>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | parsed, 9 headers read, 1 transaction, `type` `credit`, amount `-10.00` |
| `ofxparse` 0.21, file opened in binary | parsed, 9 headers read, 1 transaction, `type` `credit`, amount `-10.00` |
| `ofxtools` 1.1.1 | fails: `OFXSpecError: Can't set STMTTRN.trntype to Credit: 'Credit' is not OneOf ('CREDIT', 'DEBIT', 'INT', 'DIV', 'FEE', 'SRVCHG', 'DEP', 'ATM', 'POS', 'XFER', 'CHECK', 'PAYMENT', 'CASH', 'DIRECTDEP', 'DIRECTDEBIT', 'REPE` |

The two parsers in the three call modes split cleanly on this file. `ofxparse` reads it in both modes, keeps all nine headers, and returns the type lowercased to `credit`, which is the same value it returns for the template's `DEBIT` line lowercased to `debit`, so nothing is lost. `ofxtools` refuses the whole file over that one token: a statement whose amount, date, payee and memo are all sound is rejected because one enumerated value is not upper case. Nothing here is silently truncated, so the failure mode is a visible crash rather than a wrong figure entering a reconciliation.

## The rule

This case is covered by the shared rules, `../../reading-rules.md` section 4 "Tags", which already states that `<TRNTYPE>Credit` and `<TRNTYPE>CREDIT` are the same tag and the same value, and that a value outside an enumeration keeps its raw form, sets the normalised type to `OTHER` and raises a warning rather than an exception. Two points specific to this file. First, the comparison must be done on the value after stripping surrounding whitespace and upper casing it, before any enumeration lookup, otherwise `Credit` never reaches the table that would have matched it. Second, the explicit end tag `</TRNTYPE>` must be accepted in an SGML-style OFX 1.x body and must not become part of the value: the reader has to treat an end tag as optional on both sides, present or absent, and neither form changes what the field means. An unrecognised type never fails the file, per section 0.

## Caveats

- Fault is not established. Whether OFX 1.0.2 requires `TRNTYPE` to be upper case has not been checked in the specification text, and no source cited here quotes it. The list of allowed values reproduced above comes from the `ofxtools` error message, not from a reading of the standard. Any statement that this bank is out of spec, or that `ofxparse` is right to accept the file, depends on that unverified point.
- The bank is not named. The reporter of the comment says only "Australian banks", plural, about the two files he offers as test cases, and does not tie either one to a named institution. No country claim is made in the note header for that reason.
- The fixture carries two changes inside one line, the mixed case and the explicit end tag. The measurement therefore cannot tell which of the two `ofxtools` chokes on, though its error message names the value and not the markup, and it cannot tell whether `ofxparse` would still succeed with only one of the two present.
- The source line lives inside a `STMTTRN` that also carries empty `FITID`, `NAME`, `CHECKNUM` and `REFNUM` fields and four tags outside the spec. Those are catalogued as their own fixtures (`empty-tags-curdef-fitid-name.ofx`, `tags-outside-spec.ofx`) and are deliberately absent here, so that the diff against the template carries this deviation and no other.
- The `Credit` type sitting on a negative amount is an artefact of our reconstruction. The source transaction has `<TRNAMT>0.0`; the `-10.00` is the template's.
- Issue #81 opened on a different symptom, empty tags written as `<FI><ORG/><FID/></FI>`, and the mixed-case type appears only in a comment three years later. The forecast left in the issue in 2016, that merging #108 would make the problem go away, is contradicted for the empty-tag part of the report by the 2018 stack trace and, ten years later, by our own measurements on the sibling fixtures.
- The measurement is a single run on 2026-08-05, against `ofxparse` 0.21 and `ofxtools` 1.1.1. It says nothing about other versions of either library.
