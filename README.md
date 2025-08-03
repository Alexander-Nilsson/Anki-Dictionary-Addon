<h2 align="center">Anki Dictionary Addon </h2>
<p align="center">
  <a href="https://www.gnu.org/licenses/agpl-3.0.html" title="License: GNU AGPLv3">
    <img src="https://img.shields.io/badge/license-GNU%20AGPLv3-green.svg" alt="License: GNU AGPLv3">
  </a>
</p>

> **Note:** This project has been completely reorganized to follow Python best practices and modern project structure. See [REORGANIZATION_GUIDE.md](docs/REORGANIZATION_GUIDE.md) for details.

---

## 📖 Overview

The **Anki Dictionary Addon** is a successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon). It aims to:

- Port the original addon to support newer Anki versions.
- Fix existing bugs and improve stability.
- Introduce new features and enhancements.
- Modernize the codebase with proper project structure.

With this addon, users can:

- Look up word definitions, frequency data, and audio pronunciations.
- Export this information to Anki cards in real-time.
- Use the dictionary in standalone mode without Anki.

---

## 🏗️ Project Structure

The addon has been completely reorganized with a modular architecture:

```
src/anki_dictionary/     # Main package
├── core/               # Core functionality (database, dictionary interface)
├── ui/                 # User interface components
├── utils/              # Utility modules
├── integrations/       # External service integrations
├── exporters/          # Export functionality
└── web/                # Web-related components

assets/                  # Asset files (templates, styles, scripts, icons)
standalone/              # Standalone launcher components
docs/                   # Documentation
```

See [docs/REORGANIZATION_GUIDE.md](docs/REORGANIZATION_GUIDE.md) for a complete overview of the new structure.

---

## 📋 Table of Contents

- [Status](#status)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Building](#building)
- [Documentation](#documentation)
- [License and Credits](#license-and-credits)

---

## 🚧 Status

- **Forvo Integration:** Currently non-functional. Attempting to use it may cause application crashes.
- **Image Search:** Uses DuckDuckGo for image search functionality.
- **Platform Compatibility:** Tested only on **Linux**.
- **Anki Version Compatibility:** Confirmed working with Anki version **24.11**.

---

## 💾 Installation

1. **Install Anki:** Ensure you have the latest supported version of Anki installed. [Download Anki](https://apps.ankiweb.net/)
2. **Download the Addon:**
   - Clone or download this repository.
   - Unzip the contents to your Anki addons folder, typically located at:
     - **Linux:** `~/.local/share/Anki2/addons21/`
     - **Windows:** `%APPDATA%\Anki2\addons21\`
     - **macOS:** `~/Library/Application Support/Anki2/addons21/`

---

## ▶️ Usage

For a visual guide on how to use the addon, refer to the following video:

[![Anki Dictionary Addon Usage](https://img.youtube.com/vi/vrzBeiFlKjg/0.jpg)](https://www.youtube.com/watch?v=vrzBeiFlKjg)

---

## 🔧 Development

The addon follows modern Python development practices with a clean, modular structure:

1. **Development Setup:**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd anki-dictionary-addon
   
   # Install dependencies (using uv for fast package management)
   uv sync
   
   # Or use pip if you prefer
   pip install -e .
   ```

2. **Project Structure:**
   - `src/anki_dictionary/` - Main package with all source code
   - `assets/` - Templates, styles, scripts, and icons
   - `standalone/` - Standalone launcher components
   - `docs/` - Documentation and guides
   - `tests/` - Test suite (to be expanded)

3. **Development Workflow:**
   ```bash
   # Test the package structure
   python test_structure.py
   
   # Run standalone mode for testing
   python launch_dictionary.py
   
   # Run with specific Python environment
   uv run python launch_dictionary.py
   ```

4. **Code Organization:**
   - Follow the package structure for new features
   - Keep related functionality grouped together
   - Use absolute imports within the package
   - Document new functions and classes

See [docs/REORGANIZATION_GUIDE.md](docs/REORGANIZATION_GUIDE.md) for detailed information about the project structure.

---

## 📦 Building

The addon includes a comprehensive build system for creating distribution packages:

```bash
# Build Anki addon package (.ankiaddon)
python build.py package

# Build standalone distribution
python build.py standalone

# Build everything (addon + standalone)
python build.py all

# Clean build artifacts
python build.py clean
```

**Build Outputs:**
- `build/anki_dictionary_addon/` - Anki addon files
- `build/anki_dictionary_addon_v{version}.ankiaddon` - Installable Anki package
- `build/standalone/` - Standalone version for non-Anki use

**Package Contents:**
- All source code in `src/anki_dictionary/`
- Required assets and templates
- Configuration files
- Vendor dependencies

---

## 📚 Documentation

*Documentation is currently under development.* Future updates will include detailed guides on:

- Configuring dictionaries.
- Customizing export templates.
- Utilizing advanced features.

---

## 📝 License and Credits

The **Anki Dictionary Addon** is a successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon).

This project is **free and open-source software**. The code that runs within Anki is released under the **GNU AGPLv3 license**, extended by additional terms. For more information, please see the [LICENSE](https://www.gnu.org/licenses/agpl-3.0.html) file included with this program.

This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**.

---

*Feel free to contribute to the project or report issues. Your feedback is invaluable!*
