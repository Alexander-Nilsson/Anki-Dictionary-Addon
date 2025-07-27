# Project Reorganization Plan

## Current Issues
- All Python modules are in the root directory (flat structure)
- Mixed concerns (UI, database, utilities, core logic)
- No clear separation between addon and standalone functionality
- Test files scattered or missing proper structure
- Static assets (HTML, CSS, JS, icons) mixed with Python code

## Proposed Structure

```
anki_dictionary_addon/
├── README.md
├── pyproject.toml
├── uv.lock
├── manifest.json                    # Anki addon manifest
├── meta.json                        # Anki addon metadata
├── config.json                      # Default configuration
├── __init__.py                      # Addon entry point
│
├── src/                             # Main source code
│   └── anki_dictionary/
│       ├── __init__.py
│       ├── core/                    # Core dictionary functionality
│       │   ├── __init__.py
│       │   ├── database.py          # dictdb.py → database operations
│       │   ├── dictionary.py        # midict.py → main dictionary logic
│       │   └── search.py           # Search algorithms and utilities
│       │
│       ├── ui/                      # User interface components
│       │   ├── __init__.py
│       │   ├── main_window.py       # Main dictionary interface
│       │   ├── settings/            # Settings UI
│       │   │   ├── __init__.py
│       │   │   ├── settings_gui.py  # addonSettings.py
│       │   │   ├── dict_groups.py   # addDictGroup.py
│       │   │   └── templates.py     # addTemplate.py
│       │   ├── dialogs/             # Various dialog windows
│       │   │   ├── __init__.py
│       │   │   ├── dictionary_manager.py  # dictionaryManager.py
│       │   │   ├── theme_editor.py  # themeEditor.py
│       │   │   └── wizard.py        # dict_wizard.py, migaku_wizard.py
│       │   └── themes.py            # Theme management
│       │
│       ├── integrations/            # External service integrations
│       │   ├── __init__.py
│       │   ├── forvo.py             # forvodl.py → Forvo audio
│       │   ├── image_search.py      # duckduckgoimages.py
│       │   └── japanese.py          # miJapaneseHandler.py
│       │
│       ├── utils/                   # Utility modules
│       │   ├── __init__.py
│       │   ├── common.py            # miutils.py → common utilities
│       │   ├── clipboard.py         # Pyperclip.py
│       │   ├── updater.py           # miUpdater.py
│       │   ├── history.py           # User search history
│       │   └── ffmpeg.py            # ffmpegInstaller.py
│       │
│       ├── exporters/               # Card export functionality
│       │   ├── __init__.py
│       │   └── card_exporter.py     # cardExporter.py
│       │
│       └── web/                     # Web interface components
│           ├── __init__.py
│           ├── config.py            # webConfig.py
│           ├── windows.py           # freqConjWebWindow.py
│           └── installer.py         # dictionaryWebInstallWizard.py
│
├── assets/                          # Static assets
│   ├── templates/                   # HTML templates
│   │   ├── dictionary.html          # dictionaryInit.html
│   │   ├── welcome.html
│   │   ├── macwelcome.html
│   │   ├── zeroresults.html
│   │   └── guide.html
│   ├── styles/                      # CSS files
│   │   └── guide.css
│   ├── scripts/                     # JavaScript files
│   │   └── (move JS from dictionaryInit.html)
│   └── icons/                       # Icon files (keep existing structure)
│       ├── anki.png
│       ├── miso.png
│       └── ...
│
├── standalone/                      # Standalone execution scripts
│   ├── __init__.py
│   ├── launcher.py                  # Unified launcher (replaces multiple launchers)
│   ├── environment.py               # Minimal Anki environment setup
│   ├── import_patcher.py            # Import handling for standalone mode
│   └── demo.py                      # demo_refactored.py
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── conftest.py                  # pytest configuration
│   ├── unit/                        # Unit tests
│   │   ├── test_core/
│   │   ├── test_ui/
│   │   ├── test_integrations/
│   │   └── test_utils/
│   ├── integration/                 # Integration tests
│   └── fixtures/                    # Test data and fixtures
│
├── user_files/                      # User data (keep existing structure)
│   ├── db/
│   ├── media/
│   └── ...
│
├── vendor/                          # Third-party dependencies (keep existing)
│   └── ...
│
├── docs/                            # Documentation
│   ├── README_REFACTORED.md
│   ├── README_RUN_WITHOUT_ANKI.md
│   ├── INSTALLATION.md
│   ├── DEVELOPMENT.md
│   └── API.md
│
└── scripts/                         # Development and maintenance scripts
    ├── build.py                     # Build script for addon
    ├── test.py                      # Test runner
    └── package.py                   # Package for distribution
```

## Migration Steps

### Phase 1: Core Restructuring
1. Create new directory structure
2. Move and rename core modules:
   - `dictdb.py` → `src/anki_dictionary/core/database.py`
   - `midict.py` → `src/anki_dictionary/core/dictionary.py`
   - `miutils.py` → `src/anki_dictionary/utils/common.py`

