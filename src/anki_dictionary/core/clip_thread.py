import os
import re
import sys
import time
from os.path import join, exists, dirname
from typing import Any, Dict

from aqt.qt import QObject, QSize, Qt
from aqt.qt import pyqtSignal
from anki.utils import is_mac, is_win, is_lin

from ..utils import media_manager
from ..utils.config import get_addon_config
from ..utils.logger import get_logger

log = get_logger("clip_thread")


class ClipThread(QObject):
    sentence = pyqtSignal(str)
    search = pyqtSignal(str)
    colSearch = pyqtSignal(str)
    add = pyqtSignal(str)
    image = pyqtSignal(list)
    test = pyqtSignal(list)
    release = pyqtSignal(list)
    extensionCardExport = pyqtSignal(dict)
    searchFromExtension = pyqtSignal(list)
    extensionFileNotFound = pyqtSignal()
    bulkTextExport = pyqtSignal(list)
    bulkMediaExport = pyqtSignal(dict)
    pageRefreshDuringBulkMediaImport = pyqtSignal()

    def __init__(self, mw: Any, path: str) -> None:
        super().__init__(mw)
        self.mw = mw
        try:
            if is_mac:
                import ssl

                ssl._create_default_https_context = ssl._create_unverified_context  # ty:ignore[invalid-assignment]
                try:
                    from Quartz import (
                        CGEventGetIntegerValueField,  # ty:ignore[unresolved-import]
                        kCGKeyboardEventKeycode,  # ty:ignore[unresolved-import]
                    )

                    self.kCGKeyboardEventKeycode = kCGKeyboardEventKeycode
                    self.CGEventGetIntegerValueField = CGEventGetIntegerValueField
                except ImportError:
                    log.warning("Quartz not available on this system")
                    self.kCGKeyboardEventKeycode = None
                    self.CGEventGetIntegerValueField = None
            elif is_lin:
                pass
            sys.path.insert(0, join(dirname(__file__)))

            try:
                from pynput import keyboard

                self.keyboard = keyboard
            except ImportError:
                log.warning("pynput not available - global hotkeys will not work")
                self.keyboard = None

        except Exception as e:
            log.warning(f"Error initializing ClipThread: {e}")
            self.keyboard = None

        self.addonPath = path
        self.addon_root = dirname(dirname(dirname(dirname(__file__))))
        self.temp_dir = join(self.addon_root, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.config = get_addon_config()

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

    def attemptAddCard(self) -> None:
        self.add.emit("add")

    def checkDict(self) -> bool:
        if not self.mw.ankiDictionary or not self.mw.ankiDictionary.isVisible():
            return False
        return True

    def handleExtensionSearch(self, terms: list) -> None:
        self.searchFromExtension.emit(terms)

    def handleSystemSearch(self) -> None:
        self.search.emit(self.mw.app.clipboard().text())

    def handleColSearch(self) -> None:
        self.colSearch.emit(self.mw.app.clipboard().text())

    def getConfig(self) -> Dict[str, Any]:
        return get_addon_config()

    def handleBulkTextExport(self, cards: list) -> None:
        self.bulkTextExport.emit(cards)

    def handleExtensionCardExport(self, card: dict) -> None:
        config = self.getConfig()
        audioFileName = card["audio"]
        imageFileName = card["image"]
        bulk = card["bulk"]
        media_dir = self.mw.col.media.dir()
        if audioFileName:
            audioTempPath = join(self.temp_dir, audioFileName)
            if not media_manager.wait_for_file(audioTempPath):
                self.extensionFileNotFound.emit()
                return
            media_manager.copy_to_media(audioTempPath, audioFileName, media_dir)
            media_manager.remove_file(audioTempPath)
        if imageFileName:
            imageTempPath = join(self.temp_dir, imageFileName)
            if media_manager.wait_for_file(imageTempPath):
                avif_name = re.sub(r"\.[^.]+$", ".avif", imageFileName)
                media_manager.scale_image(
                    imageTempPath,
                    join(media_dir, avif_name),
                    self.mw.AnkiDictConfig["maxWidth"],
                    self.mw.AnkiDictConfig["maxHeight"],
                )
                media_manager.remove_file(imageTempPath)
        if bulk:
            self.bulkMediaExport.emit(card)
        else:
            self.extensionCardExport.emit(card)

    def handlePageRefreshDuringBulkMediaImport(self) -> None:
        self.pageRefreshDuringBulkMediaImport.emit()

    def handleImageExport(self) -> None:
        if self.checkDict():
            mime = self.mw.app.clipboard().mimeData()
            clip = self.mw.app.clipboard().text()

            if not clip.endswith(".mp3") and mime.hasImage():
                image = mime.imageData()
                filename = media_manager.unique_filename(ext="avif")
                fullpath = join(self.temp_dir, filename)
                maxW = max(self.maxW, image.width())  # ty:ignore[unresolved-attribute]
                maxH = max(self.maxH, image.height())  # ty:ignore[unresolved-attribute]
                image = image.scaled(
                    QSize(maxW, maxH),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image.save(fullpath, "AVIF")
                self.image.emit([fullpath, filename])
            elif clip.endswith(".mp3"):
                if not is_lin:
                    if is_mac:
                        try:
                            clip = str(
                                self.mw.app.clipboard().mimeData().urls()[0].url()
                            )
                        except Exception:
                            return
                    if clip.startswith("file:///") and clip.endswith(".mp3"):
                        try:
                            if is_mac:
                                path = clip.replace("file://", "", 1)
                            else:
                                path = clip.replace("file:///", "", 1)
                            temp, mp3 = media_manager.copy_to_temp(
                                path, self.temp_dir, ext="mp3"
                            )
                            if mp3:
                                self.image.emit([temp, "[sound:" + mp3 + "]", mp3])
                        except Exception:
                            return

    def handleSentenceExport(self) -> None:
        if self.checkDict():
            self.sentence.emit(self.mw.app.clipboard().text())
