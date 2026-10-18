"""Capture docs-site media headlessly from the real UI bundle.

Serves ``web/dist`` (preview shell built by ``build_pages.py`` + real search
documents from ``dump_docs.py``) and drives Chromium with Playwright: the
same Svelte shell the add-on loads inside Anki, wired to the mock bridge.
Produces PNG screenshots + WebM clips into ``site/media/raw/``.

Usage::

    uv run --with playwright python scripts/docs_media/capture.py
"""

from __future__ import annotations

import functools
import http.server
import json
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "web" / "dist"
RAW = REPO / "site" / "media" / "raw"

SHOT_VIEW = {"width": 1440, "height": 900}
VIDEO_VIEW = {"width": 1280, "height": 800}
TERM_MAIN = "电脑"
TERM_SECOND = "水"
TERM_TYPED = "你好"
THEME_SHOTS = ["light", "dark", "catppuccin_mocha", "gruvbox", "nord"]
THEME_VIDEO = ["catppuccin_mocha", "gruvbox", "nord", "light", "tokyo_night"]

SEARCH_INPUT = 'input[aria-label^="Search"]'
DEFS = ".definitionBlock"

SWAP_THEME_JS = """(css) => {
  const t = document.createElement("template");
  t.innerHTML = css;
  const s = t.content.firstElementChild;
  document.getElementById("customThemeCss").replaceWith(s);
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def start_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    for port in range(8940, 8970):
        handler = functools.partial(_Quiet, directory=str(DIST))
        try:
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, port
    raise RuntimeError("no free port for the capture server")


def search(page, term: str) -> None:
    page.evaluate("t => window.pycmd('searchTerm:' + t)", term)
    page.wait_for_selector(DEFS, timeout=15000)


REMOVE_BANNER = "document.getElementById('dev-mock-banner')?.remove()"


def open_preview(page, base_url: str, themes: dict[str, str], theme: str) -> None:
    page.goto(
        f"{base_url}/preview-dictionary.html?mock=1", wait_until="domcontentloaded"
    )
    page.wait_for_selector(SEARCH_INPUT, timeout=15000)
    page.evaluate(SWAP_THEME_JS, themes[theme])
    page.evaluate(REMOVE_BANNER)
    time.sleep(0.6)


def shot(page, name: str) -> None:
    path = RAW / f"{name}.png"
    page.screenshot(path=str(path))
    print(f"  shot {path.relative_to(REPO)} ({path.stat().st_size // 1024}KB)")


def save_video(page, name: str) -> None:
    video = page.video
    if video is None:
        return
    page.close()
    video.save_as(RAW / f"{name}.webm")
    print(f"  clip {name}.webm")


def do_shots(p: Playwright, base_url: str, themes: dict[str, str]) -> None:
    browser = p.chromium.launch()
    page = browser.new_page(viewport=SHOT_VIEW, device_scale_factor=2, locale="en-US")
    open_preview(page, base_url, themes, "tokyo_night")
    shot(page, "s01-welcome")

    for i, theme in enumerate(THEME_SHOTS):
        open_preview(page, base_url, themes, theme)
        search(page, TERM_MAIN)
        page.wait_for_timeout(900)
        shot(page, f"s{2 + i:02d}-search-{theme}")

    # Multi-tab: two terms side by side (tokyo_night, the default look).
    open_preview(page, base_url, themes, "tokyo_night")
    page.evaluate("window.pycmd('setTabMode:multi')")
    search(page, TERM_MAIN)
    search(page, TERM_SECOND)
    page.wait_for_timeout(700)
    shot(page, "s07-multitab")

    # Sidebar with scrollspy + recent searches.
    page.evaluate("window.openSidebar()")
    page.wait_for_timeout(400)
    shot(page, "s08-sidebar")

    # Settings: general tab + appearance gallery.
    page.goto(f"{base_url}/settings.html?mock=1", wait_until="domcontentloaded")
    page.wait_for_selector("text=Anki Dictionary Settings", timeout=15000)
    page.evaluate(REMOVE_BANNER)
    page.wait_for_timeout(800)
    shot(page, "s09-settings")
    page.click('button:has-text("Appearance")')
    page.wait_for_timeout(900)
    shot(page, "s10-settings-theme")
    page.click('button:has-text("Dictionaries")')
    page.wait_for_timeout(700)
    shot(page, "s11-settings-dicts")
    browser.close()


def do_videos(p: Playwright, base_url: str, themes: dict[str, str]) -> None:
    browser = p.chromium.launch()

    # v01: the core loop — type a word, Enter, definitions land.
    ctx = browser.new_context(
        viewport=VIDEO_VIEW,
        locale="en-US",
        record_video_dir=str(RAW / "tmp"),
        record_video_size=VIDEO_VIEW,
    )
    page = ctx.new_page()
    open_preview(page, base_url, themes, "tokyo_night")
    page.wait_for_timeout(500)
    page.click(SEARCH_INPUT)
    page.keyboard.type(TERM_TYPED, delay=180)
    page.keyboard.press("Enter")
    page.wait_for_selector(DEFS, timeout=15000)
    page.wait_for_timeout(1800)
    page.mouse.wheel(0, 320)
    page.wait_for_timeout(1200)
    save_video(page, "v01-search")
    ctx.close()

    # v02: live theme gallery over one rich result page.
    ctx = browser.new_context(
        viewport=VIDEO_VIEW,
        locale="en-US",
        record_video_dir=str(RAW / "tmp"),
        record_video_size=VIDEO_VIEW,
    )
    page = ctx.new_page()
    open_preview(page, base_url, themes, "tokyo_night")
    search(page, TERM_MAIN)
    page.wait_for_timeout(1000)
    for theme in THEME_VIDEO:
        page.evaluate(SWAP_THEME_JS, themes[theme])
        page.wait_for_timeout(1500)
    save_video(page, "v02-themes")
    ctx.close()

    # v03: multi-tab + sidebar browsing.
    ctx = browser.new_context(
        viewport=VIDEO_VIEW,
        locale="en-US",
        record_video_dir=str(RAW / "tmp"),
        record_video_size=VIDEO_VIEW,
    )
    page = ctx.new_page()
    open_preview(page, base_url, themes, "tokyo_night")
    page.evaluate("window.pycmd('setTabMode:multi')")
    search(page, TERM_MAIN)
    page.wait_for_timeout(900)
    search(page, TERM_SECOND)
    page.wait_for_timeout(900)
    page.evaluate("window.openSidebar()")
    page.wait_for_timeout(800)
    try:
        page.locator(".historyTerm").first.click(timeout=3000)
    except Exception:  # noqa: BLE001 - browsing the list is optional flourish
        page.mouse.wheel(0, 200)
    page.wait_for_timeout(1200)
    save_video(page, "v03-tabs-sidebar")
    ctx.close()

    browser.close()


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    themes: dict[str, str] = json.loads(
        (DIST / "preview" / "themes.json").read_text(encoding="utf-8")
    )
    if not (DIST / "preview-dictionary.html").exists():
        print("run build_pages.py + dump_docs.py first", file=sys.stderr)
        return 1
    srv, port = start_server()
    base_url = f"http://127.0.0.1:{port}"
    print(f"serving {DIST} at {base_url}")
    wanted = set(sys.argv[1:]) or {"shots", "videos"}
    try:
        with sync_playwright() as p:
            if "shots" in wanted:
                do_shots(p, base_url, themes)
            if "videos" in wanted:
                do_videos(p, base_url, themes)
    finally:
        srv.shutdown()
    import shutil

    shutil.rmtree(RAW / "tmp", ignore_errors=True)
    print("capture complete ->", RAW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
