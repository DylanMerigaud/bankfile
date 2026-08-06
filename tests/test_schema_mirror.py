"""The Python model and the JSON schema must not diverge.

The schema is the authority: it also serves the TypeScript implementation to come. Without this
test, the Python code becomes the de facto reference, the TS version runs behind, and each of the
two carries its own truth. That is how a multi-language project dies, and it is predictable, so it
is guarded against.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import fields
from pathlib import Path

from bankfile.model import Transaction

SCHEMA = Path(__file__).resolve().parent.parent / "corpus" / "schema" / "transaction.schema.json"


def test_the_schema_fields_and_the_model_fields_are_the_same() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    expected = set(schema["properties"])
    present = {f.name for f in fields(Transaction)}
    assert present == expected, (
        f"missing from the model: {sorted(expected - present)}; "
        f"absent from the schema: {sorted(present - expected)}"
    )


def test_the_required_schema_fields_have_no_default() -> None:
    """A field required by the schema but optional in the model lets an invalid object be built
    without anything saying so."""
    required = set(json.loads(SCHEMA.read_text(encoding="utf-8"))["required"])
    for f in fields(Transaction):
        if f.name in required:
            assert f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING, (
                f"{f.name} is required by the schema but carries a default in the model"
            )


def test_the_schema_rejects_unknown_fields() -> None:
    """`additionalProperties: false` is what makes the mirror verifiable on both sides."""
    assert json.loads(SCHEMA.read_text(encoding="utf-8"))["additionalProperties"] is False
