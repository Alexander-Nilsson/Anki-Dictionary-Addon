"""Regression tests for Issue #18: Blank edit/delete buttons in settings on Windows 10.

Tests verify that buttons in settings tables have proper text, sizing, and
tooltips, regardless of platform.  Tests run headless via Qt mocks.
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

from anki_dictionary.ui.settings.dict_groups_tab import (
    DictionaryGroupsTab,
)  # noqa: E402
from anki_dictionary.ui.settings.export_templates_tab import (
    ExportTemplatesTab,
)  # noqa: E402

DGT = "anki_dictionary.ui.settings.dict_groups_tab"
ETT = "anki_dictionary.ui.settings.export_templates_tab"


class TestButtonsCreatedAndSized(unittest.TestCase):
    """Verify that all platform branches create properly sized buttons."""

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

    # ── Button creation ────────────────────────────────────────────────

    def _check_buttons_created(self, tab):
        mod = type(tab).__module__
        with patch(f"{mod}.QPushButton") as mock_btn:
            texts = []
            mock_btn.side_effect = lambda t: (texts.append(t), MagicMock())[-1][1]
            if isinstance(tab, DictionaryGroupsTab):
                tab.loadGroupTable()
            else:
                tab.loadTemplateTable()
            self.assertIn("Edit", texts)
            self.assertIn("X", texts)

    def test_dict_groups_buttons_created(self):
        self._check_buttons_created(
            DictionaryGroupsTab(
                self.mw, self.parent, lambda: self.config, lambda: self.names
            ),
        )

    def test_export_templates_buttons_created(self):
        self._check_buttons_created(
            ExportTemplatesTab(
                self.mw, self.parent, lambda: self.config, lambda: self.names
            ),
        )

    # ── Button sizing (setFixedWidth / setFixedHeight) ─────────────────

    def _check_button_sizing(self, tab, load_method, mod_path, expect_height=True):
        with patch(f"{mod_path}.QPushButton") as mock_btn:
            edit = MagicMock()
            dlt = MagicMock()
            edit_widths = []
            dlt_widths = []
            edit_heights = []
            dlt_heights = []
            edit.setFixedWidth.side_effect = lambda w: edit_widths.append(w)
            dlt.setFixedWidth.side_effect = lambda w: dlt_widths.append(w)
            edit.setFixedHeight.side_effect = lambda h: edit_heights.append(h)
            dlt.setFixedHeight.side_effect = lambda h: dlt_heights.append(h)

            mock_btn.side_effect = lambda t: {"Edit": edit, "X": dlt}.get(
                t, MagicMock()
            )

            load_method()

            # Both buttons must have width >= 40px
            self.assertTrue(
                all(w >= 40 for w in edit_widths),
                f"Edit button widths {edit_widths} below 40",
            )
            self.assertTrue(
                all(w >= 40 for w in dlt_widths),
                f"Delete button widths {dlt_widths} below 40",
            )

            # When expect_height is True, both must have height set
            if expect_height:
                self.assertTrue(
                    len(edit_heights) > 0, "Edit button setFixedHeight not called"
                )
                self.assertTrue(
                    len(dlt_heights) > 0, "Delete button setFixedHeight not called"
                )

    def test_dict_groups_windows_button_sizing(self):
        tab = DictionaryGroupsTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        with (
            patch(f"{DGT}.is_win", True),
            patch(f"{DGT}.is_lin", False),
            patch(f"{DGT}.is_mac", False),
        ):
            self._check_button_sizing(tab, tab.loadGroupTable, DGT, expect_height=False)

    def test_dict_groups_non_windows_button_sizing(self):
        tab = DictionaryGroupsTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        with (
            patch(f"{DGT}.is_win", False),
            patch(f"{DGT}.is_lin", True),
            patch(f"{DGT}.is_mac", False),
        ):
            self._check_button_sizing(tab, tab.loadGroupTable, DGT, expect_height=True)

    def test_export_templates_windows_button_sizing(self):
        tab = ExportTemplatesTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        with (
            patch(f"{ETT}.is_win", True),
            patch(f"{ETT}.is_lin", False),
            patch(f"{ETT}.is_mac", False),
        ):
            self._check_button_sizing(
                tab, tab.loadTemplateTable, ETT, expect_height=False
            )

    # ── Delete button tooltip ──────────────────────────────────────────

    def test_delete_button_has_tooltip(self):
        tab = DictionaryGroupsTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        with patch(f"{DGT}.QPushButton") as mock_btn:
            mock_del = MagicMock()
            mock_btn.side_effect = lambda t: {"Edit": MagicMock(), "X": mock_del}.get(
                t, MagicMock()
            )
            tab.loadGroupTable()
            mock_del.setToolTip.assert_called_once()

    def test_export_delete_button_has_tooltip(self):
        tab = ExportTemplatesTab(
            self.mw, self.parent, lambda: self.config, lambda: self.names
        )
        with patch(f"{ETT}.QPushButton") as mock_btn:
            mock_del = MagicMock()
            mock_btn.side_effect = lambda t: {"Edit": MagicMock(), "X": mock_del}.get(
                t, MagicMock()
            )
            tab.loadTemplateTable()
            mock_del.setToolTip.assert_called_once()


if __name__ == "__main__":
    unittest.main()
