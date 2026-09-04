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
