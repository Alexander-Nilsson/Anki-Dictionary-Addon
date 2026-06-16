# -*- coding: utf-8 -*-
"""
Main window and UI management for the Dictionary Addon.

This module contains the main dictionary interface initialization,
window management, global hotkeys, and UI helper functions.
"""

import os
import sys
import re
import json
import time
from typing import Optional, List
from os.path import dirname, join, exists
from shutil import copyfile
from operator import itemgetter

from anki.utils import is_win, is_mac, is_lin
from aqt import mw
from ..utils.logger import get_logger

log = get_logger("main_window")
from aqt.qt import Qt
from aqt.utils import showInfo
import aqt.utils

from ..core.dictionary import DictInterface
from ..core.clip_thread import ClipThread
from ..ui.themes import *
from ..ui.dialogs.theme_editor import *
from ..ui.settings.settings_gui import SettingsGui
from ..utils.common import miInfo, miAsk
from ..integrations import image_search as duckduckgoimages

from ..utils.paths import get_addon_root, get_templates_dir, get_icons_dir

# Global variables
addon_path = get_addon_root()
tmpdir = os.path.join(addon_path, "temp")
currentNote = False
currentField = False
currentKey = False
wrapperDict = False
dictWidget = False
progressBar = False


def removeTempFiles():
    """Remove temporary files from temp directory."""
    # Create directory if it doesn't exist
    os.makedirs(tmpdir, exist_ok=True)

    try:
        # Get list of files in directory
        filelist = [f for f in os.listdir(tmpdir)]

        # Remove each file/directory
        for f in filelist:
            path = os.path.join(tmpdir, f)
            try:
                # If it's a file, remove it
                if os.path.isfile(path):
                    os.remove(path)
                # If it's a directory, remove its contents first
                elif os.path.isdir(path):
                    innerDirFiles = [df for df in os.listdir(path)]
                    for df in innerDirFiles:
                        innerPath = os.path.join(path, df)
                        if os.path.isfile(innerPath):
                            os.remove(innerPath)
                    os.rmdir(path)
            except Exception as e:
                log.error(f"Error removing {path}: {str(e)}")

    except Exception as e:
        log.error(f"Error accessing temporary directory: {str(e)}")


def ankiDict(text):
    """Show info message with addon branding."""
    showInfo(text, False, "", "info", "Anki Dictionary Add-on")  # ty:ignore[invalid-argument-type]


def showA(ar):
    """Show array/object as JSON."""
    showInfo(json.dumps(ar, ensure_ascii=False))


def performColSearch(text):
    """Perform collection search with given text."""
    if text:
        text = text.strip()
        browser = aqt.DialogManager._dialogs["Browser"][1]
        if not browser:
            mw.onBrowse()
            browser = aqt.DialogManager._dialogs["Browser"][1]
        if browser:
            browser.form.searchEdit.lineEdit().setText(text)
            browser.onSearchActivated()
            browser.activateWindow()
            if not is_win:
                browser.setWindowState(
                    browser.windowState() & ~Qt.WindowState.WindowMinimized
                    | Qt.WindowState.WindowActive
                )
                browser.raise_()
            else:
                browser.setWindowFlags(
                    browser.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                )
                browser.show()
                browser.setWindowFlags(
                    browser.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
                )
                browser.show()


def captureKey(keyList):
    """Capture key press for global hotkeys."""
    key = keyList[0]
    char = str(key)
    if char not in mw.currentlyPressed:  # ty:ignore[unresolved-attribute]
        mw.currentlyPressed.append(char)  # ty:ignore[unresolved-attribute]


def releaseKey(keyList):
    """Release key for global hotkeys."""
    key = keyList[0]
    char = str(key)
    if char in mw.currentlyPressed:  # ty:ignore[unresolved-attribute]
        mw.currentlyPressed.remove(char)  # ty:ignore[unresolved-attribute]


def getWelcomeScreen():
    """Get welcome screen HTML."""
    htmlPath = os.path.join(get_templates_dir(), "welcome.html")
    try:
        with open(htmlPath, "r", encoding="utf-8") as fh:
            file = fh.read()
        return file
    except Exception as e:
        log.error(f"Error loading welcome screen from {htmlPath}: {e}")
        return ""


def getMacWelcomeScreen():
    """Get Mac-specific welcome screen HTML."""
    htmlPath = os.path.join(get_templates_dir(), "macwelcome.html")
    try:
        with open(htmlPath, "r", encoding="utf-8") as fh:
            file = fh.read()
        return file
    except Exception as e:
        log.error(f"Error loading Mac welcome screen from {htmlPath}: {e}")
        return ""


