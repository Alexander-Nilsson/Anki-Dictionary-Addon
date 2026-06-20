# -*- coding: utf-8 -*-
from __future__ import annotations

import atexit
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Module-level aqt / anki mocking – must happen before ANY addon import
#
# IMPORTANT: We save original module references so we can restore them
# after tests complete, avoiding test interaction when running the full suite.
# ---------------------------------------------------------------------------
#
# Qt classes used ONLY for instantiation (QWidget, QVBoxLayout, …) stay as
# MagicMock – that works fine.  Classes used as BASE CLASSES
# (QTextEdit, QLineEdit) need to be real types so that `class Foo(QTextEdit)`
# does not produce a Mock object.
# ---------------------------------------------------------------------------
class _QTextEdit:
    """Stub so that MITextEdit(QTextEdit) yields a real class.
    Caches method mocks per-instance so that clear() always returns
    the same MagicMock for a given instance.
    """

    def __init__(self, parent=None):
        self.__dict__["_method_mocks"] = {}

    def __getattr__(self, name):
        if name not in self.__dict__["_method_mocks"]:
            self.__dict__["_method_mocks"][name] = MagicMock()
        return self.__dict__["_method_mocks"][name]


class _QLineEdit:
    """Stub so that MILineEdit(QLineEdit) yields a real class."""

    def __init__(self, parent=None):
        self.__dict__["_method_mocks"] = {}

    def __getattr__(self, name):
        if name not in self.__dict__["_method_mocks"]:
            self.__dict__["_method_mocks"][name] = MagicMock()
        return self.__dict__["_method_mocks"][name]


_saved_modules = {}
for _mod_name in [
    "aqt",
    "aqt.qt",
    "aqt.utils",
    "anki",
    "anki.utils",
    "anki.notes",
    "anki.sound",
]:
    _saved_modules[_mod_name] = sys.modules.get(_mod_name)


class _QRunnable:
    """Stub so that DuckDuckGo(QRunnable), ForvoWorker(QRunnable) yield real classes."""

    def __init__(self, *args, **kwargs):
        self.__dict__["_method_mocks"] = {}

    def __getattr__(self, name):
        if name not in self.__dict__["_method_mocks"]:
            self.__dict__["_method_mocks"][name] = MagicMock()
        return self.__dict__["_method_mocks"][name]


class _QSize:
    """Stub for QSize – stores width/height so QSize(200, 200).width() works."""

    def __init__(self, width=0, height=0):
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height

    def __repr__(self):
        return f"_QSize({self._width}, {self._height})"


class _QObject:
    """Stub so that DuckDuckGoSignals(QObject), etc. yield real classes."""

    def __init__(self, parent=None):
        self.__dict__["_method_mocks"] = {}

    def __getattr__(self, name):
        if name not in self.__dict__["_method_mocks"]:
            self.__dict__["_method_mocks"][name] = MagicMock()
        return self.__dict__["_method_mocks"][name]


class _MockSignal:
    """Stub for a PyQt signal – connect stores callbacks, emit calls them."""

    def __init__(self, *types):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for cb in self._callbacks:
            cb(*args, **kwargs)


def _pyqtSignal(*types):
    """Stub for pyqtSignal – returns a _MockSignal with working connect/emit."""
    return _MockSignal(*types)


class _QtEnum:
    """Namespace for Qt enums - dynamically creates sub-namespaces and values.

    Allows ``Qt.ScrollBarPolicy.ScrollBarAlwaysOff`` to work without explicitly
    listing every possible enum.  Each sub-namespace attribute returns a
    MagicMock, which is fine for test assertions.
    """

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        ns = _QtEnumNamespace(name)
        object.__setattr__(self, name, ns)
        return ns


class _QtEnumNamespace:
    """A namespace for an enum type, dynamically creates values on access."""

    def __init__(self, name):
        self._name = name

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MagicMock()


