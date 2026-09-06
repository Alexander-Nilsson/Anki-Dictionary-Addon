"""
Tests for the Svelte web UI (the dictionary shell rendered in AnkiWebView).

The web UI lives in ``web/`` and is compiled by Vite into a single
self-contained ``web/dist/dictionary.html`` (inlined JS + CSS, no ES modules)
that mirrors the injection contract of the legacy ``assets/templates`` assets:

- a ``<!-- FONT_SIZES -->`` marker (Python injects window.fefs/window.dbfs)
- an empty ``<style id="customThemeCss"></style>`` placeholder
- an empty ``<div id="welcomeBackground"></div>`` placeholder

Those placeholders must survive the build so ``MIDict._get_html_url_svelte``
can keep configuring the UI identically.
"""

import re
import tempfile
from pathlib import Path

repo_root = Path(__file__).parent.parent
web_dir = repo_root / "web"
built_html = web_dir / "dist" / "dictionary.html"


def test_package_json_defines_build_and_check_scripts():
    package = web_dir / "package.json"
    if not package.exists():
        import pytest

        pytest.skip("web/package.json missing — web UI not present")
    import json

    scripts = json.loads(package.read_text(encoding="utf-8"))["scripts"]
    assert "build" in scripts
    assert "check" in scripts


def test_svelte_sources_present():
    expected_sources = [
        web_dir / "src" / "main.ts",
        web_dir / "src" / "lib" / "bridge.ts",
        web_dir / "src" / "lib" / "tabs.svelte.ts",
        web_dir / "src" / "components" / "App.svelte",
        web_dir / "src" / "components" / "Chrome.svelte",
        web_dir / "src" / "components" / "CommandPalette.svelte",
    ]
    missing = [p for p in expected_sources if not p.exists()]
    assert not missing, f"Missing Svelte sources: {missing}"


def test_built_bundle_has_python_injection_markers():
    if not built_html.exists():
        import pytest

        pytest.skip(
            "web/dist/dictionary.html not built — run `cd web && npm run build`"
        )
    html = built_html.read_text(encoding="utf-8")

    # The markers Python's getHTMLURL replaces must be present.
    assert "<!-- FONT_SIZES -->" in html
    assert '<style id="customThemeCss"></style>' in html
    assert '<div id="welcomeBackground"></div>' in html


def test_built_bundle_is_self_contained_no_es_modules():
    if not built_html.exists():
        import pytest

        pytest.skip("web/dist/dictionary.html not built")
    html = built_html.read_text(encoding="utf-8")

    # No external asset references: everything must be inline.
    assert 'src="./assets/' not in html
    assert 'href="./assets/' not in html

    # The bundle must run as a plain (classic) script inside QtWebEngine:
    # no ES module script tags and no top-level import/export statements.
    assert '<script type="module"' not in html
    script_bodies = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html)
    assert len(script_bodies) >= 1
    for body in script_bodies:
        for line in body.splitlines():
            stripped = line.strip()
            assert not stripped.startswith(("import ", "export ")), (
                f"ESM statement leaked into classic script: {stripped[:60]}"
            )


def test_built_bundle_is_a_single_document():
    """The bundle must not contain an embedded second copy of index.html.

    Regression: inline.mjs used a *string* replacement to splice the bundle
    after the welcome placeholder. ``String.replace`` interprets ``$`` escape
    sequences inside the bundle's own JS (e.g. the regex-escape idiom
    ``'\\\\$&'`` and backtick-prefixed ``$\\``` patterns), substituting the
    matched substring / whole document prefix into the script and splicing an
    unescaped ``</script>`` into it — truncating the script and preventing the
    Svelte app from mounting.
    """
    if not built_html.exists():
        import pytest

        pytest.skip("web/dist/dictionary.html not built")
    html = built_html.read_text(encoding="utf-8")

    # An embedded document copy would add a second <!DOCTYPE> / <html>.
    assert html.count("<!DOCTYPE") == 1
    assert html.count("<html lang=") == 1


def test_built_bundle_script_runs_to_mount():
    """The inlined bundle script must survive to the app-mount code.

    If the inliner corrupts or truncates the script (the ``$``-substitution
    regression above), the mount tail and bridge globals disappear.
    """
    if not built_html.exists():
        import pytest

        pytest.skip("web/dist/dictionary.html not built")
    html = built_html.read_text(encoding="utf-8")

    script_bodies = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html)
    mount_code = "Svelte mount target #app not found"
    bundle = next((b for b in script_bodies if mount_code in b), None)
    assert bundle, (
        "inlined bundle is truncated — the app-mount code is missing "
        "(an unescaped `</script>` likely cut the script short)"
    )

    # The script element must not itself contain a terminator sequence.
    assert "</script" not in bundle and "<script" not in bundle

    # The raw Vite bundle must be embedded verbatim (no string-replace
    # `$`-substitution corruption).
    js_files = sorted((web_dir / "dist" / "assets").glob("index-*.js"))
    if js_files:
        raw = js_files[0].read_text(encoding="utf-8")
        assert raw in bundle


