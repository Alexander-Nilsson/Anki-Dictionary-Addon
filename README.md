
<h2 align="center">Anki Dictionary Add-on </h2>

<p align="center">
  <a href="https://ankiweb.net/shared/info/1973740182">
    <img src="https://img.shields.io/badge/AnkiWeb-1973740182-blue.svg" alt="AnkiWeb ID">
  </a>
  <a href="https://www.gnu.org/licenses/agpl-3.0.html" title="License: GNU AGPLv3">
    <img src="https://img.shields.io/badge/license-GNU%20AGPLv3-green.svg" alt="License: GNU AGPLv3">
  </a>
</p>

<p align="center">
  <img src="assets/demo/demo.avif" alt="Anki Dictionary Addon Demo" width="800">
</p>

## Core Features

The **Anki Dictionary Addon** is a high-performance lookup and card-creation tool designed for modern language learners.

  * **Fast Export to Anki:** Create rich, formatted flashcards instantly. Export definitions, example sentences, and frequency data directly to your cards without leaving Anki.
  * **AI-Powered Definitions:** Integrated **LLM API support** (OpenAI, Ollama, etc.) allows you to generate custom definitions and simplified explanations for complex terms.
  * **Integrated Image Search:** Quickly find and attach visual aids to your cards via built-in DuckDuckGo image search, ensuring your cards are highly memorable.
  * **Native Audio Integration:** Scraping support for **Forvo**, allowing you to find and attach high-quality native speaker pronunciations to your cards.
  * **Multi-Dictionary Support:** Aggregate results from multiple local dictionaries.



## Overview

This addon is the modern successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon), rebuilt for **Anki 25.09+** compatibility.

  - **Modern Architecture:** Completely reorganized codebase following Python best practices for better stability.
  - **Enhanced UX:** Improved styling and responsive interface design.
  - - **Theme Support:** Includes popular themes like Catppuccin and supports custom theming.

### Themes

<p align="center">
<img src="assets/demo/startscreen.avif" alt="Start Screen" width="400">
<img src="assets/demo/gruvbox.avif" alt="Gruvbox Retro Theme" width="400">
</p>
<p align="center">
<img src="assets/demo/mocha.avif" alt="Catppuccin Mocha Theme" width="400">
<img src="assets/demo/dark.avif" alt="Dark Theme" width="400">
</p>



## Table of Contents

  - [Status & Compatibility](#status)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Project Structure](#project-structure)
  - [Development](#development)
  - [Testing](#testing)
  - [License and Credits](#license-and-credits)



## Status

### Compatibility

  - **Operating Systems:** Fully tested on **macOS** and **Linux**
  - **Anki Version:** 25.09.2+



## Installation

### Option 1: AnkiWeb (Recommended)

The fastest way to install the addon and stay updated:

1.  Open Anki and go to **Tools** → **Add-ons**.
2.  Click **Get Add-ons...** and enter the code:
    > **`1973740182`**
3.  Restart Anki.

### Option 2: Install from Release File

If you need a specific version or prefer manual installation:

1.  Download the latest `.ankiaddon` file from the [Releases Page](https://github.com/Alexander-Nilsson/Anki-Dictionary-Addon/releases).
2.  Open Anki and go to **Tools** → **Add-ons**.
3.  **Drag and drop** the downloaded file onto the Add-ons window, or click **Install from file...** and select the `.ankiaddon` file.
4.  Restart Anki.

-----

### 💻 Manual/Development Installation

If you wish to contribute or run the latest source code:

1.  Clone the repository.
2.  Follow the [Development](#development) instructions to build and link the source to your Anki addons folder:
      - **macOS:** `~/Library/Application Support/Anki2/addons21/`
      - **Linux:** `~/.local/share/Anki2/addons21/`
      - **Windows:** `%APPDATA%\Anki2\addons21\`
-----

## Usage

For a visual guide on how to configure your dictionaries and export cards, refer to the following video:

[![Watch the video](https://img.youtube.com/vi/vrzBeiFlKjg/0.jpg)](https://www.youtube.com/watch?v=vrzBeiFlKjg)
-----

## Project Structure

```
src/anki_dictionary/     # Main package
├── core/                # Database and dictionary logic
├── ui/                  # PyQt6 interface components
├── integrations/        # LLM (AI) and Image search integrations
├── exporters/           # Anki card generation logic
└── web/                 # HTML/JS rendering components
tests/                   # Test suite
├── conftest.py          # Shared fixtures and qapp fixture
├── integration/         # Integration tests (real Anki + aqt runtime)
│   ├── conftest.py      # Headless anki_session + qapp fixtures
│   └── test_addon_loads.py
├── test_database.py     # DictDB unit tests
├── test_forvo.py        # Forvo parsing tests
├── test_llm.py          # LLM worker tests
├── test_themes.py       # Theme tests
└── test_addon_structure.py
```

-----

## Development

The addon follows modern Python development practices:

1.  **Setup:**

    ```bash
    git clone <repository-url>
    cd anki-dictionary-addon
    uv sync # Or: python dev.py install
    ```

2.  **Workflow:**

    ```bash
    python dev.py ci     # Run linting + tests
    python dev.py build  # Build for testing
    ```

### Testing

Tests use **pytest** with marker-based filtering for unit, integration, and network tests.

```bash
# Run all tests (skips integration and network by default)
uv run pytest tests/

# Run only fast unit tests (no network, no Anki runtime needed)
uv run pytest tests/ -m "not integration and not network"

# Run integration tests (requires real `anki` package installed)
uv run pytest tests/integration/

# Run network-dependent tests
uv run pytest tests/ -m "network"

# Full CI pipeline (lint + test)
python dev.py ci
```

**Test markers:**

| Marker        | Description                                      |
|---------------|--------------------------------------------------|
| `integration` | Tests against a real `anki.collection.Collection` |
| `network`     | Tests that make HTTP requests (Forvo, etc.)      |

**Conventions:**

- **Unit tests** (`tests/test_*.py`) use the installed `anki` and `aqt` packages directly (no module-level mocks). The shared conftest at `tests/conftest.py` only stubs the addon's root `__init__.py` entry point.
- **Integration tests** (`tests/integration/`) use a headless `anki.collection.Collection` fixture (no Qt GUI required for basic DB tests). Widget-level tests use the `qapp` fixture which sets `AA_ShareOpenGLContexts` before creating a shared `QApplication`. They auto-skip when `anki` is not installed.
- **Network tests** are marked `@pytest.mark.network` and are excluded from the default test run.

-----

## License and Credits

The **Anki Dictionary Addon** is a successor to the [Migaku Dictionary Addon](https://github.com/migaku-official/Migaku-Dictionary-Addon).

This project is **free and open-source software**. The code is released under the **GNU AGPLv3 license**. Please see the [LICENSE](https://www.gnu.org/licenses/agpl-3.0.html) file for details.

-----

*Feel free to contribute to the project or report issues via the GitHub Issue tracker.*
