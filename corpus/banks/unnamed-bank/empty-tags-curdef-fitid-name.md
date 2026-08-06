# Unnamed bank: elements present but empty on `CURDEF`, `FITID` and `NAME`

- Bank: unnamed (Australia)
- Format: OFX 1.0.2 SGML
- Fixture: `empty-tags-curdef-fitid-name.ofx` (pure ASCII)
- Sources: jseutter/ofxparse #81 (issue by sanderkruger, opened 2015-06-11), with the bytes and the traceback coming from the comments by bruny (2018-08-03 and 2018-08-09)
- Provenance: only the emptiness of three elements comes from the source. `<FITID></FITID>` and `<NAME></NAME>` are quoted literally in bruny's 2018-08-09 comment. `CURDEF` is not quoted as bytes anywhere: it appears in bruny's 2018-08-03 list of the fields his file leaves empty, and it is the field named in the traceback he pastes. Our fixture writes the three of them in the closed form used by the quoted extract, and changes nothing else: the diff against `../../template/ofx-1.0.2.ofx` is exactly three lines. The header block, the signon, the account identifiers, the dates, the balances and the memo are the template's and say nothing about this bank. `VERSION:102` is the template's value, but it happens to match the source, which states the files are "both using version 1.02 (SGML!)".

## The deviation

Three elements are written out with no content: the statement currency, the transaction identifier and the payee name. Nothing is missing from the structure, the tags are there, they simply carry no value. The reporters do not settle who is at fault and neither do we: sanderkruger asks for the tags to be ignored, bruny writes "I'm not sure whether this is actually valid, and whether the bank is at fault, or ofxparse should handle the case more gracefully?", and no source cited here quotes the OFX 1.0.2 text on empty elements. What the source does establish is an argument that stands on its own: a parser already reads these transactions when the fields are absent, so an empty field must cost no more than an absent one. That is the reading this corpus takes, and it is the shared failure doctrine, not a judgement on the bank.

What the source says:

```
<STMTTRN>
 <TRNTYPE>Credit</TRNTYPE>
 <DTPOSTED>20180801</DTPOSTED>
 <TRNAMT>0.0</TRNAMT>
 <FITID></FITID>
...
 <NAME></NAME>
...
 <CHECKNUM></CHECKNUM>
 <REFNUM></REFNUM>
 <MEMO>NEW INTEREST RATE  3.870%</MEMO>
...
</STMTTRN>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | `IndexError: list index out of range` |
| `ofxparse` 0.21, file opened in binary | `IndexError: list index out of range` |
| `ofxtools` 1.1.1 | `OFXSpecError: Can't set STMTTRN.fitid to None: String: Value is required` |

Nothing is read, in any of the three call modes. `ofxparse` dies on the first of the three empty elements it reaches, `CURDEF`, at the line the source itself pastes: `account.curdef = act_curdef.contents[0].strip()`, which indexes into an empty list of children. The exception is the same one the reporter had in 2018, and it is the same in text mode and in binary, so no encoding question is involved. `ofxtools` fails later and more explicitly: it does turn the empty element into `None`, which is the right normalisation, and then refuses it because its schema marks `FITID` as required. Both are hard failures rather than silent losses, which is the less dangerous of the two outcomes: no truncated figure reaches a reconciliation here, the whole statement is simply lost.

## The rule

The core of this case is covered by the shared rule, `../../reading-rules.md` section 4 "Tags": a tag that is present but empty means ABSENT, never an empty string, and never a crash. The self-closing spelling `<TAG/>` from the original 2015 report never reaches this step, it is neutralised earlier by the rule in `../onpoint-community-credit-union/self-closing-memo-tag.md`. Three points are specific to the three fields at hand:

- Empty `CURDEF`: look for a `CURRENCY` or `ORIGCURRENCY` on the transactions of the same `STMTRS` and take that value if they all agree. Otherwise leave the currency unset and warn. Never assume a default currency from the country, the language or the bank identifier.
- Empty `FITID`: the transaction has no stable identifier. Keep the transaction, mark it as having none, and let deduplication fall back to the other fields. Never synthesise an identifier that would look stable across imports, since two runs would then produce two different values for the same entry.
- Empty `NAME`: the payee stays null. `MEMO` is kept in its own field and is never promoted into the payee, because the two carry different things and a silent promotion makes the payee unreliable everywhere else.

## Caveats

- The bank is not named. Australia comes from bruny's own words about the files the quoted lines are taken from ("2 x separate OFX files from Australian banks"), and applies only to those files. The 2015 report that opens the issue is a different reporter with a different file, and no country is attested for it.
- `CURDEF` is the weakest of the three. Its bytes are never quoted: it is named in a list of empty fields and in a traceback. The element that actually breaks `ofxparse` in our measurement is therefore reproduced from a description, not copied from a quoted line.
- The quoted extract closes every element (`<TRNTYPE>Credit</TRNTYPE>`) in a file the same reporter calls v1.02 SGML. That mixed style is a second property of his file, and it is deliberately absent from our fixture, whose other elements keep the template's unclosed SGML form. Only the three empty elements were reproduced.
- The 2016 prediction in the issue, "My guess is that this will go away" after the merge of #108, is contradicted by the measurement: ten years later, the case still fails. PR #143, which bruny says "added fixes for some elements, still some others to go", is likewise not enough for these three, as measured on 0.21 today.
- The empty `CHECKNUM` and `REFNUM` of the quoted extract, and the non-standard `VALUEDATE`, `TRANSACTIONSPLIT`, `CATEGORY` and `ACCTBAL` around them, are separate deviations. They are catalogued elsewhere or left out on purpose, so that the diff between this fixture and the template carries this deviation and no other.
- The measurement is a single run on 2026-08-05, against `ofxparse` 0.21 and `ofxtools` 1.1.1. It says nothing about other versions of either library, and nothing about what happens when only one of the three elements is empty.
