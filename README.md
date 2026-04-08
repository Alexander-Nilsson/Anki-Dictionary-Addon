<h2 align="center">Anki Dictionary Addon </h2>
<p align="center">
  <a href="https://www.gnu.org/licenses/agpl-3.0.html" title="License: GNU AGPLv3">
    <img src="https://img.shields.io/badge/license-GNU%20AGPLv3-green.svg" alt="License: GNU AGPLv3">
  </a>
</p>

> **Note:** This project has been completely reorganized to follow Python best practices and modern project structure.

---

## 📖 Overview

The **Anki Dictionary Addon** is a modern successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon), updated for **Anki 25.09** compatibility. This project aims to:

- **Support Latest Anki:** Updated to work seamlessly with Anki version ⁨25.09.2.
- **Enhanced User Experience:** Improved styling and interface design for better usability.
- **Modern Architecture:** Completely reorganized codebase following Python best practices.
- **Reliable Services:** Migrated to DuckDuckGo for image search, ensuring better privacy and reliability.
- **Bug Fixes:** Resolved stability issues and improved overall performance.

### Key Features

- Look up word definitions, frequency data, and pronunciations across multiple languages.
- Export dictionary information to Anki cards in real-time with improved formatting.
- Enhanced image search functionality using DuckDuckGo.
- Modern, responsive user interface with better visual design.

---

## Project Structure

The addon follows a modular architecture. Source files are located in `src/`, while external dependencies and user data are managed by the build system.

```
src/anki_dictionary/     # Main package
├── core/               # Core functionality (database, dictionary interface)
├── ui/                 # User interface components
├── utils/              # Utility modules
├── integrations/       # External service integrations
├── exporters/          # Export functionality
└── web/                # Web-related components

assets/                  # Asset files (templates, styles, scripts, icons)
scripts/                # Build and maintenance scripts
tests/                  # Test suite
```

**Note:** The `vendor/` and `user_files/` directories are no longer tracked in version control. They are automatically created and populated during the build process.

---

## Table of Contents

- [Status](#status)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Building](#building)
- [Documentation](#documentation)
- [License and Credits](#license-and-credits)

---

## Status

### Key Features

- **Multi-Dictionary Search:** Look up word definitions, frequency data, and pronunciations across multiple local and online sources.
- **AI Definitions:** Generate context-aware definitions using integrated LLM support.
- **Image Search:** Privacy-respecting image search using DuckDuckGo with dynamic loading.
- **Anki Export:** Real-time export of dictionary data, images, and audio directly to Anki cards.
- **Modern UI:** Responsive, themeable interface built with PyQt6 and optimized for high-DPI displays.

### Compatibility

- **Platform Compatibility:** Tested on **Linux**. Initial support for macOS and Windows via cross-platform library adjustments.
- **Anki Version Compatibility:** Optimized for Anki version **25.07**+.

---

## Installation

1. **Install Anki:** Ensure you have the latest supported version of Anki installed. [Download Anki](https://apps.ankiweb.net/)
2. **Download the Addon:**
   - Clone or download this repository.
   - Unzip the contents to your Anki addons folder, typically located at:
     - **Linux:** `~/.local/share/Anki2/addons21/`
     - **Windows:** `%APPDATA%\Anki2\addons21\`
     - **macOS:** `~/Library/Application Support/Anki2/addons21/`

---

## Usage

For a visual guide on how to use the addon, refer to the following video:

[![Anki Dictionary Addon Usage](https://img.youtube.com/vi/vrzBeiFlKjg/0.jpg)](https://www.youtube.com/watch?v=vrzBeiFlKjg)

---

## Development

The addon follows modern Python development practices with a clean, modular structure:

1. **Development Setup:**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd anki-dictionary-addon
   
   # Install development dependencies (using uv)
   uv sync
   
   # Or use the development helper
   python dev.py install
   ```

2. **Development Workflow:**
   ```bash
   # Run CI checks (linting + tests)
   python dev.py ci
   
   # Build the addon for testing
   python dev.py build
   
   # Format code
   python dev.py format
   ```

---

## Building

The addon includes an automated build system that handles dependency bundling and environment setup:

```bash
# Build everything (addon + .ankiaddon package)
python dev.py build

# Clean build artifacts
python dev.py clean
```

**Build Process Highlights:**
- **Dependency Bundling:** Automatically installs and bundles required libraries (e.g., `pynput`) into the `vendor/` directory.
- **Environment Setup:** Creates the necessary `user_files/` structure, including default themes and an empty database.
- **Packaging:** Generates a ready-to-install `.ankiaddon` file in the `build/` directory.

---

## License and Credits

The **Anki Dictionary Addon** is a successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon).

This project is **free and open-source software**. The code that runs within Anki is released under the **GNU AGPLv3 license**, extended by additional terms. For more information, please see the [LICENSE](https://www.gnu.org/licenses/agpl-3.0.html) file included with this program.

This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**.

---

*Feel free to contribute to the project or report issues. Your feedback is invaluable!*
