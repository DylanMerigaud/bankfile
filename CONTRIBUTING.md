# Contributing

## What helps most

An anonymised excerpt of a file the library reads badly. That is what builds the project's
asset, and it is the one thing no model can produce for you: the specification is public, the
way your bank departs from it is not.

**Always anonymise**: replace amounts, names and account numbers. The structure is what
counts, never the content.

## A parsing fix without a fixture will come back

Every fix carries its file under `corpus/banks/`, with the `.md` that states the bank, the
format and the deviation. Otherwise the regression comes back at the first refactor, and the
corpus, which is the asset, has not grown.

## Before opening a PR

```bash
uv sync --all-groups
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

The lint is strict and its exemptions are written in `pyproject.toml` with their reason.
Adding one without a reason is not an exemption, it is a rule switched off because it gets in
the way.
