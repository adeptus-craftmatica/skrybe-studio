## Summary

<!-- What does this change do, and why? -->

## Architecture checklist

- [ ] Core (`src/skrybe_studio/core/`) contains no manuscript-, timeline-, story-bible-, or
      other feature-specific logic.
- [ ] Plugins do not import another plugin's implementation classes directly (only entity IDs,
      events, service interfaces, capability registration, or commands).
- [ ] New plugin-owned tables use the plugin's own `DeclarativeBase`, not the core's.
- [ ] New/changed plugin manifests still validate (`PluginManifest`).

## Test plan

<!-- How was this verified? List commands run and/or manual steps. -->

- [ ] `uv run pytest`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run pyright`

## Screenshots (if UI-visible)

<!-- Optional -->
