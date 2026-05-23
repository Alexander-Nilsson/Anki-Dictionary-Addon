# -*- coding: utf-8 -*-
from __future__ import annotations

import atexit
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Module-level mocks for Qt, Anki, and aqt BEFORE any local imports.
#
# We cannot use ``type('X', (MagicMock,), {})`` because MagicMock.__init__
# interprets the first positional argument as *spec*, and Qt code does
# ``super().__init__(parent, Qt.WindowType.Window)``, passing MagicMock
# instances as positional args, triggering ``InvalidSpecError``.
#
# Instead we create a lightweight mock base that swallows ``__init__``
# arguments and caches attribute access in an internal dict so that
# ``instance.method`` always returns the *same* MagicMock (needed for
# ``.return_value`` and ``assert_called_with`` to work).
# ---------------------------------------------------------------------------


class _QtMockMeta(type):
    """Metaclass for mock Qt classes – returns a MagicMock for any
    class-level attribute access (e.g. ``QHeaderView.ResizeMode``)."""

    def __getattr__(cls, name: str):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return MagicMock()


class _QtMockBase(metaclass=_QtMockMeta):
    """Base for every mock Qt widget/object.

    ``__init__`` swallows all arguments so that any Qt parent/flags
    arguments never reach Mock's spec-setting machinery.
    Instance-level attribute access is cached so that
    ``instance.foo`` returns the *same* MagicMock every time.
    """

    def __init__(self, *args, **kwargs):
        self._mock_attrs: dict[str, MagicMock] = {}

    def __getattr__(self, name: str):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name not in self._mock_attrs:
            self._mock_attrs[name] = MagicMock()
        return self._mock_attrs[name]


_QT_CLASSES = [
    "QAbstractItemView",
    "QCheckBox",
    "QComboBox",
    "QDialog",
    "QDoubleSpinBox",
    "QEvent",
    "QFileDialog",
    "QFontDatabase",
    "QFormLayout",
    "QFrame",
    "QGroupBox",
    "QHBoxLayout",
    "QHeaderView",
    "QIcon",
    "QKeySequence",
    "QLabel",
    "QLineEdit",
    "QMessageBox",
    "QPushButton",
    "QRadioButton",
    "QScrollArea",
    "QShortcut",
    "QSize",
    "QSpinBox",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextEdit",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
]

# Save original modules so we can restore them at exit
_saved_modules = {}
for _mod_name in [
    "aqt.qt",
    "aqt",
    "aqt.utils",
    "aqt.webview",
    "anki.utils",
    "anki.hooks",
    "anki.lang",
]:
    _saved_modules[_mod_name] = sys.modules.get(_mod_name)

_mock_aqt_qt = types.ModuleType("aqt.qt")
for _name in _QT_CLASSES:
    setattr(_mock_aqt_qt, _name, type(_name, (_QtMockBase,), {}))
_mock_aqt_qt.Qt = MagicMock()
sys.modules["aqt.qt"] = _mock_aqt_qt

# -- aqt root module --
_mock_aqt = types.ModuleType("aqt")
_mock_aqt.mw = MagicMock()
sys.modules["aqt"] = _mock_aqt

# -- aqt.utils --
_mock_aqt_utils = types.ModuleType("aqt.utils")
for _n in ("tooltip", "showInfo", "openLink", "askUser"):
    setattr(_mock_aqt_utils, _n, MagicMock())
sys.modules["aqt.utils"] = _mock_aqt_utils

# -- aqt.webview --
_mock_aqt_webview = types.ModuleType("aqt.webview")
_mock_aqt_webview.AnkiWebView = MagicMock()
sys.modules["aqt.webview"] = _mock_aqt_webview

# -- anki sub-modules --
_mock_anki_utils = types.ModuleType("anki.utils")
_mock_anki_utils.is_mac = False
_mock_anki_utils.is_win = False
_mock_anki_utils.is_lin = True
sys.modules["anki.utils"] = _mock_anki_utils

_mock_anki_hooks = types.ModuleType("anki.hooks")
_mock_anki_hooks.addHook = MagicMock()
sys.modules["anki.hooks"] = _mock_anki_hooks

_mock_anki_lang = types.ModuleType("anki.lang")
_mock_anki_lang._ = lambda x: x
sys.modules["anki.lang"] = _mock_anki_lang

