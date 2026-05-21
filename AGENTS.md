# Anki Dictionary Addon — Agent Guide

## Project Overview
PyQt6-based dictionary lookup addon for **Anki 25.09+**, successor to the Migaku Dictionary Addon. Supports multi-dictionary lookup, AI definitions (LLM), image search (DuckDuckGo), Forvo audio, and one-click card export.

**Key Technologies:** Python 3.13+ | PyQt6/Qt6 (via Anki) | SQLite | DuckDuckGo API | LLM (OpenAI/Ollama) | Forvo | `uv` | Pyright (strict)

## Project Structure
```
src/anki_dictionary/
├── core/
│   ├── database.py      # DictDB — SQLite wrapper for dictionary lookups
│   ├── dictionary.py    # DictInterface — main dictionary UI, ClipThread (clipboard)
│   └── hooks.py         # Anki addon hook registration
├── ui/
│   ├── main_window.py   # Main window, hotkey management
│   ├── themes.py        # ThemeManager — dynamic theming
│   ├── dialogs/
│   │   ├── dictionary_manager.py
│   │   ├── theme_editor.py
│   │   └── wizard.py
│   └── settings/
│       ├── settings_gui.py
│       ├── dict_groups.py
│       └── templates.py
├── integrations/
│   ├── image_search.py  # DuckDuckGo image search
│   ├── forvo.py         # Forvo audio scraping
│   └── llm.py           # LLM (AI) definition generation
├── exporters/
│   └── card_exporter.py # Card export logic
├── utils/
│   ├── config.py, common.py, constants.py, paths.py
│   ├── clipboard.py, history.py, logger.py
└── web/
    ├── installer.py, windows.py, icons.py, config.py
assets/
├── templates/            # dictionary.html, guide.html, welcome.html, etc.
├── styles/               # guide.css
├── scripts/              # dictionary.js, insertHTML.js
└── icons/                # 30 SVG icons (day/night variants)
tests/
├── conftest.py           # Shared mocks for aqt/anki
├── integration/          # Real Anki runtime tests
│   ├── conftest.py
│   └── test_addon_loads.py
├── test_database.py, test_forvo.py, test_llm.py
├── test_themes.py, test_addon_structure.py
├── test_all_dictionaries.py, test_dictionary_index.py
└── run_tests.py
scripts/                  # create_empty_db.py, create_default_themes.py, release.py
vendor/                   # Bundled deps (pynput, bs4) — created during build
user_files/               # db/, dictionaries/, themes/, fonts/, media/
```

## Development Commands
| Command | Action |
|---|---|
| `uv sync` | Install dependencies |
| `python dev.py test` | Run test suite (unit + integration) |
| `python dev.py lint` | flake8 + black --check |
| `python dev.py format` | black auto-format |
| `python dev.py ci` | lint + test (full CI check) |
| `python dev.py build` | Build .ankiaddon package |
| `python dev.py clean` | Clean build artifacts |
| `pytest tests/ -m "not integration and not network"` | Fast unit tests only |
| `pytest tests/integration/` | Integration tests (needs anki installed) |
| `act -j pipeline --input=false` | Run CI workflow locally via act to verify before pushing |

## Code Conventions
- **Naming:** `snake_case` for vars/funcs, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Formatting:** black (line length 88), flake8 (complexity ≤ 10)
- **Types:** Pyright strict mode — all new code must have type hints
- **Imports:** Absolute within package (`from anki_dictionary.core.database import DictDB`)
- **Logging:** Use `get_logger("module_name")` from `utils/logger.py`
- **Config:** Access via `miInfo()` / `miAsk()` from `utils/common.py`
- **Anki globals:** `mw` is injected at runtime; do not import at module level in testable code

## Architecture Notes
- **DictInterface** (`core/dictionary.py`) is the main orchestrator; renders results in `AnkiWebView`
- **ClipThread** monitors clipboard for word changes on a background thread
- **DictDB** (`core/database.py`) abstracts SQLite schema differences across dictionary types
- **Themes** are JSON-based; active theme stored in `user_files/themes/active.json`
- **LLM**, **image search**, and **Forvo** are async; use background threads to avoid UI freezes
- **Vendor strategy:** Only `pynput` and `beautifulsoup4` are bundled; rely on Anki's bundled PyQt6, requests, Pillow
- **Platform checks:** Use `is_mac()`, `is_win()`, `is_lin()` from `anki.utils`
- **Build:** `build.py` copies `src/`, `assets/`, `__init__.py`, `config.json`; vendors deps; generates manifest

## Test Markers
| Marker | Description |
|---|---|
| `integration` | Needs real `anki.collection.Collection` |
| `network` | Makes HTTP requests (Forvo, etc.) |

Unit tests mock `aqt`/`anki` modules (see `tests/conftest.py`). Integration tests auto-skip if `anki` not installed.
