"""Regression tests for Issue #66: addon swallowed the whole keyboard.

On Windows, ``ClipThread.run`` started ``pynput.keyboard.Listener`` with
``suppress=True``. pynput's win32 backend turns that into a low-level
keyboard hook that returns 1 for *every* key event, so no application —
including Anki — receives any keystrokes while the addon is loaded.

The global key listener serves no Windows/Linux feature: the in-app
shortcuts (Ctrl+W / Ctrl+S / Ctrl+Shift+B) are plain Qt ``QAction``
shortcuts in ``hooks.py``, and the ``currentlyPressed`` key log the
listener feeds is only read by macOS's Cmd+C intercept. So the listener
must only exist on macOS — and it must never suppress events.
"""

from __future__ import annotations

import atexit
import sys
import types
import unittest
from contextlib import contextmanager
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


# Same preamble as tests/test_settings.py and
# tests/test_issue17_disconnect_warning.py (see there for why the superset
# must stay identical), plus QTimer for the clipboard poller.
_QT_CLASSES = [
    "QColor",
    "QEvent",
    "QFileDialog",
    "QIcon",
    "QInputDialog",
    "QKeySequence",
    "QMessageBox",
    "QObject",
    "QProgressDialog",
    "QRunnable",
    "QShortcut",
    "QTimer",
    "QUrl",
    "QVBoxLayout",
    "QWidget",
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

_mock_aqt_webview = types.ModuleType("aqt.webview")
_mock_aqt_webview.AnkiWebView = type("AnkiWebView", (_QtMockBase,), {})
sys.modules["aqt.webview"] = _mock_aqt_webview

# Platform flags are patched per-test; Linux here matches the repo default.
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

import anki_dictionary.core.clip_thread as clip_thread  # noqa: E402


@contextmanager
def _platform(name: str):
    """Force one platform for construction *and* ``run()``."""
    with patch.object(clip_thread, "is_mac", name == "mac"):
        yield


def _clip() -> clip_thread.ClipThread:
    """Build a ClipThread with pynput faked."""
    fake_keyboard = MagicMock()
    with patch.dict(
        sys.modules, {"pynput": MagicMock(), "pynput.keyboard": fake_keyboard}
    ):
        with patch("pynput.keyboard", fake_keyboard, create=True):
            return clip_thread.ClipThread(MagicMock(), "/tmp")


class TestIssue66KeyboardNotSuppressed(unittest.TestCase):
    def test_windows_starts_no_global_key_listener(self):
        with _platform("win"):
            thread = _clip()
            thread.run()
        thread.keyboard.Listener.assert_not_called()

    def test_linux_starts_no_global_key_listener(self):
        with _platform("lin"):
            thread = _clip()
            thread.run()
        thread.keyboard.Listener.assert_not_called()

    def test_macos_listens_but_never_suppresses(self):
        with _platform("mac"):
            thread = _clip()
            thread.run()
        thread.keyboard.Listener.assert_called_once()
        _, kwargs = thread.keyboard.Listener.call_args
        self.assertNotIn("suppress", kwargs)
        self.assertNotIn("dict", kwargs)

    def test_clipboard_polling_starts_on_every_platform(self):
        for platform in ("win", "lin", "mac"):
            with self.subTest(platform=platform):
                with _platform(platform):
                    thread = _clip()
                    thread.run()
                thread._clip_timer.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