# -- anki_dictionary.ui.dialogs.dictionary_manager (deep import chain) --
_mock_dict_mgr = types.ModuleType("anki_dictionary.ui.dialogs.dictionary_manager")
_mock_dict_mgr.DictionaryManagerWidget = MagicMock()
sys.modules["anki_dictionary.ui.dialogs.dictionary_manager"] = _mock_dict_mgr


def _restore_modules():
    for _mod_name, _mod in _saved_modules.items():
        if _mod is not None:
            sys.modules[_mod_name] = _mod
        elif _mod_name in sys.modules:
            del sys.modules[_mod_name]


atexit.register(_restore_modules)

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------
from anki_dictionary.ui.settings.settings_gui import SettingsGui
from anki_dictionary.ui.settings.dict_groups_tab import DictionaryGroupsTab
from anki_dictionary.ui.settings.export_templates_tab import ExportTemplatesTab
from anki_dictionary.ui.settings.dict_groups import DictGroupEditor
from anki_dictionary.ui.settings.templates import TemplateEditor


# ===================================================================
# DictionaryGroupsTab
# ===================================================================
class TestDictionaryGroupsTab(unittest.TestCase):
    def setUp(self):
        self.mw = MagicMock()
        self.parent = MagicMock()
        self.config = {
            "DictionaryGroups": {
                "group1": {
                    "dictionaries": ["dict_a"],
                    "customFont": False,
                    "font": "Arial",
                },
                "group2": {
                    "dictionaries": ["dict_b", "dict_c"],
                    "customFont": True,
                    "font": "Custom.ttf",
                },
            }
        }
        self.dict_names = ["dict_a", "dict_b", "dict_c", "Images"]
        self.tab = DictionaryGroupsTab(
            self.mw,
            self.parent,
            lambda: self.config,
            lambda: self.dict_names,
        )

    def test_loadGroupTable_populates_table(self):
        self.tab.loadGroupTable()

        self.tab.table.setRowCount.assert_called()
        count = self.tab.table.setItem.call_count
        self.assertEqual(
            count,
            len(self.config["DictionaryGroups"]),
            f"Expected {len(self.config['DictionaryGroups'])} setItem calls, got {count}",
        )

    def test_addGroup_opens_editor(self):
        with patch(
            "anki_dictionary.ui.settings.dict_groups_tab.DictGroupEditor"
        ) as mock_editor_cls:
            mock_editor = MagicMock()
            mock_editor_cls.return_value = mock_editor

            self.tab.addGroup()

            mock_editor_cls.assert_called_once_with(
                self.mw, self.parent, self.dict_names
            )
            mock_editor.clearGroupEditor.assert_called_once_with(True)
            mock_editor.exec.assert_called_once()

    def test_editGroup_opens_editor_with_existing_data(self):
        with patch(
            "anki_dictionary.ui.settings.dict_groups_tab.DictGroupEditor"
        ) as mock_editor_cls:
            mock_editor = MagicMock()
            mock_editor_cls.return_value = mock_editor

            mock_item = MagicMock()
            mock_item.text.return_value = "group1"
            self.tab.table.item.return_value = mock_item

            self.tab.editGroup(0)

            mock_editor_cls.assert_called_once_with(
                self.mw,
                self.parent,
                self.dict_names,
                self.config["DictionaryGroups"]["group1"],
                "group1",
            )
            mock_editor.exec.assert_called_once()

    def test_editGroup_skips_when_group_not_in_config(self):
        with patch(
            "anki_dictionary.ui.settings.dict_groups_tab.DictGroupEditor"
        ) as mock_editor_cls:
            mock_item = MagicMock()
            mock_item.text.return_value = "nonexistent_group"
            self.tab.table.item.return_value = mock_item

            self.tab.editGroup(0)

            mock_editor_cls.assert_not_called()

    def test_removeGroup_removes_and_saves(self):
        with (
            patch("anki_dictionary.ui.settings.dict_groups_tab.miAsk") as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.dict_groups_tab.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = True

            mock_item = MagicMock()
            mock_item.text.return_value = "group1"
            self.tab.table.item.return_value = mock_item

            self.tab.removeGroup(0)

            mock_miAsk.assert_called_once()
            mock_save.assert_called_once()
            self.assertNotIn("group1", self.config["DictionaryGroups"])
            self.tab.table.removeRow.assert_called_with(0)

    def test_removeGroup_skipped_when_cancelled(self):
        with (
            patch("anki_dictionary.ui.settings.dict_groups_tab.miAsk") as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.dict_groups_tab.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = False

            mock_item = MagicMock()
            mock_item.text.return_value = "group1"
            self.tab.table.item.return_value = mock_item

            self.tab.removeGroup(0)

            mock_save.assert_not_called()

    def test_editGroupRow_returns_lambda(self):
        fn = self.tab.editGroupRow(2)
        self.assertTrue(callable(fn))

    def test_removeGroupRow_returns_lambda(self):
        fn = self.tab.removeGroupRow(2)
        self.assertTrue(callable(fn))


# ===================================================================
# ExportTemplatesTab
# ===================================================================
class TestExportTemplatesTab(unittest.TestCase):
    def setUp(self):
        self.mw = MagicMock()
        self.parent = MagicMock()
        self.config = {
            "ExportTemplates": {
                "template1": {
                    "noteType": "Basic",
                    "sentence": "Sentence",
                    "word": "Word",
                },
                "template2": {
                    "noteType": "Basic (and reversed card)",
                    "sentence": "Sentence",
                    "word": "Expression",
                },
            }
        }
        self.dict_names = ["dict_a", "Images"]
        self.tab = ExportTemplatesTab(
            self.mw,
            self.parent,
            lambda: self.config,
            lambda: self.dict_names,
        )

    def test_loadTemplateTable_populates_table(self):
        self.tab.loadTemplateTable()

        self.tab.table.setRowCount.assert_called()
        count = self.tab.table.setItem.call_count
        self.assertEqual(
            count,
            len(self.config["ExportTemplates"]),
            f"Expected {len(self.config['ExportTemplates'])} setItem calls, got {count}",
        )

    def test_addTemplate_opens_editor(self):
        with patch(
            "anki_dictionary.ui.settings.export_templates_tab.TemplateEditor"
        ) as mock_editor_cls:
            mock_editor = MagicMock()
            mock_editor_cls.return_value = mock_editor

            self.tab.addTemplate()

            mock_editor_cls.assert_called_once_with(
                self.mw, self.parent, self.dict_names
            )
            mock_editor.exec.assert_called_once()

    def test_editTemplate_opens_editor_with_existing_data(self):
        with patch(
            "anki_dictionary.ui.settings.export_templates_tab.TemplateEditor"
        ) as mock_editor_cls:
            mock_editor = MagicMock()
            mock_editor_cls.return_value = mock_editor

            mock_item = MagicMock()
            mock_item.text.return_value = "template1"
            self.tab.table.item.return_value = mock_item

            self.tab.editTemplate(0)

            mock_editor_cls.assert_called_once_with(
                self.mw,
                self.parent,
                self.dict_names,
                self.config["ExportTemplates"]["template1"],
                "template1",
            )
            mock_editor.loadTemplateEditor.assert_called_once_with(
                self.config["ExportTemplates"]["template1"], "template1"
            )
            mock_editor.exec.assert_called_once()

    def test_editTemplate_skips_when_not_in_config(self):
        with patch(
            "anki_dictionary.ui.settings.export_templates_tab.TemplateEditor"
        ) as mock_editor_cls:
            mock_item = MagicMock()
            mock_item.text.return_value = "nonexistent"
            self.tab.table.item.return_value = mock_item

            self.tab.editTemplate(0)

            mock_editor_cls.assert_not_called()

    def test_removeTemplate_removes_and_saves(self):
        with (
            patch(
                "anki_dictionary.ui.settings.export_templates_tab.miAsk"
            ) as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.export_templates_tab.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = True

            mock_item = MagicMock()
            mock_item.text.return_value = "template1"
            self.tab.table.item.return_value = mock_item

            self.tab.removeTemplate(0)

            mock_miAsk.assert_called_once()
            mock_save.assert_called_once()
            self.assertNotIn("template1", self.config["ExportTemplates"])
            self.tab.table.removeRow.assert_called_with(0)

    def test_removeTemplate_skipped_when_cancelled(self):
        with (
            patch(
                "anki_dictionary.ui.settings.export_templates_tab.miAsk"
            ) as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.export_templates_tab.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = False

            mock_item = MagicMock()
            mock_item.text.return_value = "template1"
            self.tab.table.item.return_value = mock_item

            self.tab.removeTemplate(0)

            mock_save.assert_not_called()

    def test_removeTempRow_returns_lambda(self):
        fn = self.tab.removeTempRow(1)
        self.assertTrue(callable(fn))

    def test_editTempRow_returns_lambda(self):
        fn = self.tab.editTempRow(1)
        self.assertTrue(callable(fn))


# ===================================================================
# DictGroupEditor
# ===================================================================
class TestDictGroupEditor(unittest.TestCase):
    def test_init_creates_expected_widgets(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a", "dict_b"])

        self.assertIsNotNone(editor.groupName)
        self.assertIsNotNone(editor.fontFromDropdown)
        self.assertIsNotNone(editor.fontFromFile)
        self.assertIsNotNone(editor.fontDropDown)
        self.assertIsNotNone(editor.fontFileName)
        self.assertIsNotNone(editor.browseFontFile)
        self.assertIsNotNone(editor.dictionaries)
        self.assertIsNotNone(editor.selectAll)
        self.assertIsNotNone(editor.removeAll)
        self.assertIsNotNone(editor.cancelButton)
        self.assertIsNotNone(editor.saveButton)

    def test_init_with_group_loads_existing(self):
        mw = MagicMock()
        parent = MagicMock()
        group = {
            "dictionaries": ["dict_a"],
            "customFont": True,
            "font": "Custom.ttf",
        }
        editor = DictGroupEditor(mw, parent, ["dict_a"], group, "mygroup")

        self.assertFalse(editor.new)
        editor.setWindowTitle.assert_any_call("Edit Dictionary Group")
        editor.groupName.setText.assert_called_with("mygroup")
        editor.groupName.setEnabled.assert_called_with(False)

    def test_getSelectedDictionaries_returns_correct_format(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a", "dict_b"])

        editor.dictionaries.rowCount.return_value = 2

        items = {}
        for row in range(2):
            for col in range(3):
                item = MagicMock()
                item.text.return_value = ""
                items[(row, col)] = item

        items[(0, 0)].text.return_value = "dict_a"
        items[(0, 1)].text.return_value = "1"
        items[(1, 0)].text.return_value = "dict_b"
        items[(1, 1)].text.return_value = "2"

        def item_side(row, col):
            return items.get((row, col), MagicMock())

        editor.dictionaries.item.side_effect = item_side

        result = editor.getSelectedDictionaries()
        self.assertEqual(result, [[0, 1, "dict_a"], [1, 2, "dict_b"]])

        result_names = editor.getSelectedDictionaries(onlyNames=True)
        self.assertEqual(result_names, ["dict_a", "dict_b"])

    def test_clearGroupEditor_resets_state(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a"])

        editor.groupName.reset_mock()
        editor.groupName.setEnabled.reset_mock()
        editor.setWindowTitle.reset_mock()
        editor.fontFromDropdown.setChecked.reset_mock()
        editor.fontFileName.setText.reset_mock()
        editor.fontDropDown.setCurrentIndex.reset_mock()

        editor.clearGroupEditor(True)

        self.assertTrue(editor.groupName.clear.called)
        editor.groupName.setEnabled.assert_called_with(True)
        editor.fontFromDropdown.setChecked.assert_called_with(True)
        editor.fontFileName.setText.assert_called_with("None Selected")
        editor.fontDropDown.setCurrentIndex.assert_called_with(0)

    def test_toggleFontType_from_file(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a"])

        editor.toggleFontType(True)

        editor.fontDropDown.setEnabled.assert_called_with(False)
        editor.browseFontFile.setEnabled.assert_called_with(True)
        editor.fontFileName.setEnabled.assert_called_with(True)

    def test_toggleFontType_from_dropdown(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a"])

        editor.toggleFontType(False)

        editor.fontDropDown.setEnabled.assert_called_with(True)
        editor.browseFontFile.setEnabled.assert_called_with(False)
        editor.fontFileName.setEnabled.assert_called_with(False)

    def test_resetNew(self):
        mw = MagicMock()
        parent = MagicMock()
        editor = DictGroupEditor(mw, parent, ["dict_a"])
        editor.resetNew()
        self.assertTrue(editor.new)


# ===================================================================
# TemplateEditor
# ===================================================================
class TestTemplateEditor(unittest.TestCase):
    def test_init_creates_expected_widgets(self):
        mw = MagicMock()
        mw.col.models.all.return_value = [
            {
                "name": "Basic",
                "flds": [{"name": "Front"}, {"name": "Back"}],
            }
        ]
        editor = TemplateEditor(mw, MagicMock(), ["dict_a", "Images"])

        self.assertIsNotNone(editor.templateName)
        self.assertIsNotNone(editor.noteType)
        self.assertIsNotNone(editor.wordField)
        self.assertIsNotNone(editor.sentenceField)
        self.assertIsNotNone(editor.secondaryField)
        self.assertIsNotNone(editor.notesField)
        self.assertIsNotNone(editor.imageField)
        self.assertIsNotNone(editor.audioField)
        self.assertIsNotNone(editor.otherDictsField)
        self.assertIsNotNone(editor.dictionaries)
        self.assertIsNotNone(editor.fields)
        self.assertIsNotNone(editor.addDictField)
        self.assertIsNotNone(editor.dictFieldsTable)
        self.assertIsNotNone(editor.entrySeparator)
        self.assertIsNotNone(editor.cancelButton)
        self.assertIsNotNone(editor.saveButton)

    def test_init_with_existing_template(self):
        mw = MagicMock()
        mw.col.models.all.return_value = [
            {
                "name": "Basic",
                "flds": [{"name": "Front"}, {"name": "Back"}],
            }
        ]
        template_data = {
            "noteType": "Basic",
            "sentence": "Front",
            "word": "Back",
            "secondary": "Don't Export",
            "notes": "Don't Export",
            "image": "Don't Export",
            "audio": "Don't Export",
            "unspecified": "Back",
            "specific": {},
            "separator": "<br><br>",
        }
        editor = TemplateEditor(
            mw, MagicMock(), ["dict_a"], template_data, "mytemplate"
        )

        editor.setWindowTitle.assert_any_call("Edit Export Template")


# ===================================================================
# SettingsGui
# ===================================================================
_CONFIG_WITH_EMPTY_GROUPS = {
    "DictionaryGroups": {},
    "ExportTemplates": {},
}


class TestSettingsGui(unittest.TestCase):
    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_init_creates_tabs(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = SettingsGui(mw, "/tmp", MagicMock())

        self.assertIsNotNone(gui.dictGroupsTab)
        self.assertIsNotNone(gui.exportTemplatesTab)
        self.assertIsNotNone(gui.llmTab)
        self.assertIsNotNone(gui.forvoTab)
        self.assertIsNotNone(gui.frequencyTab)

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_getConfig_returns_config(self, mock_get_config):
        expected = {"key": "value", "ExportTemplates": {}, "DictionaryGroups": {}}
        mock_get_config.return_value = expected
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = SettingsGui(mw, "/tmp", MagicMock())

        result = gui.getConfig()
        self.assertEqual(result, expected)

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_getDictionaryNames_returns_sorted_list(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = [
            {"dict": "l1nameEnglish"},
            {"dict": "l2nameFrench"},
        ]
        gui = SettingsGui(mw, "/tmp", MagicMock())

        gui.llmTab.llmEnabled.isChecked.return_value = True
        gui.forvoTab.forvoEnabled.isChecked.return_value = True

        names = gui.getDictionaryNames()
        self.assertIn("English", names)
        self.assertIn("French", names)
        self.assertIn("Images", names)
        self.assertIn("LLM", names)
        self.assertIn("Forvo", names)
        self.assertEqual(names, sorted(names, key=str.casefold))

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_getDictionaryNames_without_llm_forvo(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = SettingsGui(mw, "/tmp", MagicMock())

        gui.llmTab.llmEnabled.isChecked.return_value = False
        gui.forvoTab.forvoEnabled.isChecked.return_value = False

        names = gui.getDictionaryNames()
        self.assertIn("Images", names)
        self.assertNotIn("LLM", names)
        self.assertNotIn("Forvo", names)

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_cleanDictName_removes_pattern(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        gui = SettingsGui(MagicMock(), "/tmp", MagicMock())

        self.assertEqual(gui.cleanDictName("l1nameEnglish"), "English")
        self.assertEqual(gui.cleanDictName("l42nameHello"), "Hello")
        self.assertEqual(gui.cleanDictName("NoPattern"), "NoPattern")
        self.assertEqual(gui.cleanDictName("l1name"), "")
        self.assertEqual(gui.cleanDictName(""), "")

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_wrapInScrollArea(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        gui = SettingsGui(MagicMock(), "/tmp", MagicMock())
        mock_widget = MagicMock()
        scroll = gui.wrapInScrollArea(mock_widget)

        scroll.setWidget.assert_called_with(mock_widget)
        scroll.setWidgetResizable.assert_called_with(True)

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_restoreDefaults_with_confirmation(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        mw = MagicMock()
        mw.addonManager.addonConfigDefaults.return_value = {"default": "config"}
        gui = SettingsGui(mw, "/tmp", MagicMock())

        with (
            patch("anki_dictionary.ui.settings.settings_gui.miAsk") as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.settings_gui.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = True
            gui.restoreDefaults()
            mock_save.assert_called_once_with({"default": "config"})
            gui.reboot.assert_called_once()

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_restoreDefaults_without_confirmation(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        mw = MagicMock()
        gui = SettingsGui(mw, "/tmp", MagicMock())

        with (
            patch("anki_dictionary.ui.settings.settings_gui.miAsk") as mock_miAsk,
            patch(
                "anki_dictionary.ui.settings.settings_gui.save_addon_config"
            ) as mock_save,
        ):
            mock_miAsk.return_value = False
            gui.restoreDefaults()
            mock_save.assert_not_called()

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_loadConfig_sets_widgets(self, mock_get_config):
        full_cfg = {
            **_CONFIG_WITH_EMPTY_GROUPS,
            "highlightTarget": False,
            "maxSearch": 500,
            "dictSearch": 25,
            "imageSearchRegion": "Japan",
            "maxWidth": 800,
            "maxHeight": 300,
            "frontBracket": "(",
            "backBracket": ")",
            "showTarget": True,
            "tooltips": False,
            "dictAlwaysOnTop": True,
            "jReadingCards": True,
        }
        mock_get_config.return_value = full_cfg
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = SettingsGui(mw, "/tmp", MagicMock())

        gui.loadConfig()

        gui.highlightTarget.setChecked.assert_called_with(full_cfg["highlightTarget"])
        gui.totalDefs.setValue.assert_called_with(full_cfg["maxSearch"])
        gui.dictDefs.setValue.assert_called_with(full_cfg["dictSearch"])
        gui.imageSearchCountry.setCurrentText.assert_called_with(
            full_cfg["imageSearchRegion"]
        )
        gui.maxImgWidth.setValue.assert_called_with(full_cfg["maxWidth"])
        gui.maxImgHeight.setValue.assert_called_with(full_cfg["maxHeight"])
        gui.frontBracket.setText.assert_called_with(full_cfg["frontBracket"])
        gui.backBracket.setText.assert_called_with(full_cfg["backBracket"])
        gui.showTarget.setChecked.assert_called_with(full_cfg["showTarget"])
        gui.tooltipCB.setChecked.assert_called_with(full_cfg["tooltips"])
        gui.dictOnTop.setChecked.assert_called_with(full_cfg["dictAlwaysOnTop"])
        gui.genJSExport.setChecked.assert_called_with(full_cfg["jReadingCards"])

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_saveConfig_saves_widgets(self, mock_get_config):
        mock_get_config.return_value = {
            "ExportTemplates": {},
            "DictionaryGroups": {},
        }
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = SettingsGui(mw, "/tmp", MagicMock())

        gui.highlightTarget.isChecked.return_value = True
        gui.totalDefs.value.return_value = 100
        gui.dictDefs.value.return_value = 10
        gui.imageSearchCountry.currentText.return_value = "United States"
        gui.maxImgWidth.value.return_value = 500
        gui.maxImgHeight.value.return_value = 200
        gui.frontBracket.text.return_value = "【"
        gui.backBracket.text.return_value = "】"
        gui.showTarget.isChecked.return_value = False
        gui.tooltipCB.isChecked.return_value = True
        gui.dictOnTop.isChecked.return_value = False
        gui.genJSExport.isChecked.return_value = False

        with patch(
            "anki_dictionary.ui.settings.settings_gui.save_addon_config"
        ) as mock_save:
            gui.saveConfig()

            config = mock_save.call_args[0][0]
            self.assertTrue(config["highlightTarget"])
            self.assertEqual(config["maxSearch"], 100)
            self.assertEqual(config["dictSearch"], 10)
            self.assertEqual(config["imageSearchRegion"], "United States")
            self.assertEqual(config["maxWidth"], 500)
            self.assertEqual(config["maxHeight"], 200)
            self.assertEqual(config["frontBracket"], "【")
            self.assertEqual(config["backBracket"], "】")
            self.assertFalse(config["showTarget"])
            self.assertTrue(config["tooltips"])
            self.assertFalse(config["dictAlwaysOnTop"])
            self.assertFalse(config["jReadingCards"])

    @patch("anki_dictionary.ui.settings.settings_gui.get_addon_config")
    def test_miQLabel_creates_label(self, mock_get_config):
        mock_get_config.return_value = _CONFIG_WITH_EMPTY_GROUPS
        gui = SettingsGui(MagicMock(), "/tmp", MagicMock())
        label = gui.miQLabel("Test", 100)
        label.setFixedHeight.assert_called_with(30)
        label.setFixedWidth.assert_called_with(100)


if __name__ == "__main__":
    unittest.main()
