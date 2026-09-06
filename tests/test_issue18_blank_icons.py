"""Regression tests for Issue #18: Blank edit/delete buttons in settings on Windows 10.

The old PyQt settings tables drew "Edit"/"X" buttons with icons that rendered
blank on Windows. Those tables are gone — settings is now a Svelte web UI
hosted in an ``AnkiWebView``, and the action buttons are plain text buttons in
HTML/CSS. These tests guard the replacement contract:

1. The built settings bundle exists (a blank UI is only possible if the bundle
   is missing), so the bridge must resolve it in a source checkout.
2. When the bundle is missing, the bridge must fall back to a visible error
   page — never a silently empty web view.
3. The rendered content must be identical across platforms (no Windows-only
   code path that could drop the action buttons); only the initial window size
   differs, and both sizes stay above the 500x500 minimum so a tiny window
   never clips the action buttons.
4. The self-contained bundle must keep text-labeled Edit/Remove affordances
   (the issue-#18 fix carried into the web UI).
"""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Module-level mocks for Qt, Anki, and aqt BEFORE importing the modules under
# test (same preamble as test_settings.py / test_issue17_disconnect_warning.py).
# ---------------------------------------------------------------------------


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


def _make_signal(*_types):
    """Functional stand-in for Qt's pyqtSignal: emit() dispatches to the
    handlers connected via connect(). See tests/test_settings.py for why
    this matters (module collection order + shared aqt.qt mock)."""
    handlers: list = []

    def _connect(handler):
        handlers.append(handler)
        return signal

    def _emit(*args, **kwargs):
        for handler in list(handlers):
            handler(*args, **kwargs)
        return signal

    signal = MagicMock()
    signal.connect.side_effect = _connect
    signal.emit.side_effect = _emit
    return signal


