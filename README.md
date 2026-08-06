# bankfile

[![ci](https://github.com/DylanMerigaud/bankfile/actions/workflows/ci.yml/badge.svg)](https://github.com/DylanMerigaud/bankfile/actions/workflows/ci.yml)
[![pypi](https://img.shields.io/pypi/v/bankfile.svg)](https://pypi.org/project/bankfile/)
[![python](https://img.shields.io/pypi/pyversions/bankfile.svg)](https://pypi.org/project/bankfile/)

One schema for every bank file: MT940, MT942, CAMT.053, BAI2, OFX/QFX.

The name says `file` and not `statement`, and that is deliberate: the day the library reads a
payment order (`pain.001`) or an ACH file, those are not statements, and a name that promises
statements would fight its own scope.

**Reads today: MT940 and OFX/QFX** (OFX 1.x SGML and OFX 2.x XML). MT942, CAMT.053 and BAI2
are the next formats, and they are not written yet. This list is the honest one, not the
roadmap.

## Quickstart

```bash
pip install bankfile
bankfile statement.sta --json
```

```python
from bankfile import parse

statement = parse("statement.sta")
for transaction in statement.transactions:
    print(transaction.date, transaction.amount, transaction.counterparty_name)

# Nothing we could not read is dropped in silence. It is all in here.
for warning in statement.warnings:
    print(warning.rule, warning.field, warning.message)
```

The same code reads an MT940 and an OFX and returns the same fields. Not "similar fields":
`tests/test_same_json_across_formats.py` builds both documents from one synthetic account
described in both formats and fails on any difference outside three named exclusions, which are
`source` (provenance), each entry's `raw` (the origin format's own fields), and
`opening_balance`, which OFX 1.x has no element for and which we refuse to compute by
subtraction. That last difference is pinned by its own test rather than hidden in the list.

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

Local, over stdio. The file does not leave the machine.

### Point it at your statements

Nothing is uploaded and nothing is installed permanently if you do not want it to be. `--root`
is the directory the server may read under; it is a real restriction, not decoration, because
the server takes a path from a model and opens it.

**Claude Code**

```bash
claude mcp add bankfile -- uvx --from "bankfile[mcp]" bankfile-mcp --root ~/statements
```

**Claude Desktop**, in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bankfile": {
      "command": "uvx",
      "args": ["--from", "bankfile[mcp]", "bankfile-mcp", "--root", "/Users/you/statements"]
    }
  }
}
```

**Codex**, in `~/.codex/config.toml`:

```toml
[mcp_servers.bankfile]
command = "uvx"
args = ["--from", "bankfile[mcp]", "bankfile-mcp", "--root", "/Users/you/statements"]
```

**Cursor**, in `~/.cursor/mcp.json`: same shape as Claude Desktop above.

`uvx` runs it without installing anything into your environment. If you would rather install it,
`pip install "bankfile[mcp]"` and use `bankfile-mcp` as the command instead.

Three tools: `read_statement` for what a file holds, `list_transactions` to page through the
entries with filters, `list_warnings` for the import report.

The tools return filtered and paginated slices, never the whole file: a statement with 5000
transactions destroys a context window, and that is the first thing a naive wrapper gets wrong.
`read_statement` has no field a transaction could go in, which is cheaper than promising it
will not send one. `--root` is a real restriction: the server takes a path from a model and opens it, so the root
is what stops the model wandering. Omitting the flag does not remove the restriction, it sets
it to the working directory, which is a sensible default and rarely the one you want for
statements.

A failure returns a structured error and leaves every number null. It never fills a hole with a
figure, and every tool description carries that contract, because a model that does not know it
is talking to a grammar will hedge and estimate what it was already given exactly.

All three tools are annotated read-only and closed-world, so clients that honour annotations
stop asking you to approve every call. Paging through one account is otherwise twenty approval
prompts, which is how a working server ends up unused.

## Changes

[CHANGELOG.md](CHANGELOG.md). Anything that can change a figure gets its own line, and says
which figure.

## Contributing

A report carrying an anonymised file excerpt is worth more than a code fix. See
[CONTRIBUTING.md](CONTRIBUTING.md), and the issue template "my bank produces a file the library
cannot read".

## License

MIT for the code, the corpus and the documentation.

`tests/fixtures/mt940/` holds bank statement files borrowed from the test suites of other
projects, chiefly [wolph/mt940](https://github.com/wolph/mt940), and those keep their own
BSD-3-Clause terms with the notices reproduced beside them. They are test inputs, they are not
distributed in the published package, and they are not ours to relicense.
