"""
Tests for the toggleable styled-HTML export headers (``exportHeaderHtml``).

When the setting is off (the default) entry headers export as plain text,
exactly as before. When on, the exporter/send-to-field paths ship the
headword + badge markup with inline styles so frequency stars stay golden
inside Anki notes (whose card templates don't load the dictionary CSS).
"""

import json
from pathlib import Path

repo_root = Path(__file__).parent.parent
web_dir = repo_root / "web"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_config_json_defaults_export_header_html_to_false():
    config = json.loads((repo_root / "config.json").read_text(encoding="utf-8"))
    assert config.get("exportHeaderHtml", True) is False


def test_config_fallback_defaults_include_export_header_html():
    text = _read(repo_root / "src" / "anki_dictionary" / "utils" / "config.py")
    assert '"exportHeaderHtml": False' in text


def test_dictionary_injects_flag_and_reports_header_state():
    text = _read(repo_root / "src" / "anki_dictionary" / "core" / "dictionary.py")
    # Svelte shell + legacy fallback page both learn the flag at load…
    assert "window.exportHeaderHtml" in text
    assert "exportHeaderHtml = " in text
    # …and the unified header state carries it for live updates…
    assert (
        '"exportHeaderHtml": bool(self.config.get("exportHeaderHtml", False))' in text
    )
    # …with old configs (key missing) safely defaulting to off.
    assert 'self.config.get("exportHeaderHtml", False)' in text


def test_settings_ui_exposes_the_toggle():
    text = _read(web_dir / "src" / "settings" / "GeneralTab.svelte")
    assert "exportHeaderHtml" in text
    assert 'cfg.get("exportHeaderHtml", false)' in text


def test_export_header_helper_serializes_golden_stars():
    helper = web_dir / "src" / "lib" / "export-header.ts"
    assert helper.exists(), "web/src/lib/export-header.ts missing"
    text = _read(helper)
    assert "#e0a800" in text
    assert "headerHtmlForExport" in text
    assert "inlineHeaderBadges" in text
    assert "exportHeaderEnabled" in text


def test_svelte_export_paths_branch_on_the_flag():
    term_pron = _read(web_dir / "src" / "components" / "TermPronunciation.svelte")
    assert "headerHtmlForExport" in term_pron
    assert "ui.exportHeaderHtml" in term_pron
    compat = _read(web_dir / "src" / "lib" / "compat.ts")
    assert "exportHeaderEnabled()" in compat
    assert "inlineHeaderBadges" in compat


def test_bridge_and_store_carry_the_flag():
    bridge = _read(web_dir / "src" / "lib" / "bridge.ts")
    assert "exportHeaderHtml" in bridge
    assert "setExportHeaderHtml" in bridge
    store = _read(web_dir / "src" / "lib" / "tabs.svelte.ts")
    assert "exportHeaderHtml" in store
    assert "window.exportHeaderHtml" in store


def test_legacy_fallback_script_branches_on_the_flag():
    text = _read(repo_root / "assets" / "scripts" / "dictionary.js")
    assert "var exportHeaderHtml = false" in text
    assert "tpContExportHtml" in text
    assert "color:#e0a800" in text
    # Both Anki-bound paths (export + send-to-field) honor it; clipboard stays plain.
    assert (
        text.count("typeof exportHeaderHtml !== 'undefined' && exportHeaderHtml") == 2
    )