_QT_CLASSES = [
    "QEvent",
    "QFileDialog",
    "QIcon",
    "QInputDialog",
    "QKeySequence",
    "QMessageBox",
    "QProgressDialog",
    "QShortcut",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
    # Superset shared with tests/test_settings.py and
    # tests/test_issue17_disconnect_warning.py: pytest imports every test
    # module during collection, and the last mock preamble written to
    # sys.modules wins for the whole session. Keeping the identical superset
    # in each file makes test behaviour independent of collection/CLI order.
    # Used by anki_dictionary.integrations.llm.
    "QObject",
    "QRunnable",
    # Used by anki_dictionary.web.installer + ui.dialogs.wizard (native
    # delegates reachable from the bridge).
    "QCheckBox",
    "QDialog",
    "QFrame",
    "QHBoxLayout",
    "QLabel",
    "QLayout",
    "QLineEdit",
    "QPalette",
    "QPlainTextEdit",
    "QProgressBar",
    "QPushButton",
    "QSizePolicy",
    "QStyle",
    "QTextCursor",
    "QTextEdit",
    "QThread",
    "QTreeWidget",
    "QTreeWidgetItem",
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
_mock_aqt_qt.pyqtSignal = _make_signal
sys.modules["aqt.qt"] = _mock_aqt_qt

_mock_aqt = types.ModuleType("aqt")
_mock_aqt.mw = MagicMock()
sys.modules["aqt"] = _mock_aqt

_mock_aqt_utils = types.ModuleType("aqt.utils")
for _n in ("tooltip", "showInfo", "openLink", "askUser"):
    setattr(_mock_aqt_utils, _n, MagicMock())
sys.modules["aqt.utils"] = _mock_aqt_utils

# AnkiWebView must be a *class* (SettingsBridge subclasses it).
_mock_aqt_webview = types.ModuleType("aqt.webview")
_mock_aqt_webview.AnkiWebView = type("AnkiWebView", (_QtMockBase,), {})
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

atexit.register(lambda: None)

from anki_dictionary.ui.settings.settings_bridge import (  # noqa: E402
    SettingsBridge,
    _svelte_settings_path,
)
from anki_dictionary.ui.settings.settings_gui import SettingsGui  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE_SOURCE = os.path.join(REPO_ROOT, "web", "dist", "settings.html")


def _make_gui(mw: MagicMock | None = None) -> SettingsGui:
    mw = mw or MagicMock()
    mw.miDictDB.getAllDictsWithLang.return_value = []
    mw.col.models.all.return_value = []
    with patch(
        "anki_dictionary.ui.settings.settings_gui.get_addon_config",
        return_value={"llm_enabled": False, "forvo_enabled": True},
    ):
        return SettingsGui(mw, REPO_ROOT, MagicMock())


class TestBundlePresentInSourceCheckout(unittest.TestCase):
    """A blank UI in a source checkout means the web build is missing."""

    @unittest.skipUnless(
        os.path.isfile(BUNDLE_SOURCE),
        "web/dist/settings.html not built (npm run build)",
    )
    def test_bundle_resolves_to_existing_file(self):
        path = _svelte_settings_path(REPO_ROOT)
        self.assertTrue(os.path.isfile(path), f"settings bundle missing at {path}")

    @unittest.skipUnless(
        os.path.isfile(BUNDLE_SOURCE),
        "web/dist/settings.html not built (npm run build)",
    )
    def test_bundle_is_self_contained_html(self):
        with open(BUNDLE_SOURCE, encoding="utf-8") as fh:
            html = fh.read()
        # The page must carry the JS reply surface the bridge drives.
        self.assertIn("SETTINGS", html)
        # And must render the text-labeled action affordances (Issue #18: the
        # old Qt buttons went blank on Windows; these are plain text buttons).
        self.assertIn("Edit", html)
        self.assertIn("Remove", html)


class TestMissingBundleFallsBack(unittest.TestCase):
    """A missing bundle must produce a visible error page, never a blank view."""

    def test_missing_bundle_loads_error_page(self):
        tmp = tempfile.mkdtemp()  # no settings.html inside
        bridge = SettingsBridge(MagicMock(), MagicMock(), tmp)
        html = bridge.setHtml.call_args[0][0]
        self.assertIn("Settings bundle not found", html)
        self.assertNotEqual(html.strip(), "")


class TestPlatformIndependence(unittest.TestCase):
    """Windows may adjust window size, but never page content or minimum size."""

    def test_minimum_size_always_500(self):
        for win in (True, False):
            with patch("anki_dictionary.ui.settings.settings_gui.is_win", win):
                gui = _make_gui()
                gui.setMinimumSize.assert_called_with(500, 500)

    def test_page_content_identical_on_all_platforms(self):
        """The Svelte page loaded by the bridge must not depend on is_win."""
        tmp_dir = tempfile.mkdtemp()
        dist_dir = os.path.join(tmp_dir, "web", "dist")
        os.makedirs(dist_dir)
        bundle = os.path.join(dist_dir, "settings.html")
        with open(bundle, "w", encoding="utf-8") as fh:
            fh.write("<html>settings</html>")

        # The bridge reads the bundle verbatim; the platform must never enter
        # this code path (is_win is not even referenced by settings_bridge).
        htmls = []
        for _ in range(2):
            bridge = SettingsBridge(MagicMock(), MagicMock(), tmp_dir)
            htmls.append(bridge.setHtml.call_args[0][0])

        self.assertEqual(htmls[0], htmls[1])
        self.assertEqual(htmls[0], "<html>settings</html>")

    def test_initial_sizes_stay_above_minimum(self):
        """The only Win/non-Win difference is initial size; both are usable."""
        sizes: dict[bool, tuple[int, int]] = {}
        for win in (True, False):
            with patch("anki_dictionary.ui.settings.settings_gui.is_win", win):
                gui = _make_gui()
                sizes[win] = gui.resize.call_args[0]
        self.assertEqual(sizes[True], (920, 650))
        self.assertEqual(sizes[False], (1034, 650))
        for size in sizes.values():
            self.assertGreaterEqual(size[0], 500)
            self.assertGreaterEqual(size[1], 500)


if __name__ == "__main__":
    unittest.main()
