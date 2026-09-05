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
    """The in-web chrome (search + history + group switcher) ships in the UI."""
    chrome = web_dir / "src" / "components" / "Chrome.svelte"
    if not chrome.exists():
        import pytest

        pytest.skip("web/src/components/Chrome.svelte missing — chrome not built")
    text = chrome.read_text(encoding="utf-8")
    # Shell id measured by resizer(), and the Python evaled callbacks.
    assert 'id="chromeBar"' in text
    assert "setGroups" in text
    assert "setSearchStatus" in text
    assert "getSearchHistory" in text
    # U2: search-source chip + clipboard-monitor pause pill.
    assert "setSearchSource" in text
    assert "sourcePill" in text
    assert "pauseBtn" in text
    # U3: the chrome dropdown reads the shared history store (the prune
    # command itself lives in Sidebar.svelte; covered by the sidebar test).
    assert "ui.history" in text
    assert "getSearchHistory" in text
    # Registers the Ctrl/Cmd+K global focus shortcut.
    assert '.toLowerCase() === "k"' in text


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
    # stay in sync over one callback.
    assert "setSearchHistory" in bridge_text
    assert "ui.history" in bridge_text

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
        # window callbacks Python evals (minified into assignment form)
        "setSearchHistory:",
        "setGroups=",
        "setSearchSource=",
        "setSearchStatus=",
        # CMD -> Python command prefixes (must match handleDictAction branches)
        "searchTerm:",
        "getSearchHistory:",
        "getGroups:",
        "setGroup:",
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
