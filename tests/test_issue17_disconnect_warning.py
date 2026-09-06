"""Regression tests for Issue #17: Qt disconnect warnings on Windows 10.

The old settings tables disconnected cell-widget signals before clearing them,
and a missed disconnect produced noisy Qt warnings at runtime. That PyQt table
UI is gone — the settings UI is now a web view. These tests guard the
replacement teardown contract: closing/hiding the web settings window must
cleanly release the window reference (the analog of a disconnect-on-close
crash), and every bridge command the web page can send must be routed to a
handler so the JS<->Python protocol never silently drops updates.
"""

from __future__ import annotations

import atexit
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


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
    handlers connected via connect(). See tests/test_settings.py for why this
    matters (module collection order + shared aqt.qt mock)."""
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
    # tests/test_issue18_blank_icons.py: pytest imports every test module
    # during collection, and the last mock preamble written to sys.modules
    # wins for the whole session. Keeping the identical superset in each file
    # makes test behaviour independent of collection/CLI order.
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

from anki_dictionary.ui.settings.settings_bridge import SettingsBridge  # noqa: E402
from anki_dictionary.ui.settings.settings_gui import SettingsGui  # noqa: E402


def _make_gui():
    mw = MagicMock()
    mw.miDictDB.getAllDictsWithLang.return_value = []
    mw.col.models.all.return_value = []
    with patch(
        "anki_dictionary.ui.settings.settings_gui.get_addon_config",
        return_value={"llm_enabled": False, "forvo_enabled": True},
    ):
        gui = SettingsGui(mw, "/tmp", MagicMock())
    return gui, mw


class TestSettingsWindowTeardown(unittest.TestCase):
    """Closing/hiding the web settings window must release it cleanly."""

    def test_close_clears_window_reference(self):
        gui, mw = _make_gui()
        event = MagicMock()

        gui.closeEvent(event)

        self.assertIsNone(mw.dictSettings)
        event.accept.assert_called_once()

    def test_hide_clears_window_reference(self):
        gui, mw = _make_gui()
        event = MagicMock()

        gui.hideEvent(event)

        self.assertIsNone(mw.dictSettings)
        event.accept.assert_called_once()


class TestBridgeRoutesEveryCommand(unittest.TestCase):
    """Every command the JS page can send has a Python handler (no dropped
    updates — the analog of the old unbounded signal wiring)."""

    # settings:save / settings:testLLM / settings:deleteWordList /
    # settings:removeLanguage carry payloads; test them with a JSON payload.
    PAYLOAD_CMDS = {
        "settings:save:{}",
        "settings:testLLM:{}",
        'settings:deleteWordList:"f.json"',
        'settings:removeLanguage:"ja"',
    }

    def _bridge(self):
        mw = MagicMock()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui = MagicMock()
        gui.config = {"llm_enabled": False, "forvo_enabled": True}
        bridge = SettingsBridge(gui, mw, "/tmp")
        bridge._push = MagicMock()
        return bridge, gui, mw

    def test_known_commands_are_all_handled(self):
        bridge, gui, mw = self._bridge()
        plain_cmds = [
            "settingsLoaded",
            "settings:getConfig",
            "settings:getDictionaryNames",
            "settings:getWordListData",
            "settings:getNoteTypes",
            "settings:getLanguagesDicts",
            "settings:getForvoLanguages",
            "settings:restoreDefaults",
            "settings:close",
            "settings:webInstallDicts",
            "settings:importDicts",
            "settings:webInstallFreq",
            "settings:importFreq",
            "settings:browseFontFile",
        ]
        with (
            patch("anki_dictionary.ui.settings.settings_bridge.save_addon_config"),
            patch.object(gui, "after_save"),
        ):
            for cmd in plain_cmds + sorted(self.PAYLOAD_CMDS):
                bridge._push.reset_mock()
                gui.reset_mock()
                bridge.handleSettingsAction(cmd)

                if cmd == "settingsLoaded":
                    # Intentional handshake no-op: must not emit replies.
                    bridge._push.assert_not_called()
                    continue

                # A handler ran for this command: a JS reply was pushed, a GUI
                # native delegate fired, or (testLLM) the background taskman
                # picked up the blocking HTTP test.
                handled = (
                    bridge._push.call_count > 0
                    or any(c[0] != "reset" for c in gui.mock_calls)
                    or mw.taskman.run_in_background.called
                )
                self.assertTrue(handled, f"no handler observed for {cmd}")

    def test_unknown_command_does_not_crash(self):
        bridge, _, _ = self._bridge()
        bridge.handleSettingsAction("settings:doesNotExist")
        bridge._push.assert_not_called()

    def test_delegate_with_missing_method_does_not_crash(self):
        # A future command could reference a native method that the shell no
        # longer provides — the bridge must degrade gracefully, not raise.
        bridge, gui, _ = self._bridge()
        del gui.web_install_dicts
        bridge.handleSettingsAction("settings:webInstallDicts")
        bridge._push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