### Phase 2: UI Organization
1. Group UI components:
   - `addonSettings.py` → `src/anki_dictionary/ui/settings/settings_gui.py`
   - `addDictGroup.py` → `src/anki_dictionary/ui/settings/dict_groups.py`
   - `themeEditor.py` → `src/anki_dictionary/ui/dialogs/theme_editor.py`
   - `themes.py` → `src/anki_dictionary/ui/themes.py`

### Phase 3: Integration Modules
1. Organize external integrations:
   - `forvodl.py` → `src/anki_dictionary/integrations/forvo.py`
   - `duckduckgoimages.py` → `src/anki_dictionary/integrations/image_search.py`
   - `miJapaneseHandler.py` → `src/anki_dictionary/integrations/japanese.py`

### Phase 4: Assets and Templates
1. Move static files to `assets/` directory
2. Extract JavaScript from HTML templates to separate files
3. Organize CSS and icons

### Phase 5: Standalone and Testing
1. Consolidate standalone scripts into `standalone/` directory
2. Create proper test structure with pytest
3. Set up development tools and scripts

## Benefits of This Structure

### 1. **Clear Separation of Concerns**
- Core logic separate from UI
- Utilities clearly organized
- External integrations isolated

### 2. **Easier Maintenance**
- Related code grouped together
- Clear dependency hierarchy
- Easier to find and modify specific functionality

### 3. **Better Testing**
- Proper test structure with pytest
- Unit tests organized by module
- Integration tests separate from unit tests

### 4. **Improved Development Experience**
- Clear entry points for different use cases
- Better IDE support with proper package structure
- Consistent import patterns

### 5. **Professional Structure**
- Follows Python packaging standards
- Uses src/ layout for better isolation
- Clear documentation organization

### 6. **Standalone Support**
- Dedicated standalone directory
- Clear separation from addon functionality
- Easier to maintain standalone scripts

## Implementation Notes

1. **Backward Compatibility**: During migration, keep old import paths working with import redirects
2. **Gradual Migration**: Can be done incrementally, module by module
3. **Testing**: Each moved module should have corresponding tests
4. **Documentation**: Update all documentation to reflect new structure
5. **Build Process**: Update build scripts to work with new structure

## Alternative: Minimal Reorganization

If a full restructure is too much work, a minimal reorganization could be:

```
anki_dictionary_addon/
├── addon/                           # Main addon code
│   ├── core/                        # Core functionality
│   ├── ui/                          # User interface
│   ├── utils/                       # Utilities
│   └── integrations/                # External services
├── standalone/                      # Standalone scripts
├── assets/                          # Static files
├── tests/                           # Test suite
├── docs/                            # Documentation
└── user_files/                      # User data
```

This provides many of the same benefits with less disruption to existing code.

## Detailed File Migration Map

### Files That Are Simply MOVED/RENAMED (Content Stays Same)

#### Core Modules
```
dictdb.py                    → src/anki_dictionary/core/database.py        [MOVE + RENAME]
midict.py                    → src/anki_dictionary/core/dictionary.py      [MOVE + RENAME]
```

#### UI Components  
```
addonSettings.py             → src/anki_dictionary/ui/settings/settings_gui.py    [MOVE + RENAME]
addDictGroup.py              → src/anki_dictionary/ui/settings/dict_groups.py     [MOVE + RENAME]
addTemplate.py               → src/anki_dictionary/ui/settings/templates.py       [MOVE + RENAME]
themeEditor.py               → src/anki_dictionary/ui/dialogs/theme_editor.py     [MOVE + RENAME]
themes.py                    → src/anki_dictionary/ui/themes.py                   [MOVE]
dictionaryManager.py         → src/anki_dictionary/ui/dialogs/dictionary_manager.py [MOVE + RENAME]
```

#### Integration Modules
```
forvodl.py                   → src/anki_dictionary/integrations/forvo.py          [MOVE + RENAME]
duckduckgoimages.py          → src/anki_dictionary/integrations/image_search.py   [MOVE + RENAME]
miJapaneseHandler.py         → src/anki_dictionary/integrations/japanese.py       [MOVE + RENAME]
```

#### Utility Modules
```
miutils.py                   → src/anki_dictionary/utils/common.py                [MOVE + RENAME]
Pyperclip.py                 → src/anki_dictionary/utils/clipboard.py             [MOVE + RENAME]
miUpdater.py                 → src/anki_dictionary/utils/updater.py               [MOVE + RENAME]
history.py                   → src/anki_dictionary/utils/history.py               [MOVE]
ffmpegInstaller.py           → src/anki_dictionary/utils/ffmpeg.py                [MOVE + RENAME]
```

#### Exporter Modules
```
cardExporter.py              → src/anki_dictionary/exporters/card_exporter.py     [MOVE]
```

#### Web Components
```
webConfig.py                 → src/anki_dictionary/web/config.py                  [MOVE + RENAME]
freqConjWebWindow.py         → src/anki_dictionary/web/windows.py                 [MOVE + RENAME]
dictionaryWebInstallWizard.py → src/anki_dictionary/web/installer.py             [MOVE + RENAME]
```