def test_chrome_component_source_present():
    """The S1 minimal chrome (search + scope + overflow) ships in the UI."""
    chrome = web_dir / "src" / "components" / "Chrome.svelte"
    if not chrome.exists():
        import pytest

        pytest.skip("web/src/components/Chrome.svelte missing — chrome not built")
    text = chrome.read_text(encoding="utf-8")
    # Shell id measured by resizer(), and the Python evaled callbacks.
    assert 'id="chromeBar"' in text
    # Header state lives in the shared store; the bridge writes it.
    assert "setHeaderState" in text or "ui.group" in text
    assert "getSearchHistory" in text
    assert "getHeaderState" in text
    # S1: scope (group + mode joined) + overflow menu + contextual pills.
    assert "scopeWrap" in text
    assert "chromeMenu" in text
    assert "sourcePill" in text
    assert "showPalette" in text
    # Every old Qt toolbar capability is reachable (inline or via menu/palette).
    assert "setSearchMode" in text
    assert "setDeinflect" in text
    assert "setTabMode" in text
    assert "openHistory" in text
    assert "openTheme" in text
    assert "toggleSidebar" in text
    assert "scaleFont" in text
    # U3: the chrome dropdown reads the shared history store (the prune
    # command itself lives in Sidebar.svelte; covered by the sidebar test).
    assert "ui.history" in text
    assert "getSearchHistory" in text
    # S3: Ctrl/Cmd+K opens the palette; `/` focuses search.
    assert '.toLowerCase() === "k"' in text


def test_palette_component_source_present():
    """The S3 command palette ships alongside the minimal chrome."""
    palette = web_dir / "src" / "components" / "CommandPalette.svelte"
    if not palette.exists():
        import pytest

        pytest.skip("CommandPalette.svelte missing — S3 palette not built")
    text = palette.read_text(encoding="utf-8")
    assert "showPalette" in text
    assert "searchTerm" in text or "CMD.searchTerm" in text
    assert "palList" in text
    assert "ui.groups" in text
    assert "ui.searchModes" in text


def test_bridge_and_sidebar_sources_present():
    """U3/U4/U5 sources: shared history, sidebar prune, keymap, suggestions."""
    bridge = web_dir / "src" / "lib" / "bridge.ts"
    sidebar = web_dir / "src" / "components" / "Sidebar.svelte"
    keymap = web_dir / "src" / "components" / "KeymapOverlay.svelte"
    keymap_lib = web_dir / "src" / "lib" / "keymap.ts"
    noresults = web_dir / "src" / "components" / "NoResults.svelte"
    for p in (bridge, sidebar, keymap, keymap_lib, noresults):
        if not p.exists():
            import pytest

            pytest.skip(f"{p.name} missing — UI slice sources not present")

    bridge_text = bridge.read_text(encoding="utf-8")
    # setSearchHistory was promoted to the shared bridge so sidebar + chrome
    # stay in sync over one callback. Header state (S1) is centralised there
    # too so Chrome + palette share one source.
    assert "setSearchHistory" in bridge_text
    assert "setHeaderState" in bridge_text
    assert "ui.history" in bridge_text
    assert "ui.groups" in bridge_text
    store = web_dir / "src" / "lib" / "tabs.svelte.ts"
    assert "showPalette" in store.read_text(encoding="utf-8")

    sidebar_text = sidebar.read_text(encoding="utf-8")
    assert "Recent searches" in sidebar_text
    assert "deleteSearchHistory" in sidebar_text
    assert "historyPrune" in sidebar_text

    keymap_text = keymap.read_text(encoding="utf-8")
    assert "Keyboard shortcuts" in keymap_text
    assert "showKeymap" in keymap_text

    keymap_lib_text = keymap_lib.read_text(encoding="utf-8")
    assert '".ankiExportButton"' in keymap_lib_text
    assert '".clipper"' in keymap_lib_text
    assert "moveDict" in keymap_lib_text

    noresults_text = noresults.read_text(encoding="utf-8")
    assert "Did you mean" in noresults_text
    assert "suggestion-chip" in noresults_text
    assert "deinflect-hint" in noresults_text


