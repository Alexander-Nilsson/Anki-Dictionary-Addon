# Refactoring Plan: Structure & Quality Improvements

## Priority Order

### Stage 1: Inject `mw` Instead of Importing Globally
**Goal**: Remove module-level `from aqt import mw` in testable UI code. Pass `mw` as a constructor parameter instead.

| File | Change |
|---|---|
| `utils/paths.py` | Remove unused `from aqt import mw` (never referenced) |
| `ui/dialogs/wizard.py` | Remove unused `from aqt import mw` (never referenced) |
| `ui/settings/dict_groups.py` | Remove module-level `from aqt import mw` (already injected via constructor param) |
| `ui/themes.py` | Refactor `ThemeManager.__init__` to accept themes directory path instead of `mw.pm.addonFolder()` |
| `ui/dialogs/dictionary_manager.py` | Inject `mw` via constructor; remove module-level import. Update callers. |

*Deferred* (deeply coupled, need wider refactor):
- `utils/config.py` — uses `mw.__dict__` for config persistence
- `utils/logger.py` — uses `mw.pm` for log directory; has safe fallback
- `core/database.py` — uses `mw.pm.addonFolder()` as path fallback
- `ui/main_window.py` — fundamentally a wiring module that attaches globals to `mw`

### Stage 2: Split God Classes into Single-Responsibility Modules
**Goal**: Break up classes >500 lines into focused modules.

| God Class | Lines | Proposed Split |
|---|---|---|
| `DictInterface` (`core/dictionary.py`) | ~2280 | Extract `SearchPipeline`, `ClipboardMonitor`, `CardCreationHandler` |
| `CardExporter` (`exporters/card_exporter.py`) | ~1276 | Extract `FieldMapper`, `HtmlCleaner`, `BatchProcessor`, `MediaHandler` |
| `SettingsGui` (`ui/settings/settings_gui.py`) | ~846 | One class per settings tab |
| `DictionaryManagerWidget` (`ui/dialogs/dictionary_manager.py`) | ~1091 | Extract `DictImporter`, `TreeManager`, `LanguageManager` |

### Stage 3: Add Type Hints to All Untyped Code
**Goal**: Full Pyright strict compliance. Pervasive in UI, exporters, dialogs, and web modules.

- Add return type annotations to all methods
- Add parameter type annotations to all methods
- Replace `from aqt.qt import *` with specific imports (5 files)
- Fix 3 mutable default argument instances
- Fix mixed relative/absolute import styles

### Stage 4: Remove Dead Code + Replace `print()` with Logger
**Goal**: Eliminate dead functions/classes. Replace all `print()` error handling with `get_logger()`.

| Dead Code | File |
|---|---|
| `attemptOpenLink()` | `settings_gui.py` |
| `DictLabel` class | `settings_gui.py` |
| `AnkiSVG` class + `getSVGWidget()` | `settings_gui.py` |
| `search()` CLI entry point | `image_search.py` |
| `qt_message_handler` | `dictionary.py` |
| `kaner()` → rename to `kana_converter` | `dictionary_manager.py` |

Replace 32 `print()` calls across: `themes.py`, `theme_editor.py`, `main_window.py`, `dictionary_manager.py`, `dictionary.py`.

### Stage 5: Add Tests for Untested Critical Modules
**Goal**: Coverage for modules with 0% test coverage.

| Module | Priority |
|---|---|
| `CardExporter` | High — 1276 lines, core card creation |
| `SettingsGui` | Medium — config modification pathways |
| `DictGroupEditor` + `TemplateEditor` | Medium |
| `DuckDuckGo` image search | Medium |
| Web installer wizard (`installer.py`) | Low |

---

## Verification
After each stage:
```bash
python dev.py lint   # flake8 + black
python dev.py test   # unit + integration
pytest tests/ -m "not integration and not network"  # fast unit tests
```