#### Assets (Static Files)
```
dictionaryInit.html          → assets/templates/dictionary.html                  [MOVE + RENAME]
welcome.html                 → assets/templates/welcome.html                     [MOVE]
macwelcome.html              → assets/templates/macwelcome.html                  [MOVE]
zeroresults.html             → assets/templates/zeroresults.html                 [MOVE]
guide.html                   → assets/templates/guide.html                       [MOVE]
guide.css                    → assets/styles/guide.css                           [MOVE]
icons/                       → assets/icons/                                     [MOVE FOLDER]
js/                          → assets/scripts/                                   [MOVE FOLDER]
```

#### Documentation
```
README_REFACTORED.md         → docs/README_REFACTORED.md                         [MOVE]
README_RUN_WITHOUT_ANKI.md   → docs/README_RUN_WITHOUT_ANKI.md                  [MOVE]
```

### Files That Need SIGNIFICANT CHANGES

#### Main Entry Point (SPLIT FUNCTIONALITY)
```
main.py                      → SPLIT INTO:
                               - __init__.py (Anki addon entry point)
                               - src/anki_dictionary/ui/main_window.py (UI logic)
                               - src/anki_dictionary/core/hooks.py (Anki integration)
```

#### Wizard Files (CONSOLIDATE)
```
dict_wizard.py               → MERGE INTO:
migaku_wizard.py               src/anki_dictionary/ui/dialogs/wizard.py
migakuMessage.py               
misoMessage.py               
```

#### Complex Templates (SPLIT)
```
dictionaryInit.html          → SPLIT INTO:
                               - assets/templates/dictionary.html (HTML structure)
                               - assets/scripts/dictionary.js (JavaScript logic)
                               - assets/styles/dictionary.css (Embedded styles)
```

### Standalone Scripts (CONSOLIDATE)
```
launch_dictionary.py         → CONSOLIDATE INTO:
external_launcher.py           standalone/launcher.py
package_launcher.py            
standalone_wrapper.py         
import_patcher.py            → standalone/import_patcher.py     [MOVE]
demo_refactored.py           → standalone/demo.py               [MOVE + RENAME]
```

### Files That Stay in ROOT (Unchanged Location)
```
__init__.py                  → __init__.py                      [MODIFY CONTENT]
pyproject.toml               → pyproject.toml                   [STAYS]
config.json                  → config.json                     [STAYS]
manifest.json                → manifest.json                   [STAYS]
meta.json                    → meta.json                       [STAYS]
README.md                    → README.md                       [STAYS]
uv.lock                      → uv.lock                         [STAYS]
user_files/                  → user_files/                     [STAYS - NO CHANGE]
vendor/                      → vendor/                         [STAYS - NO CHANGE]
temp/                        → temp/                           [STAYS - NO CHANGE]
```

### New Files to CREATE
```
src/anki_dictionary/__init__.py     [NEW - package initialization]
src/anki_dictionary/core/__init__.py         [NEW]
src/anki_dictionary/ui/__init__.py           [NEW]
src/anki_dictionary/ui/settings/__init__.py  [NEW]
src/anki_dictionary/ui/dialogs/__init__.py   [NEW]
src/anki_dictionary/integrations/__init__.py [NEW]
src/anki_dictionary/utils/__init__.py        [NEW]
src/anki_dictionary/exporters/__init__.py    [NEW]
src/anki_dictionary/web/__init__.py          [NEW]
standalone/__init__.py              [NEW]
standalone/environment.py          [NEW - extracted from various launchers]
tests/conftest.py                   [NEW]
tests/__init__.py                   [NEW]
scripts/build.py                    [NEW]
scripts/test.py                     [NEW]
scripts/package.py                  [NEW]
```

## Import Changes Required

### Files That Need Import Updates (But No Logic Changes)

All moved files will need their imports updated from:
```python
# OLD (relative imports)
from . import dictdb
from . import miutils
from . import themes

# NEW (absolute imports)
from anki_dictionary.core.database import DictDB
from anki_dictionary.utils.common import miInfo
from anki_dictionary.ui.themes import ThemeManager
```

### Files That Reference Moved Files

Any file that imports moved modules will need updates:
```python
# Files that will need import updates:
- __init__.py (addon entry point)
- All standalone scripts
- All moved modules that import each other
```

## Summary by Action Type

| Action Type | File Count | Examples |
|-------------|------------|----------|
| **Simple Move** | ~8 files | `themes.py`, `history.py`, `cardExporter.py` |
| **Move + Rename** | ~15 files | `dictdb.py` → `database.py`, `miutils.py` → `common.py` |
| **Split/Refactor** | ~3 files | `main.py`, `dictionaryInit.html` |
| **Consolidate** | ~6 files | Multiple launcher scripts → single launcher |
| **Stay Same** | ~8 files | `config.json`, `manifest.json`, `user_files/` |
| **New Files** | ~17 files | All `__init__.py` files, test structure, build scripts |

The majority of files (about 70%) are simple moves or renames with import updates. Only a few files require significant restructuring.
