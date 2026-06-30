import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anki_dictionary.core.database import DictDB
from anki_dictionary.core.search.query import SearchQueryBuilder
from scripts.create_empty_db import create_empty_database


class TestDictDB(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for database tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "dictionaries.sqlite")

        # Patch get_db_dir to return our temp directory
        self.patcher = patch(
            "anki_dictionary.core.database.get_db_dir", return_value=self.test_dir.name
        )
        self.mock_get_db_dir = self.patcher.start()

        # Patch get_addon_config to return default values
        self.config_patcher = patch("anki_dictionary.core.database.get_addon_config")
        self.mock_get_config = self.config_patcher.start()
        self.mock_get_config.return_value = {
            "star_char": "★",
            "star_thresholds": [1501, 5001, 15001, 30001, 60001],
            "show_stars": True,
            "show_rank": False,
            "show_hsk": True,
            "hsk_mode": "hsk3",
        }

        # Use the REAL creation script to set up the database
        create_empty_database(self.db_path)

        # Initialize DictDB
        self.db = DictDB()

    def tearDown(self):
        self.db.closeConnection()
        self.patcher.stop()
        self.config_patcher.stop()
        self.test_dir.cleanup()

    def test_add_languages(self):
        langs = ["English", "Japanese", "Chinese"]
        self.db.addLanguages(langs)

        db_langs = self.db.getCurrentDbLangs()
        for lang in langs:
            self.assertIn(lang, db_langs)
        self.assertEqual(len(db_langs), 3)

    def test_get_lang_id(self):
        self.db.addLanguages(["English"])
        lang_id = self.db.getLangId("English")
        self.assertIsNotNone(lang_id)
        self.assertEqual(self.db.getLangId("NonExistent"), None)

    def test_add_dict(self):
        self.db.addLanguages(["English"])
        success, message, final_name = self.db.addDict("TestDict", "English", "[]")

        self.assertTrue(success)
        self.assertEqual(final_name, "TestDict")
        self.assertTrue(self.db.dictExists("TestDict", "English"))

        # Check if table was created
        lid = self.db.getLangId("English")
        table_name = self.db.formatDictName(lid, "TestDict")
        cursor = self.db._get_cursor()
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_normalize_dict_name(self):
        test_cases = [
            ("Normal Name", "Normal_Name"),
            ("Name [With] Brackets", "Name_With_Brackets"),
            ("Special!@#$%^&*()Chars", "SpecialChars"),
            ("Path/With/Slashes", "Path_With_Slashes"),
            ("", "unnamed_dictionary"),
            ("   Spaces   ", "___Spaces___"),
        ]
        for input_name, expected in test_cases:
            self.assertEqual(self.db.normalize_dict_name(input_name), expected)

    def test_star_count(self):
        self.assertEqual(self.db.getStarCount(500), "★★★★★")
        self.assertEqual(self.db.getStarCount(2000), "★★★★")
        self.assertEqual(self.db.getStarCount(10000), "★★★")
        self.assertEqual(self.db.getStarCount(25000), "★★")
        self.assertEqual(self.db.getStarCount(50000), "★")
        self.assertEqual(self.db.getStarCount(100000), "")

    def test_kaner(self):
        # Katakana to Hiragana
        self.assertEqual(self.db.kana_converter("リンゴ", True), "りんご")
        # Hiragana to Katakana
        self.assertEqual(self.db.kana_converter("りんご", False), "リンゴ")

    def test_process_definition_html(self):
        html = "Line 1\nLine 2<br/>Line 3 &lt;b&gt;bold&lt;/b&gt;"
        processed = SearchQueryBuilder.process_definition_html(html)
        self.assertIn("Line 1<br>Line 2<br>Line 3 <b>bold</b>", processed)

        # Test leading/trailing whitespace and <br>
        html2 = "  \n<br>  Definition content  <br/>\n  "
        processed2 = SearchQueryBuilder.process_definition_html(html2)
        self.assertEqual(processed2, "Definition content")

        # Test multiple <br> tags
        html3 = "<br><br>Content<br>   <br>"
        processed3 = SearchQueryBuilder.process_definition_html(html3)
        self.assertEqual(processed3, "Content")

    def test_dictionary_data_lifecycle(self):
        """Test creating a dictionary, importing data, and searching."""
        self.db.addLanguages(["Japanese"])
        success, _, dict_name = self.db.addDict("TestJP", "Japanese", "[]")
        self.assertTrue(success)

        lid = self.db.getLangId("Japanese")
        table_name = self.db.formatDictName(lid, dict_name)

        # Prepare test data
        # term, altterm, pronunciation, pos, definition, examples, audio, frequency, starCount
        test_data = [
            (
                "食べる",
                "たべる",
                "taberu",
                "verb",
                "To eat",
                "リンゴを食べる",
                "audio.mp3",
                100,
                "★★★★★",
            ),
            (
                "飲む",
                "のむ",
                "nomu",
                "verb",
                "To drink",
                "水を飲む",
                "audio2.mp3",
                500,
                "★★★★★",
            ),
        ]

        self.db.importToDict(table_name, test_data)
        self.db.commitChanges()

        # Search
        selected_group = {"dictionaries": [{"dict": "TestJP", "lang": "Japanese"}]}
        results = self.db.searchTerm(
            term="食べる",
            selectedGroup=selected_group,
            conjugations={},
            sT="Exact",
            deinflect=False,
            dictLimit="10",
            maxDefs=50,
        )

        self.assertIn("TestJP", results)
        self.assertEqual(len(results["TestJP"]), 1)
        self.assertEqual(results["TestJP"][0]["term"], "食べる")
        self.assertEqual(results["TestJP"][0]["definition"], "To eat")

    def test_extra_data_unification(self):
        """Test that frequency and level data are unified correctly via WordListRegistry."""
        lang = "Klingon"
        self.db.addLanguages([lang])

        word_lists_dir = os.path.join(self.test_dir.name, "word_lists")
        os.makedirs(word_lists_dir, exist_ok=True)

        # Create a frequency list (simple list format)
        freq_data = ["的", "我", "你"]  # Rank 0, 1, 2
        with open(
            os.path.join(word_lists_dir, f"{lang}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(freq_data, f)

        # Create an extra level list (e.g. HSK equivalent) — string values for level detection
        level_data = {"的": "1", "我": "1"}
        with open(
            os.path.join(word_lists_dir, f"{lang}_Level.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(level_data, f)

        self.db._registry.clear_cache()

        # Get extra data
        providers = self.db._get_extra_data(lang)

        self.assertEqual(len(providers), 2)
        # Find the rank provider
        rank_p = next(p for p in providers if p.type == "rank")
        self.assertEqual(rank_p.name, "Frequency")

        # Find the level provider
        level_p = next(p for p in providers if p.type == "level")
        self.assertEqual(level_p.name, "Level")

        # Test applying to an entry
        entry = {
            "term": "我",
            "altterm": "",
            "pronunciation": "",
            "frequency": "",
        }
        config = self.mock_get_config.return_value

        self.db._apply_frequency_info(entry, providers, config)

        self.assertEqual(entry["starCount"], "\u2605\u2605\u2605\u2605\u2605")
        self.assertEqual(entry["levelLabels"], "Level:1")

    def test_get_term_frequency_info(self):
        """Test the get_term_frequency_info public method."""
        lang = "TestLang"
        self.db.addLanguages([lang])

        word_lists_dir = os.path.join(self.test_dir.name, "word_lists")
        os.makedirs(word_lists_dir, exist_ok=True)

        # Create a frequency list
        freq_data = ["Word1", "Word2"]
        with open(
            os.path.join(word_lists_dir, f"{lang}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(freq_data, f)

        self.db._registry.clear_cache()

        # Test lookup
        config = self.mock_get_config.return_value
        result = self.db.get_term_frequency_info("Word1", lang, config)

        self.assertEqual(result["term"], "Word1")
        self.assertEqual(result["starCount"], "\u2605\u2605\u2605\u2605\u2605")
        self.assertEqual(result["levelLabels"], "")

        # Test empty lang
        result_empty = self.db.get_term_frequency_info("Word1", "", config)
        self.assertEqual(result_empty["starCount"], "")


if __name__ == "__main__":
    unittest.main()
