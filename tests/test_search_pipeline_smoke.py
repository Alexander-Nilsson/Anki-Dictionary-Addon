"""Smoke tests for SearchPipeline: end-to-end search and LLM result formatting.

These tests exercise the full search pipeline with a real SQLite database
but mock the Qt/Anki runtime (midict).  They do not require a display server
or a collection, so they can run as unit tests.
"""

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


class TestCustomFontServing:
    """The dictionary shell is served over http, so fonts need a served URL.

    An ``@font-face`` whose ``src`` points at the filesystem cannot load from
    an http origin, so a picked font is staged into ``user_files/fonts`` and
    referenced through Anki's ``/_addons/`` route.
    """

    def _pipeline(self, tmp_path):
        midict = MagicMock()
        midict.addon_root = str(tmp_path / "Anki-Dictionary")
        os.makedirs(midict.addon_root, exist_ok=True)
        return SearchPipeline(midict), midict

    def test_family_name_is_basename_without_extension(self):
        from anki_dictionary.core.search.renderer import custom_font_family

        assert custom_font_family("/home/u/.fonts/Takao Mincho.ttf") == "Takao Mincho"

    def test_group_style_quotes_the_family(self):
        from anki_dictionary.core.search.renderer import get_font_family

        style = get_font_family({"font": "/home/u/My.Font.ttf", "customFont": True})
        assert "font-family:'My.Font'" in style

    def test_absolute_path_is_copied_and_served(self, tmp_path):
        pipeline, midict = self._pipeline(tmp_path)
        source = tmp_path / "Takao.ttf"
        source.write_bytes(b"fake-font")

        url = pipeline._served_font_url(str(source))

        assert url == "/_addons/Anki-Dictionary/user_files/fonts/Takao.ttf"
        staged = Path(midict.addon_root) / "user_files" / "fonts" / "Takao.ttf"
        assert staged.read_bytes() == b"fake-font"

    def test_missing_font_is_skipped_rather_than_injected(self, tmp_path):
        pipeline, midict = self._pipeline(tmp_path)

        assert pipeline._served_font_url(str(tmp_path / "nope.ttf")) is None

        pipeline._inject_font(str(tmp_path / "nope.ttf"))
        midict.eval.assert_not_called()

    def test_inject_font_uses_served_url_and_clean_family(self, tmp_path):
        pipeline, midict = self._pipeline(tmp_path)
        source = tmp_path / "Takao.ttf"
        source.write_bytes(b"fake-font")

        pipeline._inject_font(str(source))

        (call,) = midict.eval.call_args_list
        js = call.args[0]
        assert "/_addons/Anki-Dictionary/user_files/fonts/Takao.ttf" in js
        assert '"Takao"' in js
        assert str(tmp_path) not in js
