"""Tests for the Phase-2 structured search document (Svelte shell payload).

``SearchPipeline.getStructuredResult`` emits a typed JSON document (sidebar +
blocks) instead of one HTML blob; ``addNewTab`` sends the document when the
Svelte shell is loaded and falls back to HTML for the legacy page.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anki_dictionary.core.database import DictDB
from anki_dictionary.core.search.pipeline import SearchPipeline
from scripts.create_empty_db import create_empty_database


@pytest.fixture
def db_and_midict(tmp_path):
    """Real DictDB + mocked midict (same setup as test_search_pipeline_smoke)."""
    config = {
        "frontBracket": "(",
        "backBracket": ")",
        "highlightTarget": True,
        "dictSearch": "10",
        "maxSearch": 50,
        "tooltips": True,
        "llm_enabled": False,
        "forvo_enabled": False,
        "maxWidth": 1500,
        "maxHeight": 400,
        "star_char": "\u2605",
        "star_thresholds": [1501, 5001, 15001, 30001, 60001],
        "show_stars": True,
        "show_rank": False,
        "show_hsk": True,
        "hsk_mode": "hsk3",
    }

    db_path = os.path.join(str(tmp_path), "dictionaries.sqlite")
    create_empty_database(db_path)

    with (
        patch("anki_dictionary.core.database.get_db_dir", return_value=str(tmp_path)),
        patch("anki_dictionary.core.database.get_addon_config", return_value=config),
    ):
        db = DictDB()
        db.addLanguages(["Japanese"])
        success, _, dict_name = db.addDict("TestDict", "Japanese", "[]")
        assert success, "TestDict should be added"

        lid = db.getLangId("Japanese")
        table_name = db.formatDictName(lid, dict_name)

        test_data = [
            (
                "\u98df\u3079\u308b",
                "\u305f\u3079\u308b",
                "taberu",
                "verb",
                "To eat<br>Definition line 2",
                "\u30ea\u30f3\u30b4\u3092\u98df\u3079\u308b",
                "audio.mp3",
                100,
                "\u2605\u2605\u2605\u2605\u2605",
            ),
            (
                "\u98f2\u3080",
                "\u306e\u3080",
                "nomu",
                "verb",
                "To drink",
                "\u6c34\u3092\u98f2\u3080",
                "audio2.mp3",
                500,
                "\u2605\u2605\u2605\u2605\u2605",
            ),
        ]

        db.importToDict(table_name, test_data)
        db.commitChanges()

        midict = MagicMock()
        midict.db = db
        midict.config = config
        midict.termHeaders = None
        midict.conjugations = {}
        midict.deinflect = False
        midict.radioCount = 0
        midict.customFontsLoaded = []
        midict.maxW = 1500
        midict.maxH = 400

        midict.sType = MagicMock()
        midict.sType.currentText.return_value = "Exact"

        midict.dictInt = MagicMock()
        midict.dictInt.theme_manager.is_dark = False
        midict.dictInt.iconpath = str(Path(__file__).parent.parent / "assets" / "icons")
        midict.dictInt.svelte_shell = True

        selected_group = {
            "dictionaries": [{"dict": "TestDict", "lang": "Japanese"}],
            "name": "TestGroup",
            "font": "",
            "customFont": False,
        }
        midict.dictInt.getSelectedDictGroup.return_value = selected_group

        yield db, midict, selected_group

        db.closeConnection()


class TestStructuredDocument:
    """The document schema the Svelte components consume."""

    def test_get_structured_result_shape(self, db_and_midict):
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)
        doc, cleaned, single_tab = pipeline.getStructuredResult(
            "\u98df\u3079\u308b", selected_group
        )

        assert cleaned == "\u98df\u3079\u308b"
        assert isinstance(single_tab, str)
        assert doc["font"] == " "
        assert doc["ankiIcon"].startswith("data:image/svg+xml;base64,")

        # Exact search for 食べる returns one entry -> title, termPron, definition.
        assert [b["type"] for b in doc["blocks"]] == [
            "dictionaryTitle",
            "termPronunciation",
            "definition",
        ]

        title = doc["blocks"][0]
        assert title["dataIndex"] == 0
        assert title["title"] == "TestDict"
        assert "overwriteSelect" in title["overwriteHtml"]
        assert "fieldSelect" in title["fieldHtml"]

        tp = doc["blocks"][1]
        assert tp["dataIndex"] == 999
        assert tp["cleanName"] == "TestDict"
        assert "taberu" in tp["headerHtml"]
        assert '<span class="term mainword"' in tp["headerHtml"]
        assert tp["stars"] == "\u2605\u2605\u2605\u2605\u2605"
        # Frequency 100 -> "[100]" rank badge; star tooltip has no source here.
        assert tp["rank"] == {"label": "[100]", "tip": ""}
        assert tp["starTip"] == "Frequency"
        assert tp["levels"] is None

        definition = doc["blocks"][2]
        assert "To eat" in definition["html"]
        # Definition html is mirrored onto the termPron block for copy/export.
        assert tp["definitionHtml"] == definition["html"]

    def test_sidebar_structure(self, db_and_midict):
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)
        doc, _, _ = pipeline.getStructuredResult("\u98df\u3079\u308b", selected_group)

        assert len(doc["sidebar"]) == 1
        side = doc["sidebar"][0]
        assert side["displayName"] == "TestDict"
        assert side["dataIndex"] == 0
        assert len(side["entries"]) == 1
        assert side["entries"][0]["dataIndex"] == 0
        assert '<span class="listTerm">' in side["entries"][0]["headerHtml"]

    def test_get_html_result_still_returns_legacy_html(self, db_and_midict):
        """The legacy HTML path must be byte-compatible for the fallback page."""
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)
        html, cleaned, single_tab = pipeline.getHTMLResult(
            "\u98df\u3079\u308b", selected_group
        )

        assert isinstance(html, str)
        assert "definitionSideBar" in html
        assert "resizeBar" in html
        assert "dictionaryTitleBlock" in html
        assert "termPronunciation" in html
        assert "definitionBlock" in html


class TestAddNewTabDualMode:
    """addNewTab sends a document (Svelte) or HTML (legacy) based on the shell."""

    def test_svelte_shell_sends_document(self, db_and_midict):
        db, midict, selected_group = db_and_midict
        midict.dictInt.svelte_shell = True

        pipeline = SearchPipeline(midict)
        pipeline.addNewTab("\u98df\u3079\u308b", selected_group)

        assert midict.eval.called
        call = midict.eval.call_args[0][0]
        assert call.startswith("addNewTab({"), call[:80]
        # The payload parses as a document, not an HTML blob.
        assert '"type": "dictionaryTitle"' in call
        assert "definitionSideBar" not in call[: call.find("addNewTab") + 30]
        # Extract the balanced first argument (the document object).
        payload = call[len("addNewTab(") :]
        depth = 0
        end = 0
        for i, ch in enumerate(payload):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        assert end > 0, "document payload not balanced"
        doc = json.loads(payload[:end])
        assert doc["sidebar"]
        assert doc["blocks"]

    def test_legacy_shell_sends_html(self, db_and_midict):
        db, midict, selected_group = db_and_midict
        midict.dictInt.svelte_shell = False

        pipeline = SearchPipeline(midict)
        pipeline.addNewTab("\u98df\u3079\u308b", selected_group)

        assert midict.eval.called
        call = midict.eval.call_args[0][0]
        assert call.startswith('addNewTab("<div'), call[:80]
        assert "definitionSideBar" in call
        assert "dictionaryTitleBlock" in call
