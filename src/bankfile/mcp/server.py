"""A local MCP server over stdio. The statement never leaves the machine.

Three properties are load bearing here, and none of them is decoration.

**The tools return slices, never the file.** A statement with 5000 transactions destroys a
context window, so there is no tool that can return one. `read_statement` returns a summary and
is structurally incapable of returning an entry; `list_transactions` is filtered, paginated and
hard capped. That is the difference between a tool and a naive `cat` wrapper, and it is the
first thing a naive wrapper gets wrong.

**A failure returns a structured error, never a number.** Every tool answers with the same
envelope: `ok`, `error`, and the payload. When `ok` is false every numeric field is null. The
model is told what went wrong in fields it can read, instead of being handed a string to guess
from, and it is never handed an amount that was invented to fill a hole.

**The determinism contract is written in the tool descriptions.** A model reading these tools
has to know it is talking to a grammar and not to another model: same file, same bytes, same
answer, forever. That sentence belongs where the model actually looks, which is the tool
description, not the README.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from bankfile import parse
from bankfile.detect import UnknownFormatError
from bankfile.model import Statement, Transaction

# Appended to every tool description. A model that does not know this is deterministic will
# hedge, re-ask, or "double check" a figure by guessing at it, which is the one behaviour this
# whole project exists to make unnecessary.
CONTRACT = """

