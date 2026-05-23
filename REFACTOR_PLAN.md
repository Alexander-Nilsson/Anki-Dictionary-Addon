# Remaining Refactoring Work

### Stage 1: Inject `mw` Instead of Importing Globally
**Goal**: Remove module-level `from aqt import mw` in testable UI code.

Still deferred (deeply coupled, need wider refactor):

| File | Reason |
|---|---|
| `utils/config.py` | Uses `mw.__dict__` for config persistence |
| `utils/logger.py` | Uses `mw.pm` for log directory (has safe fallback) |
| `core/database.py` | Uses `mw.pm.addonFolder()` as path fallback |
| `ui/main_window.py` | Fundamentally a wiring module that attaches globals to `mw` |

### Stage 2: Potential Further God Class Splits
**Goal**: Continue breaking up large classes (>500 lines).

| Target | Lines | Suggestion |
|---|---|---|
| `DictInterface` (`core/dictionary.py`) | 1563 | Extract rendering/view logic |
| `SearchPipeline` (`core/search_pipeline.py`) | 1324 | Now the largest god class |
| `CardExporter` (`exporters/card_exporter.py`) | 755 | Separate batch vs single-card paths |

### Stage 3: Add Type Hints
**Goal**: Full Pyright strict compliance (actionable items only).

| Issue | Count |
|---|---|
| `reportMissingParameterType` (missing param/return annotations) | **420** errors |

Note: ~4800 cascade errors from untyped PyQt6/anki/aqt deps are not actionable without third-party stubs.

### Stage 5: Add Tests for Untested Modules

| Module | Priority | Reason |
|---|---|---|
| `DictGroupEditor` | Medium | Config modification pathways |
| `TemplateEditor` | Medium | Config modification pathways |
| Web installer wizard (`installer.py`) | Low | 796 lines, zero coverage |

---

## Verification
```bash
python dev.py lint   # flake8 + black
python dev.py test   # unit + integration
pytest tests/ -m "not integration and not network"  # fast unit tests
```
