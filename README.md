# bankfile

One schema for every bank file: MT940, MT942, CAMT.053, BAI2, OFX/QFX.

The name says `file` and not `statement`, and that is deliberate: the day the library reads a
payment order (`pain.001`) or an ACH file, those are not statements, and a name that promises
statements would fight its own scope.

## Quickstart

```bash
pip install bankfile
bankfile releve.sta --json
```

```python
from bankfile import parse

for tx in parse("releve.sta"):
    print(tx.date, tx.amount, tx.counterparty_name)
```

The same code reads a German MT940 and a Chase QFX, and returns the same fields.

## Why this exists, and what it is not

Every format has its library, and every library has its schema. Measured on 2026-08-05: for the
same notion of a transaction, `mt940` returns 37 fields, `ofxparse` returns 10, and they have
only **three fields in common** (amount, date, identifier). The counterparty is called
`applicant_name` on one side and `payee` on the other. Anyone ingesting two formats writes the
mapping by hand, then rewrites it for the next format.

**This is not a new parser.** The good parsers exist and we build on them where we can. What is
missing is the layer above, plus the corpus below.

**This is not model-based extraction.** A bank statement has a published grammar: parsing it
with a model would be non deterministic, expensive at volume and unauditable. Bank
reconciliation cannot be probabilistic, and a wrong but plausible amount is the worst possible
failure in finance. The model has its place elsewhere, see below.

**This is not a hosted service.** A statement is the most sensitive file a company has.
Everything runs on your machine, including the MCP server.

## The corpus is the asset, not the code

A model writes a spec-compliant parser in thirty seconds, because the spec is public. It cannot
know that Wells Fargo omits the line breaks in a QFX header, that Chase writes malformed
headers, or that a file declaring `CHARSET:NONE` makes ofxparse concatenate `cp` with it and
look up a codec named `cpNONE`, which does not exist. Those are facts about the world, not about
the standard.

The three examples come from open, unmerged pull requests, not from imagination.

So `corpus/` is versioned as neutral data: JSON schema, per-bank fixtures, deviation rules. The
Python and TypeScript implementations consume it without either one becoming the reference. Two
implementations each carrying their own truth drift apart.

## Where the model actually helps

Never on the parsing path. On three points, offline, where there is no specification:

1. Generate a deviation rule from a bank's PDF documentation, once, then run it
   deterministically forever.
2. Diagnose a file that fails and propose the missing rule.
3. Read a statement delivered as a PDF, where there really is no grammar.

## MCP server

Local, over stdio. The file does not leave the machine. The tools return filtered and paginated
slices, never the whole file: a statement with 5000 transactions destroys a context window, and
that is the first thing a naive wrapper gets wrong.

## Contributing

A report carrying an anonymised file excerpt is worth more than a code fix. See
[CONTRIBUTING.md](CONTRIBUTING.md), and the issue template "my bank produces a file the library
cannot read".

## License

MIT.
