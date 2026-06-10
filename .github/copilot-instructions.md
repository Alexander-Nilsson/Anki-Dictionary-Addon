# Copilot Instructions for Anki Dictionary Addon

## Project Overview

The **Anki Dictionary Addon** is a PyQt6-based dictionary interface for Anki 25.07+ that allows users to look up definitions, frequency data, and pronunciations across multiple languages, with real-time export to Anki cards.

**Key Technologies:**
- Python 3.13+ (strict type checking with ty)
- PyQt6 for UI (leverages Anki's bundled Qt)
- AnkiWebView (QtWebEngine) for rendering HTML/CSS/JS
- SQLite for dictionary data storage
- DuckDuckGo API for image search
- Async/await for LLM integration and long-running tasks

---

## Development Workflow

### Setup Environment

```bash
# Install dependencies with uv (recommended)
uv sync

# Or via dev helper
python dev.py install
```

### Running Tests

```bash
# Run full test suite
python dev.py test

# Run tests directly
python tests/run_tests.py

# Run specific test file (when tests are expanded)
python -m pytest tests/test_specific.py -v
```

### Code Quality

```bash
# Check linting and formatting
python dev.py lint

# Auto-format code (black)
python dev.py format

# Run full CI checks (lint + test)
python dev.py ci
```

### Building & Packaging

```bash
# Build addon package (.ankiaddon file)
python dev.py build

# Clean build artifacts
python dev.py clean
```

**Build Process Overview:**
- Vendors minimal dependencies (`pynput`) to `vendor/`
- Creates `user_files/` structure (themes, empty database)
- Bundles assets and generates `manifest.json`
- Packages into `.ankiaddon` file in `build/`

---

## Architecture

### Directory Structure

```
src/anki_dictionary/
├── core/              # Core dictionary logic
│   ├── database.py    # DictDB: SQLite interface for dictionary data
│   ├── dictionary.py  # DictInterface: Main dictionary UI/logic, ClipThread
│   └── hooks.py       # Anki addon hook initialization
├── ui/                # User interface components
│   ├── main_window.py # Main window management, hotkeys
│   ├── themes.py      # ThemeManager: Dynamic theming system
│   ├── dialogs/       # Theme editor, dictionary manager, wizard
│   └── settings/      # Settings GUI, template editor, dictionary groups
├── integrations/      # External service integrations
│   ├── image_search.py  # DuckDuckGo image search integration
│   ├── japanese.py      # Japanese-specific features
│   └── llm.py           # LLM integration for AI definitions
├── exporters/         # Card export logic
├── utils/             # Utilities (config, history, clipboard, logger, FFmpeg)
└── web/               # Web components (HTML templates, JS)

assets/               # HTML/CSS/JS assets (inlined at runtime)
tests/                # Test suite (unittest framework)
vendor/               # Bundled dependencies (pynput, created during build)
user_files/           # User data: DBs, themes, media (created during build)
```

### Key Architectural Patterns

#### 1. **Core Dictionary Loop**
- `DictInterface` (in `core/dictionary.py`) is the main orchestrator
- `ClipThread` monitors clipboard for word changes
- Lookup engine queries `DictDB` (SQLite wrapper)
- Results rendered in `AnkiWebView` (QtWebEngine)
- User can export findings to Anki cards via export dialogs

#### 2. **Database Layer** (`core/database.py`)
- `DictDB` class provides SQLite interface
- Dictionary data stored in `user_files/dicts/` as SQLite files
- Queries abstract schema differences across dictionary types
- Methods: `lookup()`, `search()`, `get_definition()`, etc.

#### 3. **UI & Theming**
- **AnkiWebView**: Main display uses QtWebEngine for HTML/CSS/JS rendering
- **ThemeManager** (`ui/themes.py`): Handles dynamic theme loading/switching
- Active theme stored in `user_files/themes/active.json`
- Themes are JSON-based; CSS/HTML injected at runtime via `assets/`

#### 4. **Async Operations**
- Image search, LLM calls, and clipboard monitoring use `asyncio`
- Long-running tasks offload to background threads to prevent UI freezes
- Integrations use `aiohttp` for async HTTP requests

#### 5. **Dependency Strategy**
- **Bundled**: Only `pynput` (needed for global hotkeys on macOS/Linux)
- **External but Lightweight**: `requests`, `Pillow`, `PyQt6` (Anki provides these)
- **Avoid Heavy Dependencies**: Don't add large packages; prefer Anki's bundled libraries

#### 6. **Hooks & Initialization**
- Addon hooks registered in `src/anki_dictionary/core/hooks.py`
- Entry point is `src/anki_dictionary/__init__.py`
- Anki injects `mw` (main window) globally; legacy code accesses via `mw.__dict__`

---

## Code Organization Conventions

### File Naming & Imports

- **Module imports**: Use absolute imports within the package (e.g., `from anki_dictionary.core.database import DictDB`)
- **Type hints**: Encouraged throughout; use `Optional`, `List`, `Dict`, `Tuple`, `Union` from `typing`
- **Docstrings**: Include for public classes and functions

### Formatting & Linting

- **Code formatter**: `black` (max line length: 88)
- **Linter**: `flake8` with max complexity 10
  - Ignores: E501 (line length), W503 (binary operator placement)
  - Focuses on: E9, F63, F7, F82 (syntax/import errors)
- **Type checking**: `ty` in strict mode for `src/` directory
- Python 3.13+ features allowed; `requires-python = ">=3.13"`

### Common Patterns

**Logger Usage** (utils/logger.py):
```python
from anki_dictionary.utils.logger import get_logger
logger = get_logger("module_name")
logger.info("Message")
```

**Configuration Access** (utils/common.py):
```python
from anki_dictionary.utils.common import miInfo, miAsk
config = miInfo()  # Get addon config
```

**Database Operations** (core/database.py):
```python
from anki_dictionary.core.database import DictDB
db = DictDB()
results = db.lookup("word")
```

**Asset Injection** (web components):
- HTML/CSS/JS stored in `assets/` as separate files
- Loaded and injected into `AnkiWebView` at runtime
- Use template variables for dynamic values

---

## Anki API Integration

- Addon reliesón `aqt` (Anki Qt) and `anki` packages (bundled with Anki)
- Common imports:
  - `from aqt import mw` – Main window reference
  - `from aqt.webview import AnkiWebView` – Web view for rendering
  - `from aqt.utils import showInfo, askUser` – UI dialogs
  - `from anki.hooks import runHook` – Anki hooks
  - `from anki.utils import is_mac, is_win, is_lin` – Platform checks
- Hotkey binding uses `pynput` (vendored)

---

## Testing

**Test Framework**: `unittest` (built-in Python)

**Test Files Location**: `tests/` directory with `test_*.py` naming

**Running Tests**:
```bash
# All tests
python tests/run_tests.py

# Specific test
python -m pytest tests/test_module.py::TestClass::test_method -v
```

**Test Conventions**:
- Test files should not depend on live Anki instance (mock `aqt`, `anki` modules if needed)
- Use `unittest.TestCase` as base class
- Group related tests into test classes

---

## Extending the Addon

### Adding a New Feature

1. **Create module** in appropriate directory (e.g., `src/anki_dictionary/integrations/new_feature.py`)
2. **Add exports** to `__init__.py` in parent directory if public API
3. **Write tests** in `tests/test_new_feature.py`
4. **Register hooks** if needed in `core/hooks.py`
5. **Update UI** if user-facing (add to settings, dialogs, or main window)
6. **Run CI**: `python dev.py ci` before committing

### Adding a Dictionary Format

1. Implement format parser in `core/database.py` or separate module
2. Add lookup logic to `DictDB.lookup()` or create specialized method
3. Register format handler in configuration
4. Test with sample dictionary file

### Integrating External Service

1. Create module in `integrations/` (e.g., `integrations/my_service.py`)
2. Use `aiohttp` for async requests if appropriate
3. Add error handling and fallback behavior
4. Document API authentication/configuration needs
5. Log operations via `get_logger()`

---

## Build & Distribution

**Build Output**: `.ankiaddon` file (ZIP format) in `build/` directory

**Installation**:
- Users install via Anki's "Install from file" dialog
- Or copy unpacked addon folder to Anki addons folder

**Versioning**: Read from `pyproject.toml` `[project].version`

**Manifest**: Auto-generated during build; don't edit manually

---

## Debugging Tips

- **Enable Logging**: Check `logs/` directory for runtime logs
- **Console Output**: Anki console (Tools > Add-ons > ... > View Files > ...) shows print/warnings
- **Clipboard Monitoring**: ClipThread logs in `core/dictionary.py`
- **Theme Issues**: Check `user_files/themes/active.json` for active theme configuration
- **Database**: SQLite files in `user_files/dicts/`; inspect with SQLite browser if needed
- **Hot Reload**: Restart Anki after code changes; addon code is loaded at startup

---

## Quick Checklist for Code Changes

- [ ] Code passes `python dev.py lint`
- [ ] Code passes `python dev.py test`
- [ ] Type hints added for new functions (especially public API)
- [ ] Docstrings added for new classes/functions
- [ ] No hard dependencies added (vendor only lightweight packages)
- [ ] Anki bundled libraries used when available (PyQt6, requests, Pillow)
- [ ] Logging used instead of print() for production code
- [ ] Assets properly injected into AnkiWebView, not embedded in Python
- [ ] Platform-specific code uses `is_mac()`, `is_win()`, `is_lin()` checks
- [ ] Async operations don't block UI thread

---

## Common Gotchas

1. **Anki Global Context**: `mw` (main window) is injected globally at addon load time; don't import at module level if testing outside Anki
2. **Vendored Dependencies**: Only `pynput` is bundled; other packages rely on Anki's versions
3. **Theme Updates**: Active theme must be reloaded; changes to `active.json` don't auto-refresh
4. **Asset Caching**: Browser caches JS/CSS; clear on changes or use cache-busting query params
5. **Platform Differences**: Test macOS-specific imports (`pyobjc`) on actual macOS; they're optional
6. **Type Checking**: ty strict mode is enforced; all type hints must pass

---

## MCP Servers

**Configured MCP Servers**:

### Playwright MCP
Location: `.github/mcp-servers.json`

Enables web/UI testing capabilities via the Model Context Protocol. Useful for:
- Testing AnkiWebView component rendering
- Validating HTML/CSS/JS assets before bundling
- Automating browser-based testing for dictionary lookups
- Verifying theme rendering across different layouts

**Setup**:
```bash
# Install Node.js (if not already installed)
# MCP server will be installed on-demand via npx

# Playwright will auto-download chromium on first use
# This is handled transparently by the MCP server
```

**Usage in Copilot**:
- Ask Copilot to help write or review web component tests
- Request browser automation scripts for testing UI workflows
- Get feedback on HTML/CSS/JS asset quality

**Note**: Playwright MCP is optional. If you don't use it, existing linting (`flake8`) and type checking (`ty`) cover Python code quality. Web component testing can also be done manually via the browser console in Anki.
