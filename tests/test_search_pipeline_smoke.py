"""Smoke tests for SearchPipeline: end-to-end search and LLM result formatting.

These tests exercise the full search pipeline with a real SQLite database
but mock the Qt/Anki runtime (midict).  They do not require a display server
or a collection, so they can run as unit tests.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.create_empty_db import create_empty_database
from anki_dictionary.core.database import DictDB
from anki_dictionary.core.search_pipeline import SearchPipeline


@pytest.fixture
def db_and_midict(tmp_path):
    """Set up a real DictDB with test data and a mocked midict.

    Yields (db, midict) for use by tests.
    """
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
        patch(
            "anki_dictionary.core.database.get_frequency_dir",
            return_value=str(tmp_path),
        ),
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

        selected_group = {
            "dictionaries": [{"dict": "TestDict", "lang": "Japanese"}],
            "name": "TestGroup",
            "font": "",
            "customFont": False,
        }
        midict.dictInt.getSelectedDictGroup.return_value = selected_group

        yield db, midict, selected_group

        db.closeConnection()


class TestSearchPipelineSmoke:
    """Smoke tests that exercise the search pipeline end to end."""

    def test_dictionary_search_returns_html(self, db_and_midict):
        """SearchPipeline.getHTMLResult produces well-formed HTML for a real search."""
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)
        html, cleaned, single_tab = pipeline.getHTMLResult(
            "\u98df\u3079\u308b", selected_group
        )

        assert isinstance(html, str)
        assert len(html) > 0
        assert "\u98df\u3079\u308b" in html
        assert "To eat" in html
        assert "definitionBlock" in html
        assert "dictionaryTitleBlock" in html
        assert "taberu" in html
        assert "\u2605\u2605\u2605\u2605\u2605" in html
        assert isinstance(cleaned, str)
        assert cleaned == "\u98df\u3079\u308b"

    def test_llm_definition_formatting_includes_bullets(self, db_and_midict):
        """loadLLMResults handles bullet-point definitions without crashing.

        Regression test for the ``r\"\\u2022 \"`` raw-string bug that caused
        ``re.PatternError: bad escape \\u`` at runtime.
        """
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)

        result = {
            "dictName": "LLM",
            "idName": "llm-loader-smoke-1",
            "term": "taberu",
            "definition": "- eat food\n- consume a meal\n- have dinner",
            "starCount": "",
            "hskLevel": "",
            "altterm": "",
            "pronunciation": "",
        }

        pipeline.loadLLMResults(result)

        assert midict.eval.called, "eval() should be called to inject HTML"
        call_args = midict.eval.call_args[0][0]
        assert "definitionBlock" in call_args
        assert "\\u2022" in call_args, "Bullet character should appear in output"

    def test_format_single_entry_handles_bullets(self, db_and_midict):
        """formatSingleEntry processes bullet-point definitions without error."""
        db, midict, selected_group = db_and_midict

        pipeline = SearchPipeline(midict)

        result = {
            "term": "taberu",
            "definition": "- first item\n- second item\n- third item",
            "starCount": "",
            "hskLevel": "",
            "altterm": "",
            "pronunciation": "",
        }

        font = " "
        front_bracket = "("
        back_bracket = ")"
        html = pipeline.formatSingleEntry(
            result, "LLM", font, front_bracket, back_bracket
        )

        assert isinstance(html, str)
        assert len(html) > 0
        assert "\u2022" in html, "Bullet character should appear in output"
        assert "definitionBlock" in html