DETERMINISM CONTRACT. This tool parses a published grammar. It never calls a model, never
infers a missing value and never rounds. The same bytes always produce the same answer. Amounts
are exact decimal strings, never floats, because a cent lost in a float is a false
reconciliation. A value that could not be read is null and appears in `warnings`; it is never
guessed. If you need a figure this tool returned as null, read the file yourself, do not
estimate it."""

# A page a model can actually hold. The cap is not advice, it is enforced below: a tool that
# lets a caller ask for 5000 rows has no pagination, it has a suggestion.
DEFAULT_LIMIT = 25
MAX_LIMIT = 100


def _read_only(title: str) -> ToolAnnotations:
    """Every tool here only reads a local file, and the client needs to be TOLD that.

    Without these hints a client treats each call as a potentially destructive action and asks
    the user to approve it. On a statement of 5000 entries that is twenty approval prompts to
    page through one account, which is how a well built server ends up unused. With them,
    Claude Code and Claude Desktop auto-approve read-only calls.

    `open_world_hint=False` is the other half of the promise this server makes: it reaches
    nothing outside the machine, so there is no network for a prompt to protect you from.
    """
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )


class Error(BaseModel):
    """Why a call produced nothing usable, in fields rather than in prose."""

    kind: str = Field(description="unreadable_path, outside_root, unknown_format, or read_failed")
    message: str = Field(description="What went wrong, in one sentence.")
    path: str | None = Field(default=None, description="The path as it was given.")


class ReportedWarning(BaseModel):
    rule: str = Field(description="Which reading rule fired: encoding, header, amount, date, tag.")
    field: str | None = None
    value: str | None = Field(default=None, description="The raw value, kept verbatim.")
    message: str


class Summary(BaseModel):
    """Everything about a statement EXCEPT its entries."""

    ok: bool
    error: Error | None = None
    format: str | None = Field(default=None, description="MT940 or OFX, detected from the bytes.")
    encoding: str | None = None
    account: str | None = None
    currency: str | None = None
    opening_balance: str | None = Field(default=None, description="Exact decimal as a string.")
    closing_balance: str | None = None
    transaction_count: int = 0
    first_date: datetime.date | None = None
    last_date: datetime.date | None = None
    total_amount: str | None = Field(
        default=None, description="Sum of the entries, exact decimal as a string."
    )
    reconciles: bool | None = Field(
        default=None,
        description=(
            "Whether opening plus the entries equals the closing balance. Null when the file "
            "does not carry both balances. FALSE means the file contradicts itself, which no "
            "other parser will tell you."
        ),
    )
    warning_count: int = 0


class Entry(BaseModel):
    """One transaction, normalised. The same fields whatever the source format."""

    # `datetime.date` and not a bare `date`: the field below is CALLED date, so a bare import
    # would be shadowed by it and `booking_date` would be annotated with the field. The same
    # trap as in bankfile/model.py, caught by mypy for the same reason, twice now.
    date: datetime.date
    booking_date: datetime.date | None = None
    amount: str = Field(description="Exact decimal as a string, never a float.")
    currency: str | None = None
    counterparty_name: str | None = None
    counterparty_account: str | None = None
    reference: str | None = None
    purpose: str | None = None
    bank_reference: str | None = None
    type_code: str | None = None
    check_number: str | None = None


class Page(BaseModel):
    """A slice, and enough context to know it is one."""

    ok: bool
    error: Error | None = None
    entries: list[Entry] = Field(default_factory=list)
    total_matching: int = Field(default=0, description="How many entries matched the filters.")
    offset: int = 0
    next_offset: int | None = Field(
        default=None, description="Pass this back to get the next page. Null when this is the last."
    )
    truncated: bool = Field(
        default=False, description="True when more entries matched than this page carries."
    )


class WarningPage(BaseModel):
    ok: bool
    error: Error | None = None
    warnings: list[ReportedWarning] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    next_offset: int | None = None


def build_server(root: Path) -> MCPServer:
    """Wire the tools against a root directory the server may read under.

    The root is a real restriction, not a formality. This server takes a path from a model and
    opens it, so without a root the model can walk the filesystem. Defaulting it to the working
    directory keeps the useful case working and makes the dangerous one impossible.
    """
    resolved_root = root.resolve()

    mcp = MCPServer(
        name="bankfile",
        version="0.0.1",
        instructions=(
            "Read bank statement files (MT940, OFX, QFX) into one normalised schema.\n\n"
            "Everything runs on this machine and nothing is uploaded: a bank statement is the "
            "most sensitive file a company has.\n\n"
            f"Files can only be read under {resolved_root}.\n\n"
            "Start with read_statement to see what a file holds, then list_transactions to "
            "page through the entries. There is deliberately no tool that returns a whole "
            "file: a statement of 5000 entries would fill your context and leave you no room "
            "to reason about it."
        ),
    )

    def locate(path: str) -> tuple[Path | None, Error | None]:
        try:
            given = Path(path)
            candidate = (given if given.is_absolute() else resolved_root / given).resolve()
        except OSError as exc:
            return None, Error(kind="unreadable_path", message=str(exc), path=path)
        if resolved_root not in candidate.parents and candidate != resolved_root:
            return None, Error(
                kind="outside_root",
                message=f"this server only reads under {resolved_root}",
                path=path,
            )
        if not candidate.is_file():
            return None, Error(kind="unreadable_path", message="no such file", path=path)
        return candidate, None

    def read(path: str) -> tuple[Statement | None, Error | None]:
        located, error = locate(path)
        if error is not None or located is None:
            return None, error
        try:
            return parse(located), None
        except UnknownFormatError as exc:
            return None, Error(kind="unknown_format", message=str(exc), path=path)
        except OSError as exc:
            return None, Error(kind="read_failed", message=str(exc), path=path)

    @mcp.tool(
        annotations=_read_only("Summarise a bank file"),
        description=(
            "Summarise a bank file: account, currency, balances, how many entries it holds and "
            "whether its own figures add up. It does NOT return the entries; use "
            "list_transactions for those." + CONTRACT
        ),
    )
    def read_statement(
        path: Annotated[str, Field(description="Path to the file, relative to the server root.")],
    ) -> Summary:
        statement, error = read(path)
        if statement is None:
            return Summary(ok=False, error=error)
        amounts = [t.amount for t in statement.transactions]
        dates = sorted(t.date for t in statement.transactions)
        total = sum(amounts, Decimal("0")) if amounts else None
        reconciles: bool | None = None
        if statement.opening_balance is not None and statement.closing_balance is not None:
            reconciles = (
                statement.opening_balance + (total or Decimal("0")) == statement.closing_balance
            )
        return Summary(
            ok=True,
            format=statement.source.format,
            encoding=statement.source.encoding,
            account=statement.account,
            currency=statement.currency,
            opening_balance=_money(statement.opening_balance),
            closing_balance=_money(statement.closing_balance),
            transaction_count=len(statement.transactions),
            first_date=dates[0] if dates else None,
            last_date=dates[-1] if dates else None,
            total_amount=_money(total),
            reconciles=reconciles,
            warning_count=len(statement.warnings),
        )

    @mcp.tool(
        annotations=_read_only("Page through the entries of a bank file"),
        description=(
            "Page through the entries of a bank file, with filters. Never returns the whole "
            f"file: at most {MAX_LIMIT} entries per call, {DEFAULT_LIMIT} by default. Use "
            "`total_matching` to see how many matched and `next_offset` to continue. Filter "
            "first, page second: asking for everything and reading it all is what fills a "
            "context window." + CONTRACT
        ),
    )
    def list_transactions(
        path: Annotated[str, Field(description="Path to the file, relative to the server root.")],
        *,
        offset: Annotated[int, Field(ge=0, description="Entries to skip.")] = 0,
        # No `le` constraint on purpose. A caller asking for 5000 entries gets the first
        # MAX_LIMIT of them with `truncated` set, rather than a validation error: it is served,
        # it is told, and it can page on. The cap is enforced below whatever is asked, so it
        # holds even for a client that ignores this schema.
        limit: Annotated[
            int, Field(ge=1, description=f"Entries to return. Capped at {MAX_LIMIT}.")
        ] = DEFAULT_LIMIT,
        since: Annotated[
            datetime.date | None, Field(description="Keep entries on or after this date.")
        ] = None,
        until: Annotated[
            datetime.date | None, Field(description="Keep entries on or before this date.")
        ] = None,
        min_amount: Annotated[
            str | None, Field(description="Keep entries at or above this amount, as a string.")
        ] = None,
        max_amount: Annotated[str | None, Field(description="Keep entries at or below.")] = None,
        counterparty: Annotated[
            str | None, Field(description="Case insensitive substring of the counterparty name.")
        ] = None,
        type_code: Annotated[
            str | None, Field(description="Normalised type, for example TRANSFER or CHECK.")
        ] = None,
    ) -> Page:
        statement, error = read(path)
        if statement is None:
            return Page(ok=False, error=error)
        try:
            low = Decimal(min_amount) if min_amount is not None else None
            high = Decimal(max_amount) if max_amount is not None else None
        except InvalidOperation:
            return Page(
                ok=False,
                error=Error(
                    kind="read_failed",
                    message="min_amount and max_amount must be decimal strings, for example -10.00",
                    path=path,
                ),
            )
        wanted = Filters(
            since=since,
            until=until,
            low=low,
            high=high,
            counterparty=counterparty,
            type_code=type_code,
        )
        matching = [t for t in statement.transactions if _keeps(t, wanted)]
        capped = min(limit, MAX_LIMIT)
        window = matching[offset : offset + capped]
        consumed = offset + len(window)
        return Page(
            ok=True,
            entries=[_entry(t) for t in window],
            total_matching=len(matching),
            offset=offset,
            next_offset=consumed if consumed < len(matching) else None,
            truncated=consumed < len(matching),
        )

    @mcp.tool(
        annotations=_read_only("What could not be read"),
        description=(
            "The import report: everything in the file that could not be read, and everything "
            "that was ambiguous. An empty report means a clean read. This is where a silently "
            "dropped field shows up, which is the failure mode that costs the most: a crash is "
            "obvious, a missing cheque number is not." + CONTRACT
        ),
    )
    def list_warnings(
        path: Annotated[str, Field(description="Path to the file, relative to the server root.")],
        *,
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, description=f"Capped at {MAX_LIMIT}.")] = DEFAULT_LIMIT,
    ) -> WarningPage:
        statement, error = read(path)
        if statement is None:
            return WarningPage(ok=False, error=error)
        capped = min(limit, MAX_LIMIT)
        window = statement.warnings[offset : offset + capped]
        consumed = offset + len(window)
        return WarningPage(
            ok=True,
            warnings=[
                ReportedWarning(rule=w.rule, field=w.field, value=w.value, message=w.message)
                for w in window
            ],
            total=len(statement.warnings),
            offset=offset,
            next_offset=consumed if consumed < len(statement.warnings) else None,
        )

    return mcp


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _entry(t: Transaction) -> Entry:
    return Entry(
        date=t.date,
        booking_date=t.booking_date,
        amount=str(t.amount),
        currency=t.currency,
        counterparty_name=t.counterparty_name,
        counterparty_account=t.counterparty_account,
        reference=t.reference,
        purpose=t.purpose,
        bank_reference=t.bank_reference,
        type_code=t.type_code,
        check_number=t.check_number,
    )


@dataclass(frozen=True, slots=True)
class Filters:
    """The filters, gathered. They are seven flat parameters on the tool because that is what
    a model reads in the schema, and one object in here because that is what code reads."""

    since: datetime.date | None = None
    until: datetime.date | None = None
    low: Decimal | None = None
    high: Decimal | None = None
    counterparty: str | None = None
    type_code: str | None = None


def _keeps(t: Transaction, wanted: Filters) -> bool:
    if wanted.since is not None and t.date < wanted.since:
        return False
    if wanted.until is not None and t.date > wanted.until:
        return False
    if wanted.low is not None and t.amount < wanted.low:
        return False
    if wanted.high is not None and t.amount > wanted.high:
        return False
    if wanted.counterparty is not None:
        name = t.counterparty_name or ""
        if wanted.counterparty.casefold() not in name.casefold():
            return False
    return not (wanted.type_code is not None and (t.type_code or "") != wanted.type_code.upper())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bankfile-mcp",
        description="A local MCP server over stdio. Bank files never leave this machine.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Directory the server may read under. Defaults to the working directory.",
    )
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"bankfile-mcp: {args.root} is not a directory", file=sys.stderr)
        return 2
    build_server(args.root).run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
