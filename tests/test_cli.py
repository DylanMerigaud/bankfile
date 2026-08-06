"""The command line, which is the only surface most users will ever touch.

Two things are worth guarding here and they are both about the shape of the output, not the
parsing: the document on stdout has to be valid JSON with nothing else mixed in, and a file we
cannot identify has to fail loudly instead of printing an empty statement that reconciles to
zero.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bankfile.cli import main

PAIRED = Path(__file__).resolve().parent / "fixtures" / "paired"
CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "banks"


def test_stdout_is_json_and_nothing_else(capsys: pytest.CaptureFixture[str]) -> None:
    """Warnings go to stderr on purpose: this output is meant to be piped into `jq`, and a
    warning printed on stdout would corrupt the very document it warns about."""
    assert main([str(PAIRED / "account-a.ofx"), "--json"]) == 0
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document["account"] == "0000123456"
    assert document["source"]["format"] == "OFX"
    assert captured.err == ""


def test_the_two_formats_print_the_same_document(capsys: pytest.CaptureFixture[str]) -> None:
    """The promise of the project, checked through the actual command rather than the API."""
    printed = []
    for name in ("account-a.sta", "account-a.ofx"):
        assert main([str(PAIRED / name)]) == 0
        document = json.loads(capsys.readouterr().out)
        document.pop("source")
        document.pop("opening_balance")
        for transaction in document["transactions"]:
            transaction.pop("raw")
        printed.append(document)
    assert printed[0] == printed[1]


def test_warnings_go_to_stderr_and_stdout_stays_parsable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(CORPUS / "unnamed-bank" / "empty-tags-curdef-fitid-name.ofx")]) == 0
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document["warnings"], "the file has an empty CURDEF, that has to be reported"
    assert "CURDEF" in captured.err


def test_an_unreadable_file_fails_loudly_instead_of_printing_an_empty_statement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty statement reconciles to zero and looks like a real answer, which is why this
    is one of the two cases where failing is the correct behaviour."""
    junk = tmp_path / "holiday-photo.jpg"
    junk.write_bytes(b"\xff\xd8\xff\xe0 not a bank file at all")
    assert main([str(junk)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bankfile:" in captured.err


def test_a_missing_file_does_not_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "nope.ofx")]) == 2
    assert "bankfile:" in capsys.readouterr().err


def test_indent_zero_prints_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    """For piping into tools that read one document per line."""
    assert main([str(PAIRED / "account-a.ofx"), "--indent", "0"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert json.loads(out)["currency"] == "EUR"
