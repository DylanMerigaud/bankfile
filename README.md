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

## API

The public surface is deliberately small: `parse`, `parse_bytes`, `UnknownFormatError`,
`__version__`, and the four model types `Statement`, `Transaction`, `ReadWarning`, `Source`.
Everything else in the package is an implementation detail a caller should never need.

**`parse(path)` returns a `Statement`, not a list of transactions.** The entries are one field
of it. The account, the balances, the provenance and the import report are the others, and a
caller who keeps only `.transactions` has thrown away the part that says whether those entries
can be trusted.

`parse_bytes(data, path=None)` is the same read for content you already hold in memory. It
takes bytes and never a `str`, because choosing the encoding is the reader's job and it cannot
do that job once someone else has guessed. Both raise `UnknownFormatError` when the file is
neither MT940 nor OFX.

`Statement` and `Transaction` mirror `corpus/schema/statement.schema.json` and
`corpus/schema/transaction.schema.json`, and those schemas are the authority, not this README
and not the Python classes. They are neutral data so that the TypeScript implementation reads
the same truth; `tests/test_schema_mirror.py` fails if the classes drift from them. Where a
schema and this page disagree, the schema is right.

### `Statement`

| field | type | |
| --- | --- | --- |
| `source` | `Source` | `format` is `"MT940"` or `"OFX"`, plus `path` and `encoding`. The one part that legitimately differs across formats. |
| `account` | `str \| None` | The account identifier as the file states it. |
| `currency` | `str \| None` | ISO 4217, three letters. |
| `opening_balance` | `Decimal \| None` | Never computed by subtraction. OFX 1.x has no element for it, so it stays null there. |
| `closing_balance` | `Decimal \| None` | |
| `transactions` | `list[Transaction]` | |
| `warnings` | `list[ReadWarning]` | Always present, empty when the read was clean. |

### `Transaction`

| field | type | |
| --- | --- | --- |
| `date` | `datetime.date` | The value date, and the only date that is never null. |
| `amount` | `Decimal` | Signed. Negative is money leaving the account. |
| `currency` | `str \| None` | ISO 4217, three letters. |
| `raw` | `dict[str, Any]` | Always filled. The origin format's own fields, untouched. |
| `booking_date` | `datetime.date \| None` | |
| `counterparty_name` | `str \| None` | `applicant_name` in MT940, `NAME` in OFX. This single field is most of the reason the library exists. |
| `counterparty_account` | `str \| None` | |
| `reference` | `str \| None` | |
| `purpose` | `str \| None` | |
| `bank_reference` | `str \| None` | |
| `type_code` | `str \| None` | The shared vocabulary: `TRANSFER`, `CHECK`, `DIRECT_DEBIT`, `DEPOSIT`, `INTEREST`, `DIVIDEND`, `FEE`, `ATM`, `POINT_OF_SALE`, `CASH`, `PAYMENT`, `CREDIT`, `DEBIT`, `HOLD`, `OTHER`. The mapping is ours and it is arguable, so it is open: an unmapped code becomes `OTHER` with a warning and the original stays in `raw`. |
| `check_number` | `str \| None` | A string, because leading zeros in a cheque number are significant. |

`ReadWarning` carries `rule`, `field`, `value` and `message`. `Source` carries `format`, `path`
and `encoding`.

### Money is `Decimal`, never float

`amount`, `opening_balance` and `closing_balance` are `decimal.Decimal`, and the JSON output
carries them as strings for the same reason.

A cent lost inside a binary64 is a false reconciliation. `0.1 + 0.2` is not `0.3` in floating
point, so a thousand entries summed as floats can miss the closing balance by a few cents,
which reads as a real discrepancy and sends somebody hunting for a transaction that does not
exist. The source file already carries exact decimals: converting them to float destroys
information that arrived correct.

`Decimal` refuses to mix with float, which is the property you want here:

```python
from decimal import Decimal
from bankfile import parse

statement = parse("statement.sta")
total = sum((t.amount for t in statement.transactions), Decimal("0"))

statement.transactions[0].amount * 1.2  # TypeError, and that is the point
statement.transactions[0].amount * Decimal("1.2")
```

### `currency` is nullable, and null means the file did not say

Not "EUR by default", not "guess from the country". A real file leaves `CURDEF` empty
(ofxparse issue #81, two Australian banks), and the corpus rule for that case is to keep the
transaction, leave the currency unset and warn. The alternatives are both worse: dropping the
entry rejects a whole statement over one empty tag, and inferring a currency from the bank
identifier produces the wrong-but-plausible figure this project exists to avoid.

So `if transaction.currency is None` is a real branch you have to write, and it means the
information is not in the file.

### `warnings`: nothing unreadable is dropped in silence

A file that can be read is never rejected over the value of a single field. The unexpected
value is kept verbatim, the normalised field stays null, and a warning says so. That is the
whole point of the array: a tolerant parser without it is just a parser that loses data
quietly.

`rule` names the section of [`corpus/reading-rules.md`](corpus/reading-rules.md) that fired, so
a line in the output leads straight to the paragraph that decided it. There are five:

| rule | fires on |
| --- | --- |
| `encoding` | Which codec was finally used, and when the file asked for one we do not honour. |
| `header` | An OFX 1.x header block we could not read, so the format defaults were applied. |
| `amount` | An amount whose decimal separator was ambiguous, and the reconciliation check below. |
| `date` | A date absent, all zeros, or of a length the format does not define. |
| `tag` | An unknown tag, an empty tag, or a value outside an enumeration such as an unmapped transaction code. |

Identical warnings are collapsed to one. Measured on the real MT940 files in the test corpus,
77 of 211 transactions carry a SWIFT code outside the mapped vocabulary, and 77 identical
lines is a report nobody reads.

### `raw` always keeps the origin format

`transaction.raw` holds the source format's own fields as they were. A normalisation that
throws the original away forces a re-parse of the file the first time a question falls outside
the schema, and by then nobody has the file any more.

```python
transaction.type_code  # 'TRANSFER', ours
transaction.raw["id"]  # 'NTRF', the file's
```

### The reconciliation check

No other parser does this. When the file states both balances, opening plus the sum of the
entries is checked against the closing balance, and a mismatch becomes a warning:

```text
amount | 62F | -49.06
this statement does not add up: opening 0.00 plus -45.59 of entries gives -45.59, and the
file states a closing balance of 3.47, a difference of -49.06. The entries are returned
unchanged, the arithmetic is the file's.
```

That is a real fixture, not an invented example. The check earns its place because it found
the only genuine bug of this phase: `mt940` negates an amount for a `D` mark and not for an
`RC`, a reversed credit, so money leaving the account came back positive. No test caught it.
Arithmetic did, in one line.

Run across the real files of the test corpus it reports 13 that do not add up, all 13
verified by hand against a byte level sum that does not go through this library, and in every
case it is the file that contradicts itself, not our reading of it. Which is the point:
somebody reconciling an account needs to be told the file they were sent does not balance.

Today this fires on MT940 only, because OFX 1.x carries no opening balance and we will not
compute one by subtraction.

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
