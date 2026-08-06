"""The Python model and the JSON schemas must not diverge.

The schema is the authority: it also serves the TypeScript implementation to come. Without this
test, the Python code becomes the de facto reference, the TS version runs behind, and each of the
two carries its own truth. That is how a multi-language project dies, and it is predictable, so it
is guarded against.

The tests are parametrised over both schemas rather than written twice. A mirror that only
guards one of the two documents is a mirror the second document walks around.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from bankfile.model import ReadWarning, Statement, Transaction

SCHEMAS = Path(__file__).resolve().parent.parent / "corpus" / "schema"
MIRRORS = [
    ("transaction.schema.json", Transaction),
    ("statement.schema.json", Statement),
]


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize(("name", "model"), MIRRORS)
def test_the_schema_fields_and_the_model_fields_are_the_same(name: str, model: type) -> None:
    expected = set(load(name)["properties"])
    present = {f.name for f in fields(model)}
    assert present == expected, (
        f"{name}: missing from the model: {sorted(expected - present)}; "
        f"absent from the schema: {sorted(present - expected)}"
    )


@pytest.mark.parametrize(("name", "model"), MIRRORS)
def test_the_required_schema_fields_have_no_default(name: str, model: type) -> None:
    """A field required by the schema but optional in the model lets an invalid object be built
    without anything saying so.

    "Required" carries two different meanings across these two schemas, and the test has to
    respect both instead of averaging them. On a transaction it means a value must be supplied:
    a date or an amount that defaults to nothing is a hole. On a statement it means the KEY is
    always in the document, while the value may legitimately be null (an unreadable account
    line must not cost you the entries) or an empty array. So a default is allowed exactly when
    the schema declares the field nullable or as an array, and forbidden everywhere else.
    """
    schema = load(name)
    for f in fields(model):
        if f.name not in set(schema["required"]):
            continue
        declared = schema["properties"][f.name].get("type")
        types = declared if isinstance(declared, list) else [declared]
        may_default = "null" in types or "array" in types
        has_default = not (
            f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        )
        if may_default:
            continue
        assert not has_default, (
            f"{name}: {f.name} is required and non-nullable in the schema, "
            f"but carries a default in the model"
        )


@pytest.mark.parametrize("name", [name for name, _ in MIRRORS])
def test_the_schema_rejects_unknown_fields(name: str) -> None:
    """`additionalProperties: false` is what makes the mirror verifiable on both sides."""
    assert load(name)["additionalProperties"] is False


def test_the_warning_fields_mirror_the_schema_definition() -> None:
    """The warning type carries the failure doctrine, so it is mirrored like the rest."""
    expected = set(load("statement.schema.json")["$defs"]["warning"]["properties"])
    present = {f.name for f in fields(ReadWarning)}
    assert present == expected


def test_the_warning_rules_are_the_sections_of_the_reading_rules() -> None:
    """A warning names the rule that fired. If the enum drifts from the document, the reader
    lands on a section that no longer exists, which is worse than no reference at all."""
    rules = load("statement.schema.json")["$defs"]["warning"]["properties"]["rule"]["enum"]
    document = (SCHEMAS.parent / "reading-rules.md").read_text(encoding="utf-8").lower()
    for rule in rules:
        assert rule in document, f"{rule!r} is not a section of corpus/reading-rules.md"
