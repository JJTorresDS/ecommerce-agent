# Agent instructions

Follow this file on every change in this repo.

## Test-driven development

Do not write or edit production code until a failing test exists for the behavior you want.

1. Write or update a test in `tests/` that describes the change. Use dummy catalog data from `db/seed_products.py` and the example FAQ Google Doc URL from `ecommerce_agent/api/schemas.py` when the feature touches products or documents.
2. Run `uv run pytest`. Confirm the new test **fails** for the right reason (missing feature or old behavior), not because of a broken import or fixture.
3. Change application code in `ecommerce_agent/` (and only related files) until that test passes.
4. Run `uv run pytest` again. Do not finish while tests fail.
5. Do not add extra production code that is not required to pass the tests.

For bug fixes: reproduce the bug with a test first, then fix the code.

For refactors: keep existing tests green; add tests first if behavior changes.

## Documentation must match the code

Every change that lands in this repo must also update **both**:

- `README.md` — how to run, configure, ingest, and use the app
- `architecture.md` — as-built layout, diagrams, layer rules, data model, and env flags

Before you stop:

1. Diff your code against those two files.
2. Update run commands, file trees, mermaid diagrams, endpoints, tools, env vars, and data-model notes so they describe what exists **now**, not the previous design.
3. Remove claims about files or flows you deleted (no leftover shims or old paths).
4. If the change is internal-only and the docs already match, say so explicitly in your summary. Do not skip the check.

Do not treat `architecture_proposal.md` as as-built. That file is historical. `architecture.md` is the source of truth for the current system.