def test_built_bundle_has_chrome_and_bridge_commands():
    """The compiled bundle must still carry the chrome + new bridge commands.

    Guards against the command-string contract between ``pycmd.ts`` and
    ``MIDict.handleDictAction`` drifting apart (each ``CMDtoCommand`` prefix
    has a matching Python branch).
    """
    if not built_html.exists():
        import pytest

        pytest.skip("web/dist/dictionary.html not built")
    html = built_html.read_text(encoding="utf-8")
    for marker in (
        "chromeBar",
        "scopeWrap",
        "chromeMenu",
        "palList",
        # window callbacks Python evals (object-literal form in bridge.ts)
        "setSearchHistory:",
        "setGroups:",
        "setHeaderState:",
        "setSearchModes:",
        "setSearchSource:",
        "setSearchStatus:",
        # CMD -> Python command prefixes (must match handleDictAction branches)
        "searchTerm:",
        "getSearchHistory:",
        "getGroups:",
        "setGroup:",
        "getHeaderState:",
        "setSearchMode:",
        "setDeinflect:",
        "setTabMode:",
        "openHistory",
        "openTheme",
        "setClipboardPaused:",
        "requestSearchStatus:",
        "saveSession:",
        "deleteSearchHistory:",
        "Search the dictionary",
        # U3/U4/U5 user-facing strings survive minification
        "Recent searches",
        "Keyboard shortcuts",
        "Did you mean",
    ):
        assert marker in html, f"bundle lost chrome/bridge marker: {marker}"


def test_group_names_skips_disabled_separator_rows():
    """``_group_names`` must read enablement from the combo's model.

    ``QComboBox`` has no ``itemEnabled()``; an earlier version called it and
    every ``pushHeaderState`` raised ``AttributeError`` inside a broad
    ``except``, so the unified header silently never received its groups,
    modes or toggle states.

    Run in a subprocess: other test modules in this suite install stub
    ``anki``/``aqt`` modules in ``sys.modules``, and importing the real
    dictionary module afterwards fails depending on collection order.
    """
    import os
    import subprocess
    import sys

    import pytest

    script = """
import sys
sys.path.insert(0, {src!r})

from PyQt6.QtWidgets import QApplication, QComboBox

from anki_dictionary.core.dictionary import DictInterface

app = QApplication.instance() or QApplication([])

combo = QComboBox()
combo.addItems(["Japanese", "Chinese"])
combo.addItem("\u2500" * 6)
combo.model().item(combo.count() - 1).setEnabled(False)
combo.addItems(["All", "Images"])

stub = type("Stub", (), {{"dictGroups": combo}})()
assert DictInterface._group_names(stub) == ["Japanese", "Chinese", "All", "Images"]
print("OK")
""".format(src=str(repo_root / "src"))

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0 and "ModuleNotFoundError" in proc.stderr:
        pytest.skip(f"Qt/anki not importable in this environment: {proc.stderr[-200:]}")
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_inlined_bundles_do_not_touch_the_qt_global():
    """The inlined page bundle must not declare anything at global scope.

    Each page is inlined into a plain ``<script>`` — a classic script, not
    ``type="module"`` — so every top-level declaration becomes a property of
    ``window``. Built with ``format: "es"``, the minifier's ``function qt``
    landed on ``window.qt``, clobbering the object QtWebEngine injects to
    carry ``qt.webChannelTransport``. Anki's bridge script then found no
    transport, its QWebChannel handshake never completed, and
    ``window.pycmd`` stayed undefined: the UI rendered and still received
    results (Python -> JS ``eval`` does not use the channel) while every
    button, menu entry and search silently did nothing.

    Rather than blocklisting identifiers a future minifier run might change,
    this evaluates the real bundle with a sentinel ``qt`` in place and
    checks it survives. Function declarations are hoisted when the script is
    entered, so a leak shows up even though the bundle then throws on the
    stub DOM.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    for page in (built_html, web_dir / "dist" / "settings.html"):
        if not page.exists():
            pytest.skip(f"{page.name} not built — run `npm run build` in web/")

        html = page.read_text(encoding="utf-8")
        bundle = html[
            html.rindex("<script>") + len("<script>") : html.rindex("</script>")
        ]

        harness = """
const vm = require("vm");
const bundle = require("fs").readFileSync(process.argv[2], "utf8");
const ctx = { qt: { webChannelTransport: "SENTINEL" }, console };
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);
try { vm.runInContext(bundle, ctx); } catch (e) { /* stub DOM throws; fine */ }
const t = ctx.qt && ctx.qt.webChannelTransport;
console.log(JSON.stringify({ transport: t === undefined ? null : t }));
"""
        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "bundle.js"
            bundle_path.write_text(bundle, encoding="utf-8")
            harness_path = Path(tmp) / "harness.js"
            harness_path.write_text(harness, encoding="utf-8")
            proc = subprocess.run(
                [node, str(harness_path), str(bundle_path)],
                capture_output=True,
                text=True,
            )

        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        assert result["transport"] == "SENTINEL", (
            f"{page.name}: the bundle overwrote the global `qt`, which carries "
            "qt.webChannelTransport — Anki's pycmd bridge will never come up"
        )
