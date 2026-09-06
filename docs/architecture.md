# Architecture

## Project Structure

```
src/anki_dictionary/
├── core/
│   ├── card_handler.py      # CardHandler — card content generation from dictionary results
│   ├── clip_thread.py       # ClipThread — background clipboard monitoring
│   ├── database.py          # DictDB — SQLite wrapper for dictionary lookups
│   ├── dictionary.py        # DictInterface — main dictionary UI orchestrator
│   ├── hooks.py             # Anki addon hook registration
│   └── search_pipeline.py   # SearchPipeline — multi-source lookup orchestration
├── ui/
│   ├── main_window.py       # Main window, hotkey management
│   ├── themes.py            # ThemeManager — dynamic theming
│   ├── dialogs/
│   │   ├── dict_importer_widget.py
│   │   ├── dict_import.py
│   │   ├── dictionary_manager.py
│   │   ├── language_manager_widget.py
│   │   ├── theme_editor.py
│   │   ├── tree_manager_widget.py
│   │   └── wizard.py
│   └── settings/
│       ├── settings_bridge.py  # AnkiWebView hosting the Svelte settings page
│       └── settings_gui.py     # Thin Qt window + native flows (dialogs/installers)
├── integrations/
│   ├── forvo.py             # Forvo audio scraping
│   ├── image_search.py      # DuckDuckGo image search
│   └── llm.py               # LLM (AI) definition generation
├── exporters/
│   ├── batch_processor.py   # BatchProcessor — multi-card batch export
│   ├── card_exporter.py     # CardExporter — single-card export
│   ├── field_mapper.py      # FieldMapper — template field mapping
│   ├── html_cleaner.py      # HTMLCleaner — sanitize/clean HTML
│   └── media_handler.py     # MediaHandler — audio/image media ops
├── utils/
│   ├── common.py, config.py, constants.py, paths.py
│   ├── history.py, logger.py
└── web/
    ├── config.py, icons.py, installer.py, windows.py
web/                          # Svelte 5 + Vite UI (rendered inside AnkiWebView)
├── package.json              # vite build → dist/index.html, then inline.mjs → dist/dictionary.html
├── vite.config.ts, svelte.config.js, tsconfig.json
├── index.html                # Shell with Python-injection placeholders (FONT_SIZES, etc.)
├── scripts/
│   ├── inline.mjs            # Post-build: inline JS+CSS into self-contained dictionary.html
│   └── extract-css.mjs       # One-time migration helper (legacy CSS → src/legacy.css)
└── src/
    ├── app.css               # legacy.css + Svelte shell tweaks
    ├── main.ts               # Mounts App; wires bridges
    ├── lib/
    │   ├── tabs.svelte.ts    # Reactive shell store (tabs, sidebar, fonts) — Svelte 5 runes
    │   ├── bridge.ts         # Python→JS globals (addNewTab, loadImageHtml, ...)
    │   ├── compat.ts         # Globals used by Python-generated HTML (ankiExport, clipText, ...)
    │   ├── dom.ts, pycmd.ts, types.ts
    └── components/
        ├── App.svelte, TabBar.svelte, WelcomeScreen.svelte, TabContent.svelte
assets/
├── templates/            # dictionary.html (legacy fallback), guide.html, welcome.html, etc.
├── styles/               # guide.css
├── scripts/              # dictionary.js (legacy fallback), insertHTML.js
├── web/                  # Built Svelte bundle (dist/dictionary.html) — populated by build.py
└── icons/                # 30 SVG icons (day/night variants)
tests/
├── conftest.py           # Shared fixtures (init stub only, no aqt/anki mocks)
├── integration/          # Real Anki + aqt runtime tests
│   ├── conftest.py       # anki_session + qapp (session-scoped QApplication) fixtures
│   └── test_addon_loads.py  # Import, symbol resolution, DictInterface instantiation
├── test_addon_structure.py, test_all_dictionaries.py
├── test_card_exporter.py, test_config.py
├── test_database.py, test_dictionary_index.py
├── test_forvo.py, test_forvo_integration.py
├── test_image_search.py
├── test_llm.py, test_settings.py, test_themes.py
scripts/                  # create_empty_db.py, create_default_themes.py, release.py
vendor/                   # Bundled deps (pynput, bs4) — created during build
user_files/               # db/, dictionaries/, themes/, fonts/, media/
```

## Architecture Notes

- **DictInterface** (`core/dictionary.py`) is the main orchestrator; renders results in `AnkiWebView`
- **Svelte UI (Phase 1):** The dictionary shell — tab bar, welcome screen, sidebar state, font scaling — is now a Svelte 5 app (`web/`) compiled by Vite into one self-contained `dictionary.html`. `MIDict.getHTMLURL` prefers the built bundle (`web/dist/dictionary.html` in a checkout, `assets/web/dictionary.html` packaged) and falls back to the legacy `assets/templates/dictionary.html` + `dictionary.js` when no build exists. Tab *content* is still Python-generated HTML injected through the `{@html}` boundary; the Svelte shell re-exposes the exact bridge API (`addNewTab`, `loadImageHtml`, `appendNewImages`, `addCustomFont`, `openSidebar`, `scaleFont`) plus content-level globals (`ankiExport`, `clipText`, ...) so the addon behaves identically. Later phases convert content to structured data + Svelte components.
- **Bridge contract:** Python → JS goes through `AnkiWebView.eval(...)` into `window.*` globals installed by `web/src/lib/bridge.ts`; JS → Python goes through `pycmd(...)` (AnkiWebView bridge) handled by `MIDict.handleDictAction`.
- **ClipThread** monitors clipboard for word changes on a background thread
- **DictDB** (`core/database.py`) abstracts SQLite schema differences across dictionary types
- **Themes** are JSON-based; active theme stored in `user_files/themes/active.json`
- **LLM**, **image search**, and **Forvo** are async; use background threads to avoid UI freezes
- **Vendor strategy:** Only `pynput` and `beautifulsoup4` are bundled; rely on Anki's bundled PyQt6, requests, Pillow
- **Platform checks:** Use `is_mac()`, `is_win()`, `is_lin()` from `anki.utils`
- **Build:** `build.py` copies `src/`, `assets/`, `__init__.py`, `config.json`; vendors deps; generates manifest; builds the Svelte UI with `npm ci && npm run build` (skips gracefully if npm is missing)
