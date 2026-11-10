# Development

## Setup

```bash
git clone <repository-url>
cd anki-dictionary-addon
uv sync
```

## Workflow

```bash
python dev.py ci     # Run linting + tests
python dev.py build  # Build for testing
```

## Svelte Web UI

The dictionary interface (rendered in AnkiWebView) is a Svelte 5 app in `web/`. It is built with Vite into a single self-contained `dist/dictionary.html` (inlined JS + CSS).

```bash
cd web
npm ci               # Install JS dependencies (first time)
npm run dev          # Vite dev server (visual iteration outside Anki)
npm run build        # Build + inline → web/dist/dictionary.html
npm run check        # svelte-check (types + a11y warnings)
```

`build.py` runs `npm ci && npm run build` automatically when packaging (skips with a warning if npm is missing — the legacy `assets/templates/dictionary.html` remains the fallback). `MIDict.getHTMLURL` uses the built bundle when present, dev checkouts find it at `web/dist/dictionary.html`; the packaged addon ships it at `assets/web/dictionary.html`.

## Commands

| Command | Action |
|---|---|
| `uv sync` | Install dependencies |
| `python dev.py test` | Run test suite (unit + integration) |
| `python dev.py lint` | ruff check + ruff format --check |
| `python dev.py format` | ruff auto-format |
| `python dev.py ci` | lint + test (full CI check) |
| `python dev.py build` | Build .ankiaddon package |
| `python dev.py clean` | Clean build artifacts |
| `pytest tests/ -m "not integration and not network" --ignore=tests/test_all_dictionaries.py --ignore=tests/test_dictionary_index.py` | Fast unit tests only |
| `pytest tests/integration/` | Integration tests (needs anki installed) |
| `cd web && npm run build` | Build the Svelte UI bundle |
| `cd web && npm run check` | Run svelte-check on the Svelte UI |
| `uvx pip-audit -r <(uv export --dev --frozen)` | Security audit (Python deps) |

## CI

The CI pipeline (`.github/workflows/ci.yml`) runs on every push/PR to master:

| Job | What it does |
|---|---|
| `lint` | Ruff check, ruff format check, and type check (ty) on `ubuntu-latest` |
| `web` | `npm ci`, Vite build, and `svelte-check`; the built `web/dist` is shared with the test jobs |
| `test` | Unit and integration tests on `ubuntu-latest`, `windows-latest` and `macos-latest`; the pytest-anki2 smoke test runs on Linux under Xvfb |
| `build` | Packages the `.ankiaddon` with `build.py all` and uploads it as an artifact |
| `release` | Version bump, rebuild, git tag, and GitHub release — triggered by merged PRs (`.github/workflows/release.yml`) |
| CodeQL | Weekly Python security analysis (`.github/workflows/codeql.yml`) |
| Dependabot | Weekly PRs for `pip` and `github-actions` dependency bumps (`.github/dependabot.yml`) |

To run the same checks locally:

```bash
uv sync --frozen
uv run ruff check . && uv run ruff format --check .
uv run ty check .
cd web && npm ci && npm run build && npm run check
cd ..
uv run pytest tests/ -m "not integration and not network" \
  --ignore=tests/test_all_dictionaries.py --ignore=tests/test_dictionary_index.py
uv run pytest tests/integration/ --ignore=tests/integration/test_smoke_pytest_anki.py
uv run python build.py all
```

`python dev.py ci` runs the lint, type-check and test steps in one command.

## Code Conventions

- **Naming:** `snake_case` for vars/funcs, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Formatting:** ruff (line length 88, complexity ≤ 10)
- **Types:** ty strict mode — all new code must have type hints
- **Imports:** Absolute within package (`from anki_dictionary.core.database import DictDB`)
- **Logging:** Use `get_logger("module_name")` from `utils/logger.py`
- **Config:** Access via `miInfo()` / `miAsk()` from `utils/common.py`
- **Anki globals:** `mw` is injected at runtime; do not import at module level in testable code
