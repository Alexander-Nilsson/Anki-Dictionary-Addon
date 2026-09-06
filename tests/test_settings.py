from __future__ import annotations

import atexit
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

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
    class-level attribute access (e.g. ``Qt.WindowType.Window``)."""

    def __getattr__(cls, name: str):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return MagicMock()


class _QtMockBase(metaclass=_QtMockMeta):
    """Base for every mock Qt widget/object.

    ``__init__`` swallows all arguments so that any Qt parent/flags
    arguments never reach Mock's setting machinery.
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


def _make_signal(*_types):
    """A functional stand-in for Qt's pyqtSignal.

    ``emit`` dispatches synchronously to every ``connect``-ed handler,
    matching the behaviour real ``test_llm`` tests rely on. This matters
    because pytest imports every test module during collection and the last
    module-level mock preamble written to ``sys.modules['aqt.qt']`` wins for
    the whole session: if ``pyqtSignal`` were a plain no-op MagicMock, the
    ``LLMWorker`` signal emissions in tests/test_llm.py would silently drop
    their connected handlers and those tests would fail depending on file
    collection order.
    """
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
    # Used by anki_dictionary.integrations.llm (imported lazily by the bridge).
    "QObject",
    "QRunnable",
    # Used by anki_dictionary.web.installer + ui.dialogs.wizard (imported
    # lazily by native delegates like web_install_dicts).
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
_mock_aqt_qt.pyqtSignal = _make_signal
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

# -- aqt.webview -- AnkiWebView must be a *class* so SettingsBridge can
# subclass it (a MagicMock instance cannot be inherited from).
_mock_aqt_webview = types.ModuleType("aqt.webview")
_mock_aqt_webview.AnkiWebView = type("AnkiWebView", (_QtMockBase,), {})
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
from anki_dictionary.ui.settings.settings_bridge import SettingsBridge  # noqa: E402
from anki_dictionary.ui.settings.settings_gui import SettingsGui  # noqa: E402

_BASE_CONFIG: dict = {
    "DictionaryGroups": {},
    "ExportTemplates": {},
    "maxSearch": 1000,
    "dictSearch": 50,
    "highlightTarget": True,
    "showTarget": False,
    "tooltips": True,
    "dictAlwaysOnTop": False,
    "llm_enabled": False,
    "forvo_enabled": True,
    "forvo_language": "ja",
    "frontBracket": "【",
    "backBracket": "】",
}


def _make_mw() -> MagicMock:
    mw = MagicMock()
    mw.miDictDB.getAllDictsWithLang.return_value = []
    mw.col.models.all.return_value = []
    return mw


def _make_gui(mw: MagicMock | None = None, config: dict | None = None) -> SettingsGui:
    mw = mw or _make_mw()
    if config is not None:
        mw.miDictDB.getAllDictsWithLang.return_value = []
    with patch(
        "anki_dictionary.ui.settings.settings_gui.get_addon_config",
        return_value=config if config is not None else _BASE_CONFIG,
    ):
        gui = SettingsGui(mw, "/tmp", MagicMock())
    # Spy on the bridge's real _push method so GUI tests can assert replies.
    gui._bridge._push = MagicMock()
    return gui


def _make_bridge(settings_gui: MagicMock | None = None, mw: MagicMock | None = None):
    """Build a SettingsBridge with a stub settings_gui (no Qt window)."""
    gui = settings_gui or MagicMock()
    if not isinstance(gui, MagicMock):
        gui = MagicMock()
    gui.config = dict(_BASE_CONFIG)
    mw = mw or _make_mw()
    bridge = SettingsBridge(gui, mw, "/tmp")
    bridge._push = MagicMock()  # spy on replies
    return bridge, gui, mw


