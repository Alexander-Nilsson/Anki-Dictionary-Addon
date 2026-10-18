"""Global hotkey listener.

The addon no longer ships an external browser-extension transport. This module
keeps the one global shortcut that is actually wired end-to-end: on macOS,
Cmd+C outside Anki searches the selected clipboard text in the dictionary.
The regular Windows/Linux paths use Anki's own application shortcuts
(Ctrl+S / Ctrl+Shift+B).
"""

from typing import Any

from anki.utils import is_lin, is_mac, is_win
from aqt.qt import QObject, QTimer, pyqtSignal

from ..utils.logger import get_logger

log = get_logger("clip_thread")


class ClipThread(QObject):
    search = pyqtSignal(str)
    test = pyqtSignal(list)
    release = pyqtSignal(list)

    def __init__(self, mw: Any, path: str) -> None:
        super().__init__(mw)
        self.mw = mw
        self.addonPath = path
        try:
            if is_mac:
                try:
                    from Quartz import (
                        CGEventGetIntegerValueField,
                        kCGKeyboardEventKeycode,
                    )

                    self.kCGKeyboardEventKeycode = kCGKeyboardEventKeycode
                    self.CGEventGetIntegerValueField = CGEventGetIntegerValueField
                except ImportError:
                    log.warning("Quartz not available on this system")
                    self.kCGKeyboardEventKeycode = None
                    self.CGEventGetIntegerValueField = None
            elif is_lin:
                pass

            try:
                from pynput import keyboard

                self.keyboard = keyboard
            except ImportError:
                log.warning("pynput not available - global hotkeys will not work")
                self.keyboard = None

        except Exception as e:
            log.warning(f"Error initializing ClipThread: {e}")
            self.keyboard = None

        self._last_clipboard = ""
        self._clip_timer = QTimer(self)
        self._clip_timer.setInterval(800)
        self._clip_timer.timeout.connect(self.poll_clipboard)

    def poll_clipboard(self) -> None:
        """Search words copied while the dictionary is visible.

        Long selections and multi-line text are ignored: they are sentences,
        not headwords, and turning every copy into a lookup would make the
        monitor unusable. The in-web pause pill disables this path.
        """
        dictionary = getattr(self.mw, "ankiDictionary", None)
        if not dictionary or not dictionary.isVisible():
            return
        config = getattr(self.mw, "AnkiDictConfig", {}) or {}
        if not config.get("clipboard_monitor_enabled", True):
            return
        try:
            text = self.mw.app.clipboard().text().strip()
        except Exception:
            return
        if self.mw.__dict__.pop("_anki_dict_suppress_clipboard", False):
            self._last_clipboard = text
            return
        if not text or text == self._last_clipboard or len(text) > 60 or "\n" in text:
            return
        self._last_clipboard = text
        self.search.emit(text)

    def on_press(self, key: Any) -> None:
        self.test.emit([key])

    def on_release(self, key: Any) -> bool:
        self.release.emit([key])
        return True

    def darwinIntercept(self, event_type: Any, event: Any) -> Any:
        if not self.CGEventGetIntegerValueField or not self.kCGKeyboardEventKeycode:
            return event
        keycode = self.CGEventGetIntegerValueField(event, self.kCGKeyboardEventKeycode)
        if (
            (
                "Key.cmd" in self.mw.currentlyPressed
                or "Key.cmd_r" in self.mw.currentlyPressed
            )
            and "'c'" in self.mw.currentlyPressed
            and keycode == 1
        ):
            self.handleSystemSearch()
            self.mw.currentlyPressed = []
            return None
        return event

    def run(self) -> None:
        # Clipboard polling is independent of pynput; keep it working even
        # when the global key listener cannot start.
        self._clip_timer.start()

        if not self.keyboard:
            log.warning("Keyboard monitoring not available - skipping hotkey setup")
            return

        try:
            if is_win:
                self.listener = self.keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release,
                    dict=self.mw,
                    suppress=True,
                )
            elif is_mac:
                self.listener = self.keyboard.Listener(
                    on_press=self.on_press,
                    on_release=self.on_release,
                    dict=self.mw,
                    darwin_intercept=self.darwinIntercept,
                )
            else:
                self.listener = self.keyboard.Listener(
                    on_press=self.on_press, on_release=self.on_release
                )
            self.listener.start()
        except Exception as e:
            log.warning(f"Could not start keyboard listener: {e}")

    def handleSystemSearch(self) -> None:
        text = self.mw.app.clipboard().text()
        self._last_clipboard = text.strip()
        self.search.emit(text)

    def stop(self) -> None:
        """Stop polling and the pynput listener (profile unload)."""
        self._clip_timer.stop()
        listener = getattr(self, "listener", None)
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                log.debug("Could not stop hotkey listener", exc_info=True)
