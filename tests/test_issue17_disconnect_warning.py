"""Regression tests for Issue #17: Qt disconnect warnings on Windows 10.

Tests verify that cell-widget signals are properly disconnected before
table clearing, regardless of platform.  Uses the real code paths but
mocks Qt so tests can run headless.
"""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

import atexit


class _QtMockMeta(type):
    def __getattr__(cls, name: str):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return MagicMock()


class _QtMockBase(metaclass=_QtMockMeta):
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
    "QVBoxLayout",
    "QWidget",
]

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

_mock_aqt = types.ModuleType("aqt")
_mock_aqt.mw = MagicMock()
sys.modules["aqt"] = _mock_aqt

_mock_aqt_utils = types.ModuleType("aqt.utils")
for _n in ("tooltip", "showInfo", "openLink", "askUser"):
    setattr(_mock_aqt_utils, _n, MagicMock())
sys.modules["aqt.utils"] = _mock_aqt_utils

_mock_aqt_webview = types.ModuleType("aqt.webview")
_mock_aqt_webview.AnkiWebView = MagicMock()
sys.modules["aqt.webview"] = _mock_aqt_webview

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

_mock_dict_mgr = types.ModuleType("anki_dictionary.ui.dialogs.dictionary_manager")
_mock_dict_mgr.DictionaryManagerWidget = MagicMock()
sys.modules["anki_dictionary.ui.dialogs.dictionary_manager"] = _mock_dict_mgr

atexit.register(lambda: None)

from anki_dictionary.ui.settings.dict_groups_tab import DictionaryGroupsTab
from anki_dictionary.ui.settings.export_templates_tab import ExportTemplatesTab


def _make_mock_button() -> MagicMock:
    btn = MagicMock()
    btn.clicked = MagicMock()
    return btn


class TestDisconnectBeforeTableClear(unittest.TestCase):
    """Verify cell-widget signals are disconnected before setRowCount(0)."""

    def setUp(self):
        self.mw = MagicMock()
        self.parent = MagicMock()
        self.config = {
            "DictionaryGroups": {
                "g1": {"dictionaries": ["a"], "customFont": False, "font": "A"},
            },
            "ExportTemplates": {
                "t1": {"noteType": "Basic", "sentence": "S", "word": "W"},
            },
        }
        self.names = ["a", "Images"]

    def _disconnect_and_reload(self, tab, mod_path):
        """Simulate a reload that triggers disconnect then setRowCount(0)."""
        old_edit = _make_mock_button()
        old_del = _make_mock_button()
        tab.table.cellWidget.side_effect = lambda r, c: {
            (0, 1): old_edit,
            (0, 2): old_del,
        }.get((r, c))
        tab.table.rowCount = MagicMock(return_value=1)
        tab.table.columnCount = MagicMock(return_value=3)

        with patch(f"{mod_path}.QPushButton") as mock_btn_cls:
            mock_btn_cls.side_effect = lambda text: _make_mock_button()
            tab.loadGroupTable()

        return old_edit, old_del

    def test_dict_groups_tab_disconnects(self):
        tab = DictionaryGroupsTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        tab.loadGroupTable()
        old_edit, old_del = self._disconnect_and_reload(
            tab, "anki_dictionary.ui.settings.dict_groups_tab"
        )
        old_edit.clicked.disconnect.assert_called_once()
        old_del.clicked.disconnect.assert_called_once()

    def test_export_templates_tab_disconnects(self):
        tab = ExportTemplatesTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        tab.loadTemplateTable()
        old_edit = _make_mock_button()
        old_del = _make_mock_button()
        tab.table.cellWidget.side_effect = lambda r, c: {
            (0, 1): old_edit,
            (0, 2): old_del,
        }.get((r, c))
        tab.table.rowCount = MagicMock(return_value=1)
        tab.table.columnCount = MagicMock(return_value=3)

        with patch(
            "anki_dictionary.ui.settings.export_templates_tab.QPushButton"
        ) as mock_btn_cls:
            mock_btn_cls.side_effect = lambda text: _make_mock_button()
            tab.loadTemplateTable()

        old_edit.clicked.disconnect.assert_called_once()
        old_del.clicked.disconnect.assert_called_once()

    def test_disable_buttons_in_remove_group(self):
        tab = DictionaryGroupsTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        tab.loadGroupTable()

        old_edit = _make_mock_button()
        old_del = _make_mock_button()
        tab.table.cellWidget.side_effect = lambda r, c: {
            (0, 1): old_edit,
            (0, 2): old_del,
        }.get((r, c))
        tab.table.rowCount = MagicMock(return_value=1)
        tab.table.columnCount = MagicMock(return_value=3)

        with (
            patch("anki_dictionary.ui.settings.dict_groups_tab.miAsk") as ask,
            patch("anki_dictionary.ui.settings.dict_groups_tab.save_addon_config"),
            patch("anki_dictionary.ui.settings.dict_groups_tab.QPushButton"),
        ):
            ask.return_value = True
            mock_item = MagicMock()
            mock_item.text.return_value = "g1"
            tab.table.item.return_value = mock_item
            tab.removeGroup(0)

        old_edit.clicked.disconnect.assert_called_once()
        old_del.clicked.disconnect.assert_called_once()

    def test_disable_buttons_in_remove_template(self):
        tab = ExportTemplatesTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        tab.loadTemplateTable()

        old_edit = _make_mock_button()
        old_del = _make_mock_button()
        tab.table.cellWidget.side_effect = lambda r, c: {
            (0, 1): old_edit,
            (0, 2): old_del,
        }.get((r, c))
        tab.table.rowCount = MagicMock(return_value=1)
        tab.table.columnCount = MagicMock(return_value=3)

        with (
            patch("anki_dictionary.ui.settings.export_templates_tab.miAsk") as ask,
            patch("anki_dictionary.ui.settings.export_templates_tab.save_addon_config"),
            patch("anki_dictionary.ui.settings.export_templates_tab.QPushButton"),
        ):
            ask.return_value = True
            mock_item = MagicMock()
            mock_item.text.return_value = "t1"
            tab.table.item.return_value = mock_item
            tab.removeTemplate(0)

        old_edit.clicked.disconnect.assert_called_once()
        old_del.clicked.disconnect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
