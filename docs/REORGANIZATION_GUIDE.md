# Anki Dictionary Addon - Reorganized Structure

## Overview

The Anki Dictionary Addon has been completely reorganized to follow Python best practices and modern project structure. This reorganization improves maintainability, modularity, and makes the codebase easier to understand and extend.

## New Project Structure

```
anki-dictionary-addon/
├── src/anki_dictionary/          # Main package source code
│   ├── __init__.py               # Package initialization
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── database.py           # Database operations (was dictdb.py)
│   │   ├── dictionary.py         # Main dictionary interface (was midict.py)
│   │   └── hooks.py              # Anki integration hooks (split from main.py)
│   ├── ui/                       # User interface components
│   │   ├── __init__.py
│   │   ├── main_window.py        # Main UI logic (split from main.py)
│   │   ├── themes.py             # Theme management
│   │   ├── settings/             # Settings UI components
│   │   │   ├── __init__.py
│   │   │   ├── settings_gui.py   # Main settings GUI (was addonSettings.py)
│   │   │   ├── dict_groups.py    # Dictionary group editor (was addDictGroup.py)
│   │   │   └── templates.py      # Template editor (was addTemplate.py)
│   │   └── dialogs/              # Dialog components
│   │       ├── __init__.py
│   │       ├── dictionary_manager.py  # Dictionary manager (was dictionaryManager.py)
│   │       ├── theme_editor.py   # Theme editor (was themeEditor.py)
│   │       └── wizard.py         # Consolidated wizard (was dict_wizard.py, migaku_wizard.py, etc.)
│   ├── utils/                    # Utility modules
│   │   ├── __init__.py
│   │   ├── common.py             # Common utilities (was miutils.py)
│   │   ├── history.py            # History management
│   │   ├── clipboard.py          # Clipboard operations (was Pyperclip.py)
│   │   ├── ffmpeg.py             # FFMPEG installer (was ffmpegInstaller.py)
│   │   └── updater.py            # Auto-updater (was miUpdater.py)
│   ├── integrations/             # External service integrations
│   │   ├── __init__.py
│   │   ├── forvo.py              # Forvo integration (was forvodl.py)
│   │   ├── image_search.py       # Image search (was duckduckgoimages.py)
│   │   └── japanese.py           # Japanese language handler (was miJapaneseHandler.py)
│   ├── exporters/                # Export functionality
│   │   ├── __init__.py
│   │   └── card_exporter.py      # Card export (was cardExporter.py)
│   └── web/                      # Web-related components
│       ├── __init__.py
│       ├── config.py             # Web configuration (was webConfig.py)
│       ├── windows.py            # Web windows (was freqConjWebWindow.py)
│       └── installer.py          # Web installer (was dictionaryWebInstallWizard.py)
├── assets/                       # Asset files
│   ├── templates/
│   │   └── dictionary.html       # Main HTML template (was dictionaryInit.html)
│   ├── styles/
│   │   └── guide.css             # Stylesheets (was guide.css)
│   ├── scripts/
│   │   └── dictionary.js         # JavaScript (extracted from HTML)
│   └── icons/                    # Icon files (was icons/)
├── standalone/                   # Standalone launcher components
│   ├── __init__.py
│   ├── demo.py                   # Standalone demo (was demo_refactored.py)
│   ├── launcher.py               # External launcher (was external_launcher.py)
│   └── import_patcher.py         # Import patching utilities
├── docs/                         # Documentation
│   ├── README_REFACTORED.md      # Refactoring documentation
│   └── README_RUN_WITHOUT_ANKI.md # Standalone usage
├── __init__.py                   # Anki addon entry point (was main.py imports)
├── launch_dictionary.py          # Standalone launcher script
├── build.py                      # Build and packaging script
└── pyproject.toml                # Project configuration
```

## Key Improvements

### 1. **Modular Architecture**
- Clear separation of concerns with dedicated packages for different functionality
- Core logic separated from UI components
- Utilities and integrations properly organized

### 2. **Python Best Practices**
- Proper package structure with `__init__.py` files
- Descriptive module and file names
- Clear import hierarchy and dependencies

### 3. **Asset Organization**
- HTML templates in `assets/templates/`
- CSS stylesheets in `assets/styles/`
- JavaScript extracted to `assets/scripts/`
- Icons organized in `assets/icons/`

### 4. **Enhanced Maintainability**
- Related functionality grouped together
- Reduced file size and complexity
- Better code discoverability

### 5. **Build System**
- Automated build script for packaging
- Support for both Anki addon and standalone distributions
- Clean separation of build artifacts

## Migration Benefits

1. **Developer Experience**: Much easier to find and modify specific functionality
2. **Code Quality**: Better organization leads to cleaner, more maintainable code
3. **Testing**: Modular structure makes unit testing more straightforward
4. **Documentation**: Clear structure makes the codebase self-documenting
5. **Collaboration**: New contributors can understand the project structure quickly

## Usage

### As Anki Addon
The addon works exactly as before from a user perspective. All functionality remains the same.

### Standalone Mode
```bash
python launch_dictionary.py
```

### Building and Packaging
```bash
# Build addon package
python build.py package

# Build standalone version
python build.py standalone

# Build everything
python build.py all

# Clean build artifacts
python build.py clean
```

## Compatibility

- ✅ Full backward compatibility with existing Anki installations
- ✅ All original features preserved
- ✅ Standalone mode still functional
- ✅ Configuration and data files unchanged

## Development

The new structure makes development much more pleasant:

1. **Finding Code**: Use the logical package structure to locate functionality
2. **Adding Features**: Add new modules in the appropriate package
3. **Testing**: Import specific modules for unit testing
4. **Debugging**: Clearer stack traces with meaningful module names

## File Mapping

| Original File | New Location | Notes |
|---------------|--------------|-------|
| `main.py` | Split into `__init__.py`, `ui/main_window.py`, `core/hooks.py` | Separated concerns |
| `dictdb.py` | `core/database.py` | More descriptive name |
| `midict.py` | `core/dictionary.py` | Clearer naming |
| `miutils.py` | `utils/common.py` | Better organization |
| `addonSettings.py` | `ui/settings/settings_gui.py` | Grouped with settings |
| `dictionaryInit.html` | `assets/templates/dictionary.html` | Asset organization |
| `dict_wizard.py`, `migaku_wizard.py` | `ui/dialogs/wizard.py` | Consolidated duplicates |
| And many more... | See full structure above | Systematic organization |

This reorganization provides a solid foundation for future development while maintaining complete compatibility with existing functionality.
