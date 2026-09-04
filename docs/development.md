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
| `dagger run python -m ci` | Run full CI pipeline locally via Dagger (containerized) |
| `python dev.py dagger` | Run same pipeline via dev.py wrapper |
| `cd web && npm run build` | Build the Svelte UI bundle |
| `cd web && npm run check` | Run svelte-check on the Svelte UI |
| `uvx pip-audit -r <(uv export --dev --frozen)` | Security audit (Python deps) |

## CI

The CI pipeline (`.github/workflows/ci.yml`) runs on every push/PR to master:

| Job | What it does |
|---|---|
| `ci` | Lint (ruff), type check (ty), unit tests, integration tests, security audit (pip-audit), and build on `ubuntu-latest` |
| `macos-ci` | Lint, type check, and unit tests on `macos-latest` (no manylinux workaround needed) |
| `release` | Version bump, rebuild, git tag, and GitHub release — only on master push, requires both CI jobs |
| CodeQL | Weekly Python security analysis (`.github/workflows/codeql.yml`) |
| Dependabot | Weekly PRs for `pip` and `github-actions` dependency bumps (`.github/dependabot.yml`) |

To run the full CI pipeline locally (containerized, reproducible):

```bash
dagger run python -m ci
```

Requires [Dagger](https://docs.dagger.io/install) and a Docker daemon. The Dagger pipeline builds an `ubuntu:24.04` container, installs all system deps and uv, then runs lint, type check, tests, and build — matching the GitHub Actions environment exactly.

You can also run via the dev.py wrapper: `python dev.py dagger`.

## Code Conventions

- **Naming:** `snake_case` for vars/funcs, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Formatting:** ruff (line length 88, complexity ≤ 10)
- **Types:** ty strict mode — all new code must have type hints
- **Imports:** Absolute within package (`from anki_dictionary.core.database import DictDB`)
- **Logging:** Use `get_logger("module_name")` from `utils/logger.py`
- **Config:** Access via `miInfo()` / `miAsk()` from `utils/common.py`
- **Anki globals:** `mw` is injected at runtime; do not import at module level in testable code