# ===================================================================
# SettingsGui — the Qt shell
# ===================================================================
class TestSettingsGuiShell(unittest.TestCase):
    def test_init_loads_config_and_creates_bridge(self):
        gui = _make_gui()
        self.assertEqual(gui.config["maxSearch"], 1000)
        self.assertIsInstance(gui._bridge, SettingsBridge)
        gui._bridge.setHtml.assert_called()  # web page loaded

    def test_init_sets_window_chrome(self):
        gui = _make_gui()
        gui.setMinimumSize.assert_called_with(500, 500)
        gui.setWindowTitle.assert_called_once()
        gui.setContextMenuPolicy.assert_called_once()
        # Non-Windows default size (is_win is False in the mock env).
        gui.resize.assert_called_with(1034, 650)

    def test_close_clears_mw_dict_settings(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        event = MagicMock()
        gui.closeEvent(event)
        mw.dictSettings = None
        event.accept.assert_called_once()

    def test_hide_clears_mw_dict_settings(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        event = MagicMock()
        gui.hideEvent(event)
        mw.dictSettings = None
        event.accept.assert_called_once()

    def test_after_save_pushes_derived_data(self):
        mw = _make_mw()
        mw.miDictDB.getAllDictsWithLang.return_value = [{"dict": "l1nameEnglish"}]
        mw.miDictDB.cleanDictName.side_effect = lambda n: n.replace("l1name", "")
        gui = _make_gui(mw)

        gui.after_save()

        gui._bridge._push.assert_called()
        names = [
            c.args[1]
            for c in gui._bridge._push.call_args_list
            if c.args[0] == "setDictionaryNames"
        ][0]
        self.assertIn("English", names)
        self.assertIn("Images", names)

    def test_browse_font_file_pushes_selected_path(self):
        gui = _make_gui()
        with patch("anki_dictionary.ui.settings.settings_gui.QFileDialog") as qfd:
            qfd.getOpenFileName.return_value = ("/fonts/Custom.ttf", "")
            gui.browse_font_file()
            gui._bridge._push.assert_called_with("setFontFile", "/fonts/Custom.ttf")

    def test_browse_font_file_cancelled_pushes_nothing(self):
        gui = _make_gui()
        with patch("anki_dictionary.ui.settings.settings_gui.QFileDialog") as qfd:
            qfd.getOpenFileName.return_value = ("", "")
            gui.browse_font_file()
            gui._bridge._push.assert_not_called()

    def test_remove_language_confirmed(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        wl_dir = tempfile.mkdtemp()
        with open(os.path.join(wl_dir, "English_freq.json"), "w") as f:
            f.write("{}")
        with (
            patch("anki_dictionary.ui.settings.settings_gui.QMessageBox") as qmb,
            patch(
                "anki_dictionary.ui.settings.settings_gui.get_word_lists_dir",
                return_value=wl_dir,
            ),
            patch(
                "anki_dictionary.ui.settings.settings_gui.get_db_dir",
                return_value=tempfile.mkdtemp(),
            ),
        ):
            dlg = MagicMock()
            qmb.StandardButton.Yes = 1
            qmb.StandardButton.No = 2
            dlg.exec.return_value = qmb.StandardButton.Yes
            qmb.side_effect = lambda *a, **k: dlg

            gui.remove_language("English")

            mw.miDictDB.deleteLanguage.assert_called_once_with("English")
            self.assertFalse(os.path.isfile(os.path.join(wl_dir, "English_freq.json")))

    def test_remove_language_cancelled(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        with (
            patch("anki_dictionary.ui.settings.settings_gui.QMessageBox") as qmb,
            patch("anki_dictionary.ui.settings.settings_gui.get_word_lists_dir"),
        ):
            dlg = MagicMock()
            dlg.exec.return_value = 2
            qmb.StandardButton.Yes = 1
            qmb.side_effect = lambda *a, **k: dlg

            gui.remove_language("English")

            mw.miDictDB.deleteLanguage.assert_not_called()

    def test_select_language_uses_existing_languages(self):
        mw = _make_mw()
        mw.miDictDB.getCurrentDbLangs.return_value = ["English", "Japanese"]
        gui = _make_gui(mw)
        with patch("anki_dictionary.ui.settings.settings_gui.QInputDialog") as qid:
            qid.getItem.return_value = ("Japanese", True)
            self.assertEqual(gui._select_language(), "Japanese")

    def test_select_language_prompts_when_no_languages(self):
        mw = _make_mw()
        mw.miDictDB.getCurrentDbLangs.return_value = []
        gui = _make_gui(mw)
        with patch("anki_dictionary.ui.settings.settings_gui.QInputDialog") as qid:
            qid.getText.return_value = ("German", True)
            self.assertEqual(gui._select_language(), "German")

    def test_web_install_dicts_runs_wizard_and_refreshes(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        with (
            patch("anki_dictionary.web.installer.DictionaryWebInstallWizard") as wizard,
            patch.object(gui, "_after_native_change") as refresh,
        ):
            gui.web_install_dicts()
            wizard.execute_modal.assert_called_once()
            refresh.assert_called_once()

    def test_import_freq_copies_file_and_refreshes(self):
        mw = _make_mw()
        gui = _make_gui(mw)
        src_dir = tempfile.mkdtemp()
        src = os.path.join(src_dir, "English_freq.json")
        with open(src, "w") as f:
            json.dump({"term": 1}, f)
        with (
            patch("anki_dictionary.ui.settings.settings_gui.get_word_lists_dir") as wld,
            patch("anki_dictionary.ui.settings.settings_gui.QFileDialog") as qfd,
            patch.object(gui, "_select_language", return_value="English"),
            patch.object(gui, "_after_native_change") as refresh,
            patch("anki_dictionary.ui.settings.settings_gui.QMessageBox"),
        ):
            wld.return_value = tempfile.mkdtemp()
            qfd.getOpenFileName.return_value = (src, "")
            gui.import_freq()
            refresh.assert_called_once()
            target = os.path.join(wld.return_value, "English_freq.json")
            self.assertTrue(os.path.isfile(target))


# ===================================================================
# SettingsBridge — the pycmd<->eval command protocol
# ===================================================================
class TestSettingsBridge(unittest.TestCase):
    def test_settingsLoaded_is_noop(self):
        bridge, _, _ = _make_bridge()
        bridge.handleSettingsAction("settingsLoaded")
        bridge._push.assert_not_called()

    def test_getConfig_pushes_staged_config(self):
        bridge, gui, _ = _make_bridge()
        gui.config = {"key": "value", "maxSearch": 500}
        bridge.handleSettingsAction("settings:getConfig")
        bridge._push.assert_called_with("setConfig", {"key": "value", "maxSearch": 500})

    def test_save_persists_config_and_refreshes(self):
        bridge, gui, mw = _make_bridge()
        payload = {"maxSearch": 123, "frontBracket": "["}
        with (
            patch(
                "anki_dictionary.ui.settings.settings_bridge.save_addon_config",
                return_value=True,
            ) as save,
            patch.object(gui, "after_save") as after_save,
        ):
            bridge.handleSettingsAction("settings:save:" + json.dumps(payload))

            save.assert_called_once_with(payload)
            self.assertEqual(gui.config, payload)
            after_save.assert_called_once()
            mw.refreshAnkiDictConfig.assert_called_with(payload)
        bridge._push.assert_called_with("setSaved", True)

    def test_save_invalid_json_does_not_crash(self):
        bridge, gui, _ = _make_bridge()
        with (
            patch(
                "anki_dictionary.ui.settings.settings_bridge.save_addon_config"
            ) as save,
            patch.object(gui, "after_save") as after_save,
        ):
            bridge.handleSettingsAction("settings:save:not-json{")
            save.assert_not_called()
            after_save.assert_not_called()
        bridge._push.assert_called_with("setSaved", True)

    def test_getDictionaryNames_includes_images_llm_forvo(self):
        bridge, gui, mw = _make_bridge()
        mw.miDictDB.getAllDictsWithLang.return_value = [
            {"dict": "l1nameEnglish"},
            {"dict": "l2nameFrench"},
        ]
        mw.miDictDB.cleanDictName.side_effect = lambda n: n.replace(
            "l1name", ""
        ).replace("l2name", "")
        gui.config = {"llm_enabled": True, "forvo_enabled": True}

        bridge.handleSettingsAction("settings:getDictionaryNames")

        names = bridge._push.call_args[0][1]
        self.assertEqual(
            names,
            sorted(["English", "French", "Images", "LLM", "Forvo"], key=str.casefold),
        )

    def test_getDictionaryNames_skips_disabled_providers(self):
        bridge, gui, mw = _make_bridge()
        mw.miDictDB.getAllDictsWithLang.return_value = []
        gui.config = {"llm_enabled": False, "forvo_enabled": False}

        bridge.handleSettingsAction("settings:getDictionaryNames")

        names = bridge._push.call_args[0][1]
        self.assertEqual(names, ["Images"])

    def test_getNoteTypes(self):
        bridge, _, mw = _make_bridge()
        mw.col.models.all.return_value = [
            {"name": "Basic", "flds": [{"name": "Front"}, {"name": "Back"}]}
        ]
        bridge.handleSettingsAction("settings:getNoteTypes")
        bridge._push.assert_called_with("setNoteTypes", {"Basic": ["Front", "Back"]})

    def test_getLanguagesDicts(self):
        bridge, _, mw = _make_bridge()
        mw.miDictDB.getAllDictsWithLang.return_value = [
            {"dict": "l1nameEnglish", "lang": "English"},
            {"dict": "l2nameFrench", "lang": "French"},
        ]
        mw.miDictDB.cleanDictName.side_effect = lambda n: n.replace(
            "l1name", ""
        ).replace("l2name", "")
        bridge.handleSettingsAction("settings:getLanguagesDicts")
        bridge._push.assert_called_with(
            "setLanguagesDicts", {"English": ["English"], "French": ["French"]}
        )

    def test_getWordListData_groups_files(self):
        bridge, _, mw = _make_bridge()
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "English_freq.json"), "w") as f:
            json.dump({"term": [[1, 2]]}, f)
        with patch(
            "anki_dictionary.ui.settings.settings_bridge.get_word_lists_dir",
            return_value=tmp,
        ):
            bridge.handleSettingsAction("settings:getWordListData")
        payload = bridge._push.call_args[0][1]
        self.assertEqual(payload["files"][0]["lang"], "English")
        self.assertEqual(payload["files"][0]["files"][0]["name"], "English_freq.json")
        self.assertIsInstance(payload["providers"], list)

    def test_deleteWordList_removes_file_and_refreshes(self):
        bridge, _, mw = _make_bridge()
        tmp = tempfile.mkdtemp()
        target = os.path.join(tmp, "English_freq.json")
        with open(target, "w") as f:
            f.write("{}")
        with (
            patch(
                "anki_dictionary.ui.settings.settings_bridge.get_word_lists_dir",
                return_value=tmp,
            ),
            patch.object(bridge, "_word_list_data", return_value={"files": []}),
        ):
            bridge.handleSettingsAction(
                "settings:deleteWordList:" + json.dumps("English_freq.json")
            )
        self.assertFalse(os.path.isfile(target))
        bridge._push.assert_called_with("setWordListData", {"files": []})

    def test_restoreDefaults_saves_defaults_and_pushes(self):
        bridge, gui, mw = _make_bridge()
        with (
            patch(
                "anki_dictionary.ui.settings.settings_bridge.save_addon_config"
            ) as save,
            patch.object(gui, "after_save") as after_save,
        ):
            from aqt import mw as aqt_mw

            aqt_mw.addonManager.addonConfigDefaults.return_value = {"defaults": True}
            bridge.handleSettingsAction("settings:restoreDefaults")

            save.assert_called_once_with({"defaults": True})
            self.assertEqual(gui.config, {"defaults": True})
            after_save.assert_called_once()
        bridge._push.assert_called_with("setConfig", {"defaults": True})

    def test_removeLanguage_delegates_and_refreshes(self):
        bridge, gui, _ = _make_bridge()
        with patch.object(bridge, "_languages_dicts", return_value={"English": []}):
            bridge.handleSettingsAction(
                "settings:removeLanguage:" + json.dumps("Japanese")
            )
            gui.remove_language.assert_called_once_with("Japanese")
        bridge._push.assert_called_with("setLanguagesDicts", {"English": []})

    def test_close_delegates_to_gui(self):
        bridge, gui, _ = _make_bridge()
        bridge.handleSettingsAction("settings:close")
        gui.close.assert_called_once()

    def test_testLLM_runs_in_background(self):
        bridge, _, mw = _make_bridge()
        config = {"llm_api_key": "k", "llm_base_url": "http://x", "llm_model": "m"}
        bridge.handleSettingsAction("settings:testLLM:" + json.dumps(config))

        mw.taskman.run_in_background.assert_called_once()
        run_fn, done_fn = mw.taskman.run_in_background.call_args[0]
        self.assertTrue(callable(run_fn))
        self.assertTrue(callable(done_fn))

        # Simulate task completion: on_done must push the result to the UI.
        future = MagicMock()
        future.result.return_value = {"success": True, "message": "OK"}
        done_fn(future)
        bridge._push.assert_called_with(
            "setLLMTest", {"success": True, "message": "OK"}
        )

    def test_native_delegate_routes_to_settings_gui(self):
        bridge, gui, _ = _make_bridge()
        for cmd, attr in [
            ("settings:webInstallDicts", "web_install_dicts"),
            ("settings:importDicts", "import_dicts"),
            ("settings:webInstallFreq", "web_install_freq"),
            ("settings:importFreq", "import_freq"),
            ("settings:browseFontFile", "browse_font_file"),
        ]:
            getattr(gui, attr).reset_mock()
            bridge.handleSettingsAction(cmd)
            getattr(gui, attr).assert_called_once()

    def test_unknown_command_is_ignored(self):
        bridge, _, _ = _make_bridge()
        bridge.handleSettingsAction("settings:notACommand")
        bridge._push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