def showAfterGlobalSearch():
    """Show dictionary after global search."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.activateWindow()  # ty:ignore[unresolved-attribute]
        if not is_win:
            mw.ankiDictionary.setWindowState(  # ty:ignore[unresolved-attribute]
                mw.ankiDictionary.windowState() & ~Qt.WindowState.WindowMinimized  # ty:ignore[unresolved-attribute]
                | Qt.WindowState.WindowActive
            )
            mw.ankiDictionary.raise_()  # ty:ignore[unresolved-attribute]
        else:
            mw.ankiDictionary.setWindowFlags(
                mw.ankiDictionary.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
            mw.ankiDictionary.show()
            mw.ankiDictionary.setWindowFlags(
                mw.ankiDictionary.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
            )
            mw.ankiDictionary.show()


def dictionaryInit(terms=False):
    """Initialize or toggle the dictionary window."""
    if terms and isinstance(terms, str):
        terms = [terms]

    shortcut = "(Ctrl+W)"
    if is_mac:
        shortcut = "⌘W"

    # Get welcome screen - Show shortcuts and help inside dictionary
    if is_mac:
        welcomeScreen = getMacWelcomeScreen()
    else:
        welcomeScreen = getWelcomeScreen()

    if not mw.ankiDictionary:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary = DictInterface(  # ty:ignore[unresolved-attribute]
            mw.miDictDB,  # ty:ignore[unresolved-attribute]
            mw,
            addon_path,
            welcomeScreen,
            terms=terms,
        )
        mw.openMiDict.setText("Close Dictionary " + shortcut)  # ty:ignore[unresolved-attribute]
        showAfterGlobalSearch()
    elif not mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.show()  # ty:ignore[unresolved-attribute]
        mw.openMiDict.setText("Close Dictionary " + shortcut)  # ty:ignore[unresolved-attribute]
        showAfterGlobalSearch()
    else:
        mw.ankiDictionary.hide()  # ty:ignore[unresolved-attribute]


def openDictionarySettings():
    """Open dictionary settings window."""
    if not mw.dictSettings:  # ty:ignore[unresolved-attribute]
        mw.dictSettings = SettingsGui(mw, addon_path, openDictionarySettings)  # ty:ignore[unresolved-attribute]
    mw.dictSettings.show()  # ty:ignore[unresolved-attribute]
    if mw.dictSettings.windowState() == Qt.WindowState.WindowMinimized:  # ty:ignore[unresolved-attribute]
        mw.dictSettings.setWindowState(Qt.WindowState.WindowNoState)  # ty:ignore[unresolved-attribute]
    mw.dictSettings.setFocus()  # ty:ignore[unresolved-attribute]
    mw.dictSettings.activateWindow()  # ty:ignore[unresolved-attribute]


def searchTermList(terms):
    """Search for a list of terms."""
    limit = mw.AnkiDictConfig.get("unknownsToSearch", 3)  # ty:ignore[unresolved-attribute]
    terms = terms[:limit]
    if not mw.ankiDictionary or not mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
        dictionaryInit(terms)
    else:
        for term in terms:
            mw.ankiDictionary.initSearch(term)  # ty:ignore[unresolved-attribute]
        showAfterGlobalSearch()


def extensionFileNotFound():
    """Handle extension file not found."""
    miInfo(
        'The media files were not found in your "Download Directory", please make sure you have selected the correct directory.'
    )


def initGlobalHotkeys():
    """Initialize global hotkey thread."""
    mw.hkThread = ClipThread(mw, addon_path)  # ty:ignore[unresolved-attribute]
    mw.hkThread.sentence.connect(exportSentence)  # ty:ignore[unresolved-attribute]
    mw.hkThread.search.connect(trySearch)  # ty:ignore[unresolved-attribute]
    mw.hkThread.colSearch.connect(performColSearch)  # ty:ignore[unresolved-attribute]
    mw.hkThread.image.connect(exportImage)  # ty:ignore[unresolved-attribute]
    mw.hkThread.bulkTextExport.connect(extensionBulkTextExport)  # ty:ignore[unresolved-attribute]
    mw.hkThread.add.connect(attemptAddCard)  # ty:ignore[unresolved-attribute]
    mw.hkThread.test.connect(captureKey)  # ty:ignore[unresolved-attribute]
    mw.hkThread.release.connect(releaseKey)  # ty:ignore[unresolved-attribute]
    mw.hkThread.pageRefreshDuringBulkMediaImport.connect(cancelBulkMediaExport)  # ty:ignore[unresolved-attribute]
    mw.hkThread.bulkMediaExport.connect(extensionBulkMediaExport)  # ty:ignore[unresolved-attribute]
    mw.hkThread.extensionCardExport.connect(extensionCardExport)  # ty:ignore[unresolved-attribute]
    mw.hkThread.searchFromExtension.connect(searchTermList)  # ty:ignore[unresolved-attribute]
    mw.hkThread.extensionFileNotFound.connect(extensionFileNotFound)  # ty:ignore[unresolved-attribute]
    mw.hkThread.run()  # ty:ignore[unresolved-attribute]


def selectedText(page):
    """Get selected text from a web page."""
    text = page.selectedText()
    return text.strip() if text else None


def searchTerm(webview):
    """Search selected text in dictionary."""
    from ..utils.common import getTarget

    text = selectedText(webview)

    if text:
        text = re.sub(r"\[[^\]]+?\]", "", text)
        text = text.strip()
        if not mw.ankiDictionary or not mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
            dictionaryInit([text])
        mw.ankiDictionary.ensureVisible()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.initSearch(text)  # ty:ignore[unresolved-attribute]
        if webview.title == "main webview":
            if mw.state == "review":
                mw.ankiDictionary.dict.setReviewer(mw.reviewer)  # ty:ignore[unresolved-attribute]
        elif webview.title == "editor":
            target = getTarget(type(webview.parentEditor.parentWindow).__name__)
            mw.ankiDictionary.dict.setCurrentEditor(webview.parentEditor, target)  # ty:ignore[unresolved-attribute]
        showAfterGlobalSearch()


def searchCol(webview):
    """Search selected text in collection."""
    text = selectedText(webview)
    performColSearch(text)


# Make functions available globally
mw.dictionaryInit = dictionaryInit  # ty:ignore[unresolved-attribute]
mw.searchTerm = searchTerm  # ty:ignore[unresolved-attribute]
mw.searchCol = searchCol  # ty:ignore[unresolved-attribute]


# Implementation of global exporter functions
def exportSentence(sentence):
    """Export sentence to the card exporter."""
    if mw.ankiDictionary and mw.ankiDictionary.dict:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.initCardExporterIfNeeded()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.addWindow.exportSentence(sentence)  # ty:ignore[unresolved-attribute]


def trySearch(text):
    """Try to search text in the dictionary."""
    if mw.ankiDictionary:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.initSearch(text)  # ty:ignore[unresolved-attribute]


def exportImage(path, name):
    """Export image to the card exporter."""
    if mw.ankiDictionary and mw.ankiDictionary.dict:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.initCardExporterIfNeeded()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.addWindow.exportImage(path, name)  # ty:ignore[unresolved-attribute]


def extensionBulkTextExport(cards):
    """Handle bulk text export from extension."""
    if mw.ankiDictionary and mw.ankiDictionary.dict:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.initCardExporterIfNeeded()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.addWindow.bulkTextExport(cards)  # ty:ignore[unresolved-attribute]


def attemptAddCard():
    """Attempt to add a card from exporter."""
    if (
        mw.ankiDictionary  # ty:ignore[unresolved-attribute]
        and mw.ankiDictionary.dict  # ty:ignore[unresolved-attribute]
        and mw.ankiDictionary.dict.addWindow  # ty:ignore[unresolved-attribute]
    ):
        mw.ankiDictionary.dict.addWindow.addCard()  # ty:ignore[unresolved-attribute]


def cancelBulkMediaExport():
    """Cancel ongoing bulk media export."""
    if (
        mw.ankiDictionary  # ty:ignore[unresolved-attribute]
        and mw.ankiDictionary.dict  # ty:ignore[unresolved-attribute]
        and mw.ankiDictionary.dict.addWindow  # ty:ignore[unresolved-attribute]
    ):
        mw.ankiDictionary.dict.addWindow.bulkMediaExportCancelledByBrowserRefresh()  # ty:ignore[unresolved-attribute]


def extensionBulkMediaExport(card):
    """Handle bulk media export from extension."""
    if mw.ankiDictionary and mw.ankiDictionary.dict:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.initCardExporterIfNeeded()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.addWindow.bulkMediaExport(card)  # ty:ignore[unresolved-attribute]


def extensionCardExport(card):
    """Handle single card export from extension."""
    if mw.ankiDictionary and mw.ankiDictionary.dict:  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.initCardExporterIfNeeded()  # ty:ignore[unresolved-attribute]
        mw.ankiDictionary.dict.addWindow.addMediaCard(card)  # ty:ignore[unresolved-attribute]
