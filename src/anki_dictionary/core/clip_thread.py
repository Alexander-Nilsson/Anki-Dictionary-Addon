import os
import re
import sys
import time
from os.path import join, exists, dirname
from shutil import copyfile
from typing import Any, Dict, Tuple

from aqt.qt import QImage, QObject, QSize, Qt
from aqt.qt import pyqtSignal
from anki.utils import is_mac, is_win, is_lin

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
        try:
            if is_mac:
                import ssl

                ssl._create_default_https_context = ssl._create_unverified_context
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
                "Key.cmd" in self.mw.currentlyPressed  # ty:ignore[unresolved-attribute]
                or "Key.cmd_r" in self.mw.currentlyPressed  # ty:ignore[unresolved-attribute]
            )
            and "'c'" in self.mw.currentlyPressed  # ty:ignore[unresolved-attribute]
            and keycode == 1
        ):
            self.handleSystemSearch()
            self.mw.currentlyPressed = []  # ty:ignore[unresolved-attribute]
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
        if not self.mw.ankiDictionary or not self.mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
            return False
        return True

    def handleExtensionSearch(self, terms: list) -> None:
        self.searchFromExtension.emit(terms)

    def handleSystemSearch(self) -> None:
        self.search.emit(self.mw.app.clipboard().text())  # ty:ignore[unresolved-attribute]

    def handleColSearch(self) -> None:
        self.colSearch.emit(self.mw.app.clipboard().text())  # ty:ignore[unresolved-attribute]

    def getConfig(self) -> Dict[str, Any]:
        return get_addon_config()

    def handleBulkTextExport(self, cards: list) -> None:
        self.bulkTextExport.emit(cards)

    def handleExtensionCardExport(self, card: dict) -> None:
        config = self.getConfig()
        audioFileName = card["audio"]
        imageFileName = card["image"]
        bulk = card["bulk"]
        if audioFileName:
            audioTempPath = join(self.temp_dir, audioFileName)
            if not self.checkFileExists(audioTempPath):
                self.extensionFileNotFound.emit()
                return
            self.moveExtensionFileToMediaFolder(audioTempPath, audioFileName)
            self.removeFile(audioTempPath)
        if imageFileName:
            imageTempPath = join(self.temp_dir, imageFileName)
            if self.checkFileExists(imageTempPath):
                self.saveScaledImage(imageTempPath, imageFileName)
                self.removeFile(imageTempPath)
        if bulk:
            self.bulkMediaExport.emit(card)
        else:
            self.extensionCardExport.emit(card)

    def saveScaledImage(self, imageTempPath: str, imageFileName: str) -> None:
        maxW = self.mw.AnkiDictConfig["maxWidth"]  # ty:ignore[unresolved-attribute]
        maxH = self.mw.AnkiDictConfig["maxHeight"]  # ty:ignore[unresolved-attribute]
        if not imageFileName.lower().endswith(".avif"):
            imageFileName = re.sub(r"\.[^.]+$", ".avif", imageFileName)

        path = join(self.mw.col.media.dir(), imageFileName)  # ty:ignore[unresolved-attribute]
        image = QImage(imageTempPath)
        image = image.scaled(
            QSize(maxW, maxH),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image.save(path, "AVIF")

    def removeFile(self, file: str) -> None:
        os.remove(file)

    def checkFileExists(self, source: str) -> bool:
        now = time.time()
        while True:
            if exists(source):
                return True
            if time.time() - now > 15:
                return False

    def moveExtensionFileToMediaFolder(self, source: str, filename: str) -> bool | None:
        if exists(source):
            path = join(self.mw.col.media.dir(), filename)  # ty:ignore[unresolved-attribute]
            if not exists(path):
                copyfile(source, path)
                return True
        return None

    def handlePageRefreshDuringBulkMediaImport(self) -> None:
        self.pageRefreshDuringBulkMediaImport.emit()

    def handleImageExport(self) -> None:
        if self.checkDict():
            mime = self.mw.app.clipboard().mimeData()  # ty:ignore[unresolved-attribute]
            clip = self.mw.app.clipboard().text()  # ty:ignore[unresolved-attribute]

            if not clip.endswith(".mp3") and mime.hasImage():
                image = mime.imageData()
                filename = str(time.time()) + ".avif"
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
                            temp, mp3 = self.moveAudioToTempFolder(path)
                            if mp3:
                                self.image.emit([temp, "[sound:" + mp3 + "]", mp3])
                        except Exception:
                            return

    def moveAudioToTempFolder(self, path: str) -> Tuple[Any, Any]:
        try:
            if exists(path):
                filename = str(time.time()).replace(".", "") + ".mp3"
                destpath = join(self.temp_dir, filename)
                if not exists(destpath):
                    copyfile(path, destpath)
                    return destpath, filename
            return False, False
        except Exception:
            return False, False

    def handleSentenceExport(self) -> None:
        if self.checkDict():
            self.sentence.emit(self.mw.app.clipboard().text())  # ty:ignore[unresolved-attribute]
