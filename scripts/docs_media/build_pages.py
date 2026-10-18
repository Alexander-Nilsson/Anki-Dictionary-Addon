"""Build the themed preview shell used for docs-site media capture.

Reproduces the exact string substitutions the add-on performs at runtime
(see ``DictInterface._get_html_url_svelte``): font-size bootstrap, active
theme CSS, and the welcome-screen HTML. The output is served from
``web/dist`` and driven headlessly by ``capture.py`` with ``?mock=1``; the
mock bridge (web/src/dev-mock.ts) then replays the real search documents
produced by ``dump_docs.py``.

Usage::

    uv run python scripts/docs_media/build_pages.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import types as _types

_init_stub = _types.ModuleType("__init__")
_init_stub.get_addon_state = MagicMock(return_value=MagicMock(config={}))
sys.modules["__init__"] = _init_stub

import aqt

aqt.mw = MagicMock()

from anki_dictionary.ui import theme_controller
from anki_dictionary.ui.themes import ThemeManager

DIST = REPO / "web" / "dist"
BASE_THEME = "tokyo_night"
# Themes previewed for the site gallery (must exist in themes.json/defaults).
GALLERY_THEMES = [
    "light",
    "dark",
    "catppuccin_mocha",
    "catppuccin_latte",
    "nord",
    "gruvbox",
    "tokyo_night",
]


def main() -> int:
    html = (DIST / "dictionary.html").read_text(encoding="utf-8")

    # Same bootstrap the add-on injects (mac=false: Linux/Windows capture).
    font_size_init = (
        "<script>window.fefs = 12; window.dbfs = 22; window.sidebarWidth = 260;"
        " window.isMac = false; window.exportHeaderHtml = false;</script>"
    )
    html = html.replace("<!-- FONT_SIZES -->", font_size_init)

    # Welcome screen content, exactly as the add-on serves it.
    from anki_dictionary.ui.main_window import getWelcomeScreen

    welcome = getWelcomeScreen()
    html = html.replace(
        '<div id="welcomeBackground"></div>',
        f'<div id="welcomeBackground">{welcome}</div>',
    )

    manager = ThemeManager(str(REPO))
    themes_css: dict[str, str] = {}
    for name in GALLERY_THEMES:
        if name not in manager.themes:
            print(f"  skip unknown theme {name}")
            continue
        themes_css[name] = theme_controller.generate_html_css(
            vars(manager.themes[name])
        )

    # Bake the base theme into the preview page.
    page = html.replace('<style id="customThemeCss"></style>', themes_css[BASE_THEME])
    assert '<style id="customThemeCss">' in page, "theme injection failed"
    (DIST / "preview-dictionary.html").write_text(page, encoding="utf-8")

    out = DIST / "preview"
    out.mkdir(exist_ok=True)
    (out / "themes.json").write_text(
        json.dumps(themes_css, ensure_ascii=False), encoding="utf-8"
    )

    print("preview-dictionary.html + preview/themes.json written")
    print(f"themes: {list(themes_css)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