_aqt_mock = MagicMock()
_aqt_qt_mock = MagicMock()
_aqt_qt_mock.QTextEdit = _QTextEdit
_aqt_qt_mock.QLineEdit = _QLineEdit
_aqt_qt_mock.QRunnable = _QRunnable
_aqt_qt_mock.QObject = _QObject
_aqt_qt_mock.pyqtSignal = _pyqtSignal
_aqt_qt_mock.QSize = _QSize
_aqt_qt_mock.Qt = _QtEnum()
_aqt_qt_mock.QThreadPool = MagicMock()
_aqt_qt_mock.QImage = MagicMock()
_aqt_utils_mock = MagicMock()
_anki_mock = MagicMock()
_anki_utils_mock = MagicMock()
_anki_utils_mock.is_mac = False
_anki_utils_mock.is_lin = False
_anki_utils_mock.is_win = False
_anki_notes_mock = MagicMock()
_anki_sound_mock = MagicMock()

sys.modules["aqt"] = _aqt_mock
sys.modules["aqt.qt"] = _aqt_qt_mock
sys.modules["aqt.utils"] = _aqt_utils_mock
sys.modules["anki"] = _anki_mock
sys.modules["anki.utils"] = _anki_utils_mock
sys.modules["anki.notes"] = _anki_notes_mock
sys.modules["anki.sound"] = _anki_sound_mock


def _restore_modules():
    for _mod_name, _mod in _saved_modules.items():
        if _mod is not None:
            sys.modules[_mod_name] = _mod
        elif _mod_name in sys.modules:
            del sys.modules[_mod_name]


atexit.register(_restore_modules)

_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Now safe to import addon modules
from anki_dictionary.exporters.html_cleaner import HtmlCleaner  # noqa: E402
from anki_dictionary.exporters.card_exporter import CardExporter  # noqa: E402


# ===================================================================
# HtmlCleaner
# ===================================================================
class TestHtmlCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = HtmlCleaner()

    def test_clean_span_font_weight_to_bold(self):
        html = '<span style="font-weight:600;">bold text</span>'
        result = self.cleaner.cleanHTML(html)
        self.assertIn("bold text", result)
        self.assertNotIn("<span", result)
        self.assertNotIn("</span>", result)

    def test_clean_span_font_style_to_italic(self):
        html = '<span style="font-style:italic;">italic text</span>'
        result = self.cleaner.cleanHTML(html)
        self.assertIn("italic text", result)
        self.assertNotIn("<span", result)

    def test_clean_span_text_decoration_to_underline(self):
        html = '<span style="text-decoration: underline;">underlined text</span>'
        result = self.cleaner.cleanHTML(html)
        self.assertIn("underlined text", result)
        self.assertNotIn("<span", result)

    def test_clean_replaces_paragraph_close_with_br(self):
        html = "<p>first</p><p>second</p>"
        result = self.cleaner.cleanHTML(html)
        self.assertNotIn("<p>", result)
        self.assertNotIn("</p>", result)
        self.assertIn("first", result)
        self.assertIn("second", result)

    def test_clean_strips_html_head_body(self):
        html = "<html><head>meta</head><body>content</body></html>"
        result = self.cleaner.cleanHTML(html)
        self.assertNotIn("<html>", result)
        self.assertNotIn("</html>", result)
        self.assertNotIn("<head>", result)
        self.assertNotIn("<body>", result)
        self.assertIn("content", result)

    def test_clean_strips_bare_span(self):
        html = "<span>just text</span>"
        result = self.cleaner.cleanHTML(html)
        self.assertNotIn("<span>", result)
        self.assertNotIn("</span>", result)
        self.assertEqual(result, "just text")

    def test_clean_empty_string(self):
        self.assertEqual(self.cleaner.cleanHTML(""), "")
        self.assertEqual(self.cleaner.cleanHTML("   "), "")

    def test_clean_strips_trailing_single_br(self):
        result = self.cleaner.cleanHTML("content<br />")
        self.assertEqual(result, "content")

    def test_clean_strips_trailing_two_br(self):
        result = self.cleaner.cleanHTML("content<br /><br />")
        self.assertEqual(result, "content")

    def test_clean_preserves_internal_br(self):
        result = self.cleaner.cleanHTML("line1<br />line2")
        self.assertEqual(result, "line1<br />line2")


