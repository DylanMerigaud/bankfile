# OnPoint Community Credit Union: an empty MEMO written in the self-closing form `<MEMO/>`

- Bank: OnPoint Community Credit Union
- Format: OFX 1.0.2 SGML
- Fixture: `self-closing-memo-tag.ofx`
- Sources: jseutter/ofxparse #167 (issue, opened 2022-04-24), jseutter/ofxparse #81 (issue, opened 2015-06-11)
- Provenance: from #167 come the token shape `<MEMO/>` and the bank, which the reporter names only by its domain, onpointcu.com. From #81 comes the same construct on other tags, quoted as `<FI><ORG/><FID/></FI>`. Everything else in the fixture (the nine header lines, the signon block, the account identifiers, the amounts, the dates, both balance blocks) comes from the shared template `corpus/template/ofx-1.0.2.ofx`. The single line that differs from the template is line 49: the template writes `<MEMO>ANON MEMO`, the fixture writes `<MEMO/>`. No byte of the real OnPoint file is reproduced here beyond the tag form itself.

## The deviation

The file carries a transaction whose `MEMO` element has no value, and writes that absence in the XML self-closing form `<MEMO/>` instead of omitting the element. A tokeniser that splits on `</?[a-z0-9_.]+>` sees a token that starts with `<` but not with `</`, so it classifies `<MEMO/>` as an opening tag with no matching close, and the SGML repair pass that inserts the missing close tags works on a wrong premise. Who is at fault depends on a version this source never states: if the OnPoint file declares an OFX 1.x version, its body is SGML and the self-closing form is out of specification for it; if it declares 2.x, the form is plain valid XML and the parser is simply wrong. The `VERSION:102` line in our fixture comes from the shared template, not from OnPoint, so it establishes nothing about that file. The reporter himself declines to assign fault, and asks for a parser that does not fault either way.

What the source says:

```
tokens that look like <MEMO/> cause OfxPreprocessedFile() to set is_closing_tag=false and
is_open_tag=true which, in turn causes re.findall() to fault. This flavor of token appears
in the ofx file from my credit union, onpointcu.com. It may be encoded wrong, but the right
fix would be a better parse code that does not allow the code to fault.
```

Issue #81 quotes the same construct on other elements:

```
<FI><ORG/><FID/></FI>
```

## Measured 2026-08-05

| parser | result |
|---|---|
| `ofxparse` 0.21, file opened in text mode (documented usage) | reads, 9 headers, 1 transaction: type `debit`, amount `-10.00`, date `2026-01-15 00:00:00`, payee `ANON MERCHANT`, memo `` (empty), checknum `` (empty) |
| `ofxparse` 0.21, file opened in binary | identical: reads, 9 headers, 1 transaction, memo `` (empty) |
| `ofxtools` 1.1.1 | `OFXSpecError: Can't set STMTRS.ledgerbal to None: SubAggregate: Value is required` |

`ofxparse` 0.21 does not fault on this fixture in either call mode: it reads the nine headers and returns the transaction with its other fields intact. `ofxtools` 1.1.1 is the one that rejects the file, and its message names `LEDGERBAL`, an aggregate that is present and complete in the fixture (`<BALAMT>90.00`, `<DTASOF>20260131`), which places the damage somewhere upstream of the element it complains about rather than on `MEMO` itself. That error is specific to this fixture: no other fixture in the 2026-08-05 run produces it. The empty memo comes back as an empty string rather than as an absent field, which is the failure mode shared rule 4 exists to prevent.

## The rule

Fully covered by [`../../reading-rules.md`](../../reading-rules.md), section 4 (Tags): the self-closing form `<TAG/>` is normalised into an empty tag before extraction, and a tag that is present but empty means ABSENT, never an empty string and never a crash. Nothing here is specific to OnPoint beyond the element on which the form was observed, so this note adds no rule of its own. The normalisation happens in the tokenising pass, before the empty-value handling described in `unnamed-bank/empty-tags-curdef-fitid-name.md`, which is why that note does not have to list the self-closing form again.

## Caveats

- The measurement contradicts the source on the crash. #167 reports that `OfxPreprocessedFile()` faults on `<MEMO/>`; on 2026-08-05, `ofxparse` 0.21 parses our fixture in both call modes without raising. Our harness calls `OfxParser.parse`, the documented entry point, and we did not check whether that entry point routes through `OfxPreprocessedFile` in 0.21, nor did we test the constructor the issue names directly. So the reported fault is neither reproduced nor refuted; what is established is that the documented usage no longer breaks on this construct.
- The version of the real OnPoint file is not attested. `VERSION:102` in the fixture is the template's, and the issue never states a version, so the "out of specification" reading above stays conditional.
- The reporter does not assign fault: "It may be encoded wrong, but the right fix would be a better parse code that does not allow the code to fault."
- The bank name "OnPoint Community Credit Union" is the expansion of the domain onpointcu.com given in the issue. The issue names no country. The reporter's username reads as a place name, which is not an attestation about the file, so no country is claimed here.
- The `<MEMO/>` token is the only byte sequence taken from the source. The transaction it sits in, the account it belongs to and the statement around it are ours.
- `ofxtools` failing on `LEDGERBAL` is what the run recorded. That the self-closing tag is the cause is an inference from the fact that it is the only line differing from the template, not something the error message says.
- The measurement covers two parsers in three call modes, not three parsers.
