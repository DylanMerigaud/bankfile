"""The MCP server, tested against the three properties phase 2 asks for.

Those three are not features, they are the difference between this and a `cat` wrapper: the
tools never return a whole file, a failure returns a structured error instead of a number, and
the determinism contract is written where a model actually looks, in the tool description.

Everything here goes through `call_tool`, the same path a real client takes. Calling the
underlying functions directly would test code that no client can reach.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bankfile.mcp.server import DEFAULT_LIMIT, MAX_LIMIT, Summary, build_server, main

REPO = Path(__file__).resolve().parent.parent
BUSY = "tests/fixtures/mt940/betterplace/sepa_mt9401.sta"  # 97 entries
PAIRED_MT940 = "tests/fixtures/paired/account-a.sta"
PAIRED_OFX = "tests/fixtures/paired/account-a.ofx"


@pytest.fixture
def server() -> Any:
    return build_server(REPO)


async def call(server: Any, tool: str, **arguments: Any) -> dict[str, Any]:
    result = await server.call_tool(tool, arguments)
    assert result.structured_content is not None, f"{tool} returned no structured content"
    return dict(result.structured_content)


@pytest.mark.anyio
async def test_every_tool_description_carries_the_determinism_contract(server: Any) -> None:
    """A model that does not know this is deterministic will hedge, re-ask, or estimate a
    figure it was already given exactly. The contract goes where it reads, not in the README."""
    tools = await server.list_tools()
    assert {t.name for t in tools} == {"read_statement", "list_transactions", "list_warnings"}
    for tool in tools:
        assert "DETERMINISM CONTRACT" in (tool.description or ""), tool.name
        assert "never calls a model" in (tool.description or ""), tool.name


def test_the_summary_cannot_carry_a_transaction() -> None:
    """Structural, not a promise. `read_statement` is the tool a model reaches for first, and
    the cheapest way to guarantee it never dumps 5000 entries is to give it no field to put
    them in."""
    assert "entries" not in Summary.model_fields
    assert "transactions" not in Summary.model_fields


@pytest.mark.anyio
async def test_a_summary_describes_a_busy_file_without_returning_any_of_it(server: Any) -> None:
    summary = await call(server, "read_statement", path=BUSY)
    assert summary["ok"] is True
    assert summary["transaction_count"] == 97
    assert summary["format"] == "MT940"
    assert summary["total_amount"] == "-9269135.90"
    assert summary["first_date"] == "2007-09-04"


@pytest.mark.anyio
async def test_a_page_says_how_much_it_is_not_showing(server: Any) -> None:
    """A slice that does not say it is a slice is a lie by omission: the model concludes the
    account has two entries."""
    page = await call(server, "list_transactions", path=BUSY, limit=2)
    assert len(page["entries"]) == 2
    assert page["total_matching"] == 97
    assert page["next_offset"] == 2
    assert page["truncated"] is True


@pytest.mark.anyio
async def test_paging_walks_the_whole_file_without_ever_loading_it(server: Any) -> None:
    seen: list[dict[str, Any]] = []
    offset: int | None = 0
    pages = 0
    while offset is not None:
        page = await call(
            server, "list_transactions", path=BUSY, offset=offset, limit=DEFAULT_LIMIT
        )
        seen += page["entries"]
        offset = page["next_offset"]
        pages += 1
    assert len(seen) == 97
    assert pages == 4
    assert len({e["bank_reference"] for e in seen}) > 1, "pages must not repeat the same entry"


@pytest.mark.anyio
async def test_asking_for_the_whole_file_is_served_capped_and_told(tmp_path: Path) -> None:
    """A caller asking for 5000 entries gets MAX_LIMIT of them, not an error and not 5000.

    Served rather than refused: the model gets data and learns the cap from `truncated`. Capped
    rather than obeyed: this is the one guarantee that stops a statement from filling a context
    window, so it cannot depend on the client respecting the schema.
    """
    generated = tmp_path / "many.sta"
    entries = "".join(
        f":61:2601{day:02d}{day:02d}D1,00NTRFNONREF//B{index:04d}\n:86:entry {index}\n"
        for index, day in ((i, (i % 28) + 1) for i in range(150))
    )
    generated.write_text(
        ":20:MANY\n:25:0000123456\n:28C:1/1\n:60F:C260101EUR1000,00\n"
        + entries
        + ":62F:C260131EUR850,00\n",
        encoding="utf-8",
    )
    server = build_server(tmp_path)
    page = await call(server, "list_transactions", path="many.sta", limit=5000)
    assert page["total_matching"] == 150
    assert len(page["entries"]) == MAX_LIMIT
    assert page["truncated"] is True
    assert page["next_offset"] == MAX_LIMIT


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"type_code": "TRANSFER"}, 1),
        ({"type_code": "CHECK"}, 0),
        ({"counterparty": "anon merchant"}, 1),
        ({"counterparty": "nobody"}, 0),
        ({"since": "2026-02-01"}, 0),
        ({"until": "2026-01-01"}, 0),
        ({"min_amount": "0"}, 0),
        ({"max_amount": "0"}, 1),
    ],
)
async def test_the_filters_select_before_the_page_is_cut(
    server: Any, filters: dict[str, Any], expected: int
) -> None:
    """Filter first, page second. Paging through everything to find one entry is how a model
    burns a context window on a question a filter answers in one call."""
    page = await call(server, "list_transactions", path=PAIRED_MT940, **filters)
    assert page["ok"] is True
    assert page["total_matching"] == expected


@pytest.mark.anyio
async def test_the_two_formats_answer_identically_through_the_tools(server: Any) -> None:
    """The phase 1 promise, checked through the MCP surface rather than through the API."""
    from_mt940 = await call(server, "list_transactions", path=PAIRED_MT940)
    from_ofx = await call(server, "list_transactions", path=PAIRED_OFX)
    assert from_mt940["entries"] == from_ofx["entries"]
    assert from_mt940["entries"][0]["amount"] == "-10.00"


@pytest.mark.anyio
async def test_a_file_outside_the_root_is_refused_and_says_why(server: Any) -> None:
    """This server takes a path from a model and opens it. Without the root, the model walks
    the filesystem."""
    summary = await call(server, "read_statement", path="../../../etc/passwd")
    assert summary["ok"] is False
    assert summary["error"]["kind"] == "outside_root"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "kind"),
    [("README.md", "unknown_format"), ("does-not-exist.sta", "unreadable_path")],
)
async def test_a_failure_returns_fields_and_not_a_single_figure(
    server: Any, path: str, kind: str
) -> None:
    """The requirement of this phase, literally: a failure produces a structured error rather
    than an invented amount. Every number stays null, so nothing can be read as a balance."""
    summary = await call(server, "read_statement", path=path)
    assert summary["ok"] is False
    assert summary["error"]["kind"] == kind
    assert summary["error"]["path"] == path
    assert summary["opening_balance"] is None
    assert summary["closing_balance"] is None
    assert summary["total_amount"] is None
    assert summary["transaction_count"] == 0


@pytest.mark.anyio
async def test_a_bad_amount_filter_is_a_structured_error_too(server: Any) -> None:
    page = await call(server, "list_transactions", path=PAIRED_MT940, min_amount="ten euros")
    assert page["ok"] is False
    assert page["error"]["kind"] == "read_failed"
    assert page["entries"] == []


@pytest.mark.anyio
async def test_the_import_report_is_paginated_like_everything_else(server: Any) -> None:
    """A broken file can carry more warnings than entries, so the report pages too."""
    report = await call(server, "list_warnings", path=BUSY, limit=1)
    assert report["ok"] is True
    assert report["total"] == 2
    assert len(report["warnings"]) == 1
    assert report["next_offset"] == 1
    assert report["warnings"][0]["rule"] in {"encoding", "header", "amount", "date", "tag"}


@pytest.mark.anyio
async def test_a_clean_file_reports_nothing(server: Any) -> None:
    report = await call(server, "list_warnings", path=PAIRED_OFX)
    assert report["ok"] is True
    assert report["total"] == 0


@pytest.mark.anyio
async def test_a_statement_that_contradicts_itself_says_so_in_the_summary(server: Any) -> None:
    """`reconciles: false` is the field no other parser offers. It is the difference between
    finding out today and finding out in a spreadsheet three days later."""
    broken = await call(server, "read_statement", path="tests/fixtures/mt940/jejik/ing.sta")
    assert broken["reconciles"] is False
    clean = await call(server, "read_statement", path=PAIRED_MT940)
    assert clean["reconciles"] is True


def test_a_root_that_is_not_a_directory_fails_before_any_transport_opens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The entry point checks its argument before opening stdio, because after that there is no
    channel left to report on: a server that dies mid handshake tells the client nothing."""
    not_a_directory = tmp_path / "statement.sta"
    not_a_directory.write_text(":20:X\n", encoding="utf-8")
    assert main(["--root", str(not_a_directory)]) == 2
    assert "not a directory" in capsys.readouterr().err
