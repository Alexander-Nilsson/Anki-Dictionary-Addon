# Anki Dictionary Addon Repository

## Overview

This repository contains the **Anki Dictionary Addon**, a successor to the Migaku Dictionary Addon. It's designed to provide dictionary lookup functionality, frequency data, and audio pronunciations directly within Anki, allowing users to export this information to Anki cards in real-time.

## Project Structure

The main addon code is located in the `Anki-Dictionary-Addon/` directory, which contains:

- **Core Python modules**: Main functionality split across multiple Python files
- **Web assets**: HTML, CSS, and JavaScript files for the user interface
- **Icons and themes**: Visual assets and theming system
- **Vendor dependencies**: Third-party libraries bundled with the addon
- **User files**: Database, dictionaries, fonts, and configuration files

### Key Files

- `main.py` - Main entry point and core functionality
- `midict.py` - Dictionary interface and clipboard monitoring
- `dictdb.py` - Database management for dictionaries
- `themes.py` - Theme management system
- `duckduckgoimages.py` - Image search functionality (replaced Google Images)
- `manifest.json` - Addon metadata and requirements
- `config.json` - Default configuration settings

## Features

- **Dictionary Lookup**: Look up word definitions from multiple dictionary sources
- **Frequency Data**: Access word frequency information
- **Audio Pronunciations**: Get audio pronunciations for words
- **Real-time Export**: Export definitions and data to Anki cards instantly
- **Image Search**: Search for images using DuckDuckGo (Google Images replacement)
- **Theme System**: Customizable themes for the interface
- **Multi-platform Support**: Designed to work on Linux, Windows, and macOS

## Installation

This is an Anki addon that needs to be installed within Anki:

1. **Prerequisites**: 
   - Anki version 24.11 or compatible
   - Python dependencies are bundled in the `vendor/` directory

2. **Installation Steps**:
   - Copy the `Anki-Dictionary-Addon/` directory to your Anki addons folder:
     - **Linux**: `~/.local/share/Anki2/addons21/`
     - **Windows**: `%APPDATA%\Anki2\addons21\`
     - **macOS**: `~/Library/Application Support/Anki2/addons21/`

3. **Restart Anki** to load the addon

## How to Run/Test the Code

### Running the Addon
The addon runs automatically when Anki starts. It integrates into Anki's interface and provides:
- Dictionary lookup windows
- Card export functionality
- Settings and configuration panels

### Testing Individual Components

You can test specific components outside of Anki:

```bash
# Navigate to the addon directory
cd Anki-Dictionary-Addon/

# Test image search functionality
python test_search.py
```

This will test both Google and DuckDuckGo image search engines.

### Development Testing

For development and debugging:

1. **Enable Anki's debug mode** by starting Anki with debug flags
2. **Check Anki's addon manager** for any error messages
3. **Use Anki's built-in addon development tools**

## Configuration

The addon uses several configuration files:

- `config.json` - Main configuration with default settings
- `user_files/themes/active.json` - Active theme configuration
- `user_files/themes/themes.json` - Available themes
- `user_files/db/dictionaries.sqlite` - Dictionary database

## Current Status

- **Platform Compatibility**: Tested primarily on Linux
- **Anki Version**: Compatible with Anki 24.11
- **Known Issues**: 
  - Forvo integration is currently non-functional
  - Google Images replaced with DuckDuckGo

## Dependencies

The addon includes bundled dependencies in the `vendor/` directory:
- `requests` - HTTP library
- `bs4` (BeautifulSoup) - HTML parsing
- `tornado` - Web framework components
- `pynput` - Input handling
- `pyobjc-core` - macOS integration (macOS only)
- Various platform-specific modules

## Development

The codebase is structured as a traditional Anki addon with:
- Event hooks into Anki's interface
- Web-based UI components
- Database integration for dictionary management
- Cross-platform compatibility layers

## License

Released under GNU AGPLv3 license. This is free and open-source software distributed without warranty.

## Standalone Possibility

**Can this addon run without Anki?** Yes, with significant refactoring. The core dictionary functionality can be extracted and made standalone:

### Extractable Components
- **Dictionary Database**: SQLite-based dictionary storage and search
- **Image Search**: DuckDuckGo image search functionality  
- **Audio Processing**: Forvo audio downloads and management
- **Japanese Text Processing**: Language-specific text analysis

### Implementation Options
1. **Web Application**: Flask/FastAPI-based web interface
2. **Desktop Application**: Standalone PyQt/Tkinter application
3. **Command Line Tool**: CLI-based dictionary lookup

### Proof of Concept
A working demonstration is available in `standalone_dict_demo.py` which shows:
- Standalone dictionary database operations
- Image search without Qt dependencies
- HTML export functionality
- Command-line interface

```bash
# Run the standalone demo
python standalone_dict_demo.py hello
```

See `standalone_analysis.md` for detailed feasibility analysis and implementation approaches.

## Additional Resources

- [Usage Video Tutorial](https://www.youtube.com/watch?v=vrzBeiFlKjg)
- Original Migaku Dictionary Addon (predecessor)
- Anki addon development documentation
- `standalone_analysis.md` - Detailed analysis of making the addon standalone
- `standalone_dict_demo.py` - Working proof-of-concept implementation