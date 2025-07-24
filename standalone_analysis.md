# Making Anki Dictionary Addon Standalone - Feasibility Analysis

## Executive Summary

**Yes, it is possible to make the Anki Dictionary Addon runnable without Anki**, but it would require significant refactoring. The core dictionary functionality, image search, and database operations can be extracted and made standalone, but the current codebase is tightly integrated with Anki's APIs and Qt-based UI framework.

## Current Dependencies on Anki

### Critical Anki Dependencies
1. **aqt.qt** - Qt UI framework (371+ references to `mw.`)
2. **anki.hooks** - Event system for Anki integration
3. **aqt.webview.AnkiWebView** - Web-based UI components
4. **anki.utils** - Platform detection and utilities
5. **aqt.utils** - UI dialogs and notifications
6. **mw (main window)** - Anki's main application window

### Database Dependencies
- Uses `mw.pm.addonFolder()` for database path resolution
- Relies on Anki's profile management system

## Extractable Components

### ✅ Fully Extractable (Minimal Dependencies)
1. **Dictionary Database Logic** (`dictdb.py`)
   - SQLite operations
   - Dictionary management
   - Term searching

2. **Image Search** (`duckduckgoimages.py`)
   - DuckDuckGo image search
   - HTML generation for image galleries
   - Only needs requests library

3. **Audio Processing** (`forvodl.py`)
   - Forvo audio downloads
   - Audio file management

4. **Japanese Text Processing** (`miJapaneseHandler.py`)
   - Text parsing and analysis
   - Language-specific utilities

### ⚠️ Partially Extractable (Requires Refactoring)
1. **Core Dictionary Interface** (`midict.py`)
   - Heavy Qt/Anki integration
   - Could extract search logic
   - UI would need complete rewrite

2. **Configuration Management**
   - Currently uses Anki's config system
   - Could use standalone JSON config

3. **Theme System** (`themes.py`)
   - UI theming logic
   - Could work with different UI framework

### ❌ Anki-Specific (Not Extractable)
1. **Card Export** (`cardExporter.py`)
   - Directly creates Anki cards
   - Fundamental to Anki integration

2. **Editor Integration**
   - Hooks into Anki's card editor
   - Context menu integration

3. **Anki Hooks and Events**
   - Startup hooks
   - Review hooks
   - Editor hooks

## Standalone Implementation Approaches

### Approach 1: Web Application
Convert to a Flask/FastAPI web application:

```python
# Example structure
app/
├── main.py              # Web server
├── dictionary/
│   ├── database.py      # Extracted DB logic
│   ├── search.py        # Search functionality
│   └── images.py        # Image search
├── templates/           # HTML templates
├── static/             # CSS/JS assets
└── config.json         # Configuration
```

**Pros:**
- Cross-platform compatibility
- Modern web UI
- Easy deployment
- No Qt dependencies

**Cons:**
- Different user experience
- Requires web development

### Approach 2: Desktop Application (Tkinter/PyQt)
Create a standalone desktop application:

```python
# Example structure
standalone_dict/
├── main.py              # Main application
├── gui/
│   ├── main_window.py   # Main UI
│   ├── search_widget.py # Search interface
│   └── results_widget.py# Results display
├── core/
│   ├── database.py      # Dictionary DB
│   ├── search.py        # Search logic
│   └── images.py        # Image search
└── resources/           # Icons, themes
```

**Pros:**
- Native desktop experience
- Similar to original addon
- Offline capability

**Cons:**
- Platform-specific packaging
- UI framework dependency

### Approach 3: Command Line Tool
Create a CLI-based dictionary tool:

```bash
# Usage examples
dict-lookup hello
dict-lookup --language japanese こんにちは
dict-lookup --export-html --images hello
```

**Pros:**
- Minimal dependencies
- Easy to integrate with other tools
- Fast and lightweight

**Cons:**
- Limited UI capabilities
- Less user-friendly for general users

## Implementation Effort Estimate

### Phase 1: Core Extraction (2-3 weeks)
- Extract database operations
- Create standalone search functionality
- Implement basic image search
- Set up configuration system

### Phase 2: UI Development (3-4 weeks)
- Choose UI framework (web/desktop/CLI)
- Implement search interface
- Create results display
- Add basic theming

### Phase 3: Advanced Features (2-3 weeks)
- Audio integration
- Export functionality (non-Anki formats)
- Advanced search options
- Performance optimization

### Phase 4: Polish & Distribution (1-2 weeks)
- Packaging for different platforms
- Documentation
- Testing
- Distribution setup

**Total Estimated Effort: 8-12 weeks**

## Demonstration

I've created a working proof-of-concept (`standalone_dict_demo.py`) that demonstrates:

1. **Standalone Database**: SQLite-based dictionary storage without Anki
2. **Image Search**: DuckDuckGo integration without Qt dependencies
3. **HTML Export**: Generate standalone HTML results
4. **CLI Interface**: Command-line usage

### Running the Demo

```bash
# Basic lookup
python standalone_dict_demo.py hello

# This creates:
# - SQLite database with sample data
# - Image search results
# - HTML export file
```

## Recommended Approach

For maximum impact and usability, I recommend **Approach 1 (Web Application)**:

1. **Modern Interface**: Web-based UI with responsive design
2. **Cross-Platform**: Works on any device with a browser
3. **Easy Deployment**: Can be hosted locally or on a server
4. **Extensible**: Easy to add new features and integrations
5. **Familiar**: Similar to many modern dictionary applications

## Conclusion

The Anki Dictionary Addon can definitely be made standalone, but it requires significant architectural changes. The core functionality (dictionary lookup, image search, database management) is highly portable, but the UI and Anki integration layers need complete replacement.

The proof-of-concept demonstrates that the essential features can work independently, and with proper planning, a standalone version could offer even more flexibility and broader appeal than the Anki-specific version.