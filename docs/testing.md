# Testing

Tests use **pytest** with marker-based filtering for unit, integration, and network tests.

## Running Tests

```bash
# Run all tests (skips integration and network by default)
uv run pytest tests/

# Run only fast unit tests (no network, no Anki runtime needed)
uv run pytest tests/ -m "not integration and not network" \
  --ignore=tests/test_all_dictionaries.py \
  --ignore=tests/test_dictionary_index.py

# Run integration tests (requires real `anki` package installed)
uv run pytest tests/integration/

# Run network-dependent tests
uv run pytest tests/ -m "network"

# Full CI pipeline (lint + test)
python dev.py ci
```

## Test Markers

| Marker | Description |
|---|---|
| `integration` | Needs real `anki.collection.Collection` |
| `network` | Makes HTTP requests (Forvo, etc.) |

## Test Conventions

- **Unit tests** (`tests/test_*.py`) use the installed `anki` and `aqt` packages directly (no module-level mocks). The shared conftest at `tests/conftest.py` only stubs the addon's root `__init__.py` entry point.
- **Integration tests** (`tests/integration/`) use a headless `anki.collection.Collection` fixture (no Qt GUI required for basic DB tests). Widget-level tests use the `qapp` fixture which sets `QT_QPA_PLATFORM=offscreen` and imports `PyQt6.QtWebEngineWidgets` before creating a shared `QApplication`. They auto-skip when `anki` is not installed.
- **Network tests** are marked `@pytest.mark.network` and are excluded from the default test run.

**Note:** `test_all_dictionaries.py` and `test_dictionary_index.py` import `aqt` at module level, so they're excluded from the `not integration and not network` filter with `--ignore`. These files are marked `network` and should only run with network access and Qt libraries available.

## Key Integration Tests

Located in `tests/integration/test_addon_loads.py`:

| Test | What it catches |
|---|---|
| `test_all_qt_names_have_imports` | AST scan — any Qt symbol used in `dictionary.py` without a corresponding explicit import |
| `test_dictinterface_instantiation` | `QApplication`-required errors; uses session-scoped `qapp` fixture |
| `test_dictinterface_constructor_symbols` | Runtime resolution of `QThreadPool`, `QColor`, `QShortcut`, etc. in `__init__` |
| `test_image_resizer_runtime` | `QImage`/`QSize`/`Qt` resolution at runtime |
| `test_qthreadpool_instantiation` | Regression gate for previously-missing `QThreadPool` import |
| `test_main_window_importable` | `aqt.mw` wiring in `main_window.py` |
