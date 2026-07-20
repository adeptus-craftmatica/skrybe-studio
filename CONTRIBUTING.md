# Contributing to Skrybe Studio

Skrybe Studio is currently a private, early-stage project owned and maintained by
[`adeptus-craftmatica`](https://github.com/adeptus-craftmatica). This document sets expectations
for anyone contributing code.

## Before you start

Read [`docs/architecture.md`](docs/architecture.md). The single most important rule in this
codebase is:

> The core (`src/skrybe_studio/core/`) has no knowledge of manuscripts, timelines, story
> bibles, or any other feature-specific concept. Those live entirely in plugins.

If a change adds feature-specific logic to `core/`, it almost certainly belongs in a plugin
instead. If you're proposing a new plugin, see
[`.github/ISSUE_TEMPLATE/plugin_proposal.yml`](.github/ISSUE_TEMPLATE/plugin_proposal.yml).

## Setup

```bash
uv sync
```

## Before opening a pull request

Run all of the following and ensure they pass:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

## Code style

- Modern Python typing (`X | None`, `list[str]`, etc.) - no `Optional`/`Union` from `typing`.
- No hardcoded colors, spacing, or fonts in widget code - use `core/themes` design tokens and
  `ui/design_tokens.py`.
- No SQL in widgets - persistence goes through a plugin's repository/service layer.
- Plugins never import another plugin's implementation classes. Cross-plugin communication
  goes through entity IDs, events, service interfaces, capability registration, or commands.
- Prefer small, explicit interfaces over deep inheritance hierarchies or DI frameworks.

## Tests

- New core services and plugin application/domain logic need tests under `tests/core/` or
  `tests/plugins/<plugin>/`.
- Tests must use temporary directories (`tmp_path`) - never the real user home, app-support, or
  log directories. See `tests/conftest.py` for the isolated `application` fixture.
- UI smoke tests belong in `tests/integration/` and use `pytest-qt`'s `qtbot`.

## Commit style

Prefer Conventional-Commits-style prefixes (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`)
with a short, imperative summary line.

## Ownership

All changes are reviewed under [`CODEOWNERS`](.github/CODEOWNERS), currently
`@adeptus-craftmatica` for the whole repository.