# ===================================================================
# CardExporter
# ===================================================================
class TestCardExporter(unittest.TestCase):
    """Tests for CardExporter — uses full instantiation with mocked deps."""

    _base_config = {
        "autoDefinitionSettings": [],
        "ExportTemplates": {
            "Basic": {
                "noteType": "Basic",
                "sentence": "Expression",
                "word": "Word",
                "image": "Image",
                "audio": "Audio",
                "secondary": "Secondary",
                "notes": "Notes",
                "unspecified": "Notes",
                "specific": {},
                "separator": ", ",
            }
        },
        "currentTemplate": "Basic",
        "autoAddCards": False,
        "unknownsToSearch": 3,
        "autoAddDefinitions": False,
        "jReadingCards": False,
        "tooltips": False,
        "currentDeck": "Default",
        "dictAlwaysOnTop": False,
        "exporterSizePos": None,
        "exporterLastTags": "",
    }

    def setUp(self):
        self.config_patcher = patch(
            "anki_dictionary.exporters.card_exporter.get_addon_config"
        )
        self.mock_get_config = self.config_patcher.start()
        self.mock_get_config.return_value = dict(self._base_config)

        self.dictInt = MagicMock()
        self.dictInt.mw = MagicMock()
        self.dictInt.addonPath = "/fake/addon"
        self.dictInt.writeConfig = MagicMock()
        self.dictInt.getMacComboStyle.return_value = ""
        self.dictInt.getMacTableStyle.return_value = ""

        self.dictWeb = MagicMock()

        self.exporter = CardExporter(self.dictInt, self.dictWeb)

        # QLabel() and QTableWidget() return the same MagicMock for every call,
        # so these would all share a single mock across test instances.
        # Give them separate mocks for test isolation.
        self.exporter.audioMap = MagicMock()
        self.exporter.imageMap = MagicMock()
        self.exporter.definitions = MagicMock()
        self.exporter.definitions.rowCount.return_value = 0

    def tearDown(self):
        self.config_patcher.stop()

    # -- Composition ----------------------------------------------------

    def test_composition_creates_html_cleaner(self):
        self.assertIsInstance(self.exporter.html_cleaner, HtmlCleaner)

    # -- fieldValid / emptyValueIfEmptyHtml -----------------------------

    def test_field_valid_returns_true(self):
        self.assertTrue(self.exporter.fieldValid("Expression"))
        self.assertTrue(self.exporter.fieldValid("Notes"))
        self.assertTrue(self.exporter.fieldValid(""))

    def test_field_valid_returns_false_for_dont_export(self):
        self.assertFalse(self.exporter.fieldValid("Don't Export"))

    def test_empty_value_if_empty_html_returns_empty(self):
        html = "<p><br></p>"
        self.assertEqual(self.exporter.emptyValueIfEmptyHtml(html), "")

    def test_empty_value_if_empty_html_returns_original(self):
        self.assertEqual(
            self.exporter.emptyValueIfEmptyHtml("plain text"), "plain text"
        )

    def test_empty_value_if_empty_html_with_content(self):
        html = "<b>content</b>"
        self.assertEqual(self.exporter.emptyValueIfEmptyHtml(html), html)

    # -- addDefinition (was on MediaHandler) ---------------------------

    def test_add_definition_appends_to_list(self):
        self.exporter.addDefinition("TestDict", "apple", "A fruit")
        self.assertEqual(len(self.exporter.definitionList), 1)
        entry = self.exporter.definitionList[0]
        self.assertEqual(entry[0], "TestDict")
        self.assertEqual(entry[2], "A fruit")
        self.assertFalse(entry[3])

    def test_add_definition_sets_word_le_when_empty(self):
        self.exporter.wordLE.text.return_value = ""
        self.exporter.addDefinition("TestDict", "apple", "A fruit")
        self.exporter.wordLE.setText.assert_called_with("apple")

    def test_add_definition_does_not_overwrite_word(self):
        self.exporter.wordLE.text.return_value = "existing"
        self.exporter.addDefinition("TestDict", "apple", "A fruit")
        self.exporter.wordLE.setText.assert_not_called()

    def test_add_definition_duplicate_shows_info(self):
        self.exporter.addDefinition("D", "w", "def1")
        with patch("anki_dictionary.exporters.card_exporter.miInfo") as mock_info:
            self.exporter.addDefinition("D", "w", "def1")
            mock_info.assert_called_once()

    def test_add_definition_increments_row_count(self):
        self.exporter.addDefinition("D", "w", "def")
        self.exporter.definitions.setRowCount.assert_called_with(1)

    def test_add_definition_shortens_long_definitions(self):
        long_def = "A" * 50
        self.exporter.addDefinition("D", "w", long_def)
        entry = self.exporter.definitionList[0]
        short = entry[1]
        self.assertTrue(short.endswith("..."))
        self.assertLessEqual(len(short), 43)

    def test_remove_definition_removes_from_list(self):
        self.exporter.definitionList = [["DictName", "short...", "full", False]]

        mock_item_0 = MagicMock()
        mock_item_0.text.return_value = "DictName"
        mock_item_1 = MagicMock()
        mock_item_1.text.return_value = "short..."

        sel_model = self.exporter.definitions.selectionModel.return_value
        sel_model.currentIndex.return_value.row.return_value = 0
        self.exporter.definitions.item = MagicMock(
            side_effect=lambda row, col: mock_item_0 if col == 0 else mock_item_1
        )

        # Step through removeDefinition manually
        row = self.exporter.definitions.selectionModel().currentIndex().row()
        dictName = self.exporter.definitions.item(row, 0).text()
        shortDef = self.exporter.definitions.item(row, 1).text()

        self.assertEqual(row, 0)
        self.assertEqual(dictName, "DictName")
        self.assertEqual(shortDef, "short...")

        self.exporter.removeFromDefinitionList(dictName, shortDef)

        self.assertEqual(len(self.exporter.definitionList), 0)

    def test_remove_definition_handles_exception_gracefully(self):
        self.exporter.definitions.selectionModel.side_effect = Exception("fail")
        self.exporter.removeDefinition()

    # -- exportWord / exportImage / exportAudio / exportSentence --------

    def test_export_word_sets_text(self):
        self.exporter.exportWord("hello")
        self.exporter.wordLE.setText.assert_called_with("hello")

    def test_play_audio_calls_player_with_path(self):
        self.exporter.audioPath = "/fake/path/audio.mp3"
        self.exporter.media_transfer = MagicMock()
        self.exporter.playAudio()
        self.exporter.media_transfer.play_audio.assert_called_with(
            "/fake/path/audio.mp3"
        )

    def test_play_audio_no_path(self):
        self.exporter.media_transfer = MagicMock()
        self.exporter.playAudio()
        self.exporter.media_transfer.play_audio.assert_not_called()

    def test_export_image_sets_attributes(self):
        self.exporter.imageMap = MagicMock()
        self.exporter.exportImage("/path/img.png", "img.png")
        self.assertEqual(self.exporter.imgName, "img.png")
        self.assertEqual(self.exporter.imgPath, "/path/img.png")

    def test_export_audio_sets_attributes(self):
        self.exporter.audioMap = MagicMock()
        self.exporter.audioPlay = MagicMock()
        self.exporter.exportAudio("/path/a.mp3", "[sound:a.mp3]", "a.mp3")
        self.assertEqual(self.exporter.audioTag, "[sound:a.mp3]")
        self.assertEqual(self.exporter.audioName, "a.mp3")
        self.assertEqual(self.exporter.audioPath, "/path/a.mp3")

    def test_export_sentence_sets_html(self):
        self.exporter.exportSentence("<b>hello</b>")
        self.exporter.sentenceLE.setHtml.assert_called_with("<b>hello</b>")

    def test_export_secondary_sets_html(self):
        self.exporter.exportSecondary("secondary text")
        self.exporter.secondaryLE.setHtml.assert_called_with("secondary text")

    # -- addImgs -------------------------------------------------------

    def test_add_imgs_appends_to_definition_list(self):
        self.exporter.addImgs("word", ["img1"], "thumb")
        self.assertEqual(len(self.exporter.definitionList), 1)

    # -- getDecks -------------------------------------------------------

    def test_get_decks_returns_dict(self):
        decks = self.exporter.getDecks()
        self.assertIsInstance(decks, dict)

    def test_get_decks_returns_empty_when_no_decks(self):
        decks = self.exporter.getDecks()
        self.assertEqual(decks, {})

    def test_get_decks_populated(self):
        deck_info = MagicMock()
        deck_info.id = 12345
        deck_info.name = "Default"
        raw_deck = {"name": "Default", "dyn": False}
        self.exporter.mw.col.decks.all_names_and_ids.return_value = [deck_info]
        self.exporter.mw.col.decks.get.return_value = raw_deck

        decks = self.exporter.getDecks()
        self.assertIn("Default", decks)
        self.assertEqual(decks["Default"], 12345)

    # -- clearCurrent ---------------------------------------------------

    def test_clear_current_resets_definition_list(self):
        self.exporter.definitionList = [("a", "b", "c")]
        self.exporter.clearCurrent()
        self.assertEqual(self.exporter.definitionList, [])

    def test_clear_current_clears_text_widgets(self):
        self.exporter.clearCurrent()
        self.exporter.sentenceLE.clear.assert_called()
        self.exporter.secondaryLE.clear.assert_called()
        self.exporter.notesLE.clear.assert_called()
        self.exporter.wordLE.clear.assert_called()

    def test_clear_current_resets_audio_labels(self):
        self.exporter.audioTag = "[sound:test.mp3]"
        self.exporter.audioName = "test.mp3"
        self.exporter.audioPath = "/path/test.mp3"
        self.exporter.clearCurrent()
        self.assertEqual(self.exporter.audioTag, "")
        self.assertEqual(self.exporter.audioName, "")
        self.assertEqual(self.exporter.audioPath, "")

    def test_clear_current_resets_image_labels(self):
        self.exporter.imgName = "img.png"
        self.exporter.imgPath = "/path/img.png"
        self.exporter.clearCurrent()
        self.assertEqual(self.exporter.imgName, "")
        self.assertEqual(self.exporter.imgPath, "")

    def test_clear_current_sets_audio_map_text(self):
        self.exporter.clearCurrent()
        self.exporter.audioMap.setText.assert_called_with("No Audio Selected")

    def test_clear_current_sets_image_map_text(self):
        self.exporter.clearCurrent()
        self.exporter.imageMap.setText.assert_called_with("No Image Selected")

    def test_clear_current_resets_table(self):
        self.exporter.clearCurrent()
        self.exporter.definitions.setRowCount.assert_called_with(0)

    # -- closeProgressBar -----------------------------------------------

    def test_close_progress_bar_closes_and_deletes(self):
        progress_bar = MagicMock()
        self.exporter.closeProgressBar(progress_bar)
        self.assertTrue(progress_bar.closedBecauseFinishedImporting)
        progress_bar.close.assert_called_once()
        progress_bar.deleteLater.assert_called_once()

    def test_close_progress_bar_none(self):
        self.exporter.closeProgressBar(None)

    def test_close_progress_bar_false(self):
        self.exporter.closeProgressBar(False)

    # -- bulkMediaExportCancelledByBrowserRefresh -----------------------

    def test_bulk_media_export_cancelled_by_browser_refresh(self):
        self.exporter.bulk_processor.media_export_progress_window = MagicMock()
        self.exporter.bulk_processor.media_export_progress_window.current_value = 5

        self.exporter.bulkMediaExportCancelledByBrowserRefresh()

        self.assertIsNone(self.exporter.bulk_processor.media_export_progress_window)
        self.assertFalse(self.exporter.mw.DictBulkMediaExportWasCancelled)

    def test_bulk_media_export_cancelled_no_window(self):
        self.exporter.bulk_processor.media_export_progress_window = None
        self.exporter.bulkMediaExportCancelledByBrowserRefresh()

    # -- attemptAutoAdd -------------------------------------------------

    def test_attempt_auto_add_when_checked(self):
        self.exporter.autoAdd.isChecked.return_value = True
        self.exporter.addCard = MagicMock()
        self.exporter.attemptAutoAdd(bulkExport=False)
        self.exporter.addCard.assert_called_once()

    def test_attempt_auto_add_when_bulk_export(self):
        self.exporter.autoAdd.isChecked.return_value = False
        self.exporter.addCard = MagicMock()
        self.exporter.attemptAutoAdd(bulkExport=True)
        self.exporter.addCard.assert_called_once()

    def test_attempt_auto_add_skipped(self):
        self.exporter.autoAdd.isChecked.return_value = False
        self.exporter.addCard = MagicMock()
        self.exporter.attemptAutoAdd(bulkExport=False)
        self.exporter.addCard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
