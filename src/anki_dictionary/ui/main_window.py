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
from aqt.qt import *
from aqt.utils import showInfo
import aqt.utils

from ..core.dictionary import DictInterface, ClipThread
from ..ui.themes import *
from ..ui.dialogs.theme_editor import *
from ..ui.settings.settings_gui import SettingsGui
from ..utils.common import miInfo, miAsk
from ..integrations.forvo import Forvo
from ..integrations import image_search as duckduckgoimages

# Global variables
addon_path = dirname(dirname(dirname(__file__)))
tmpdir = join(addon_path, 'temp')
currentNote = False
currentField = False
currentKey = False
wrapperDict = False
dictWidget = False
progressBar = False

def refresh_anki_dict_config(config=False):
    """Refresh the addon configuration."""
    if config:
        mw.AnkiDictConfig = config
        return
    mw.AnkiDictConfig = mw.addonManager.getConfig(__name__)

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
                print(f"Error removing {path}: {str(e)}")

    except Exception as e:
        print(f"Error accessing temporary directory: {str(e)}")

def ankiDict(text):
    """Show info message with addon branding."""
    showInfo(text, False, "", "info", "Anki Dictionary Add-on")

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
                browser.setWindowState(browser.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
                browser.raise_()
            else:
                browser.setWindowFlags(browser.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
                browser.show()
                browser.setWindowFlags(browser.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
                browser.show()

def captureKey(keyList):
    """Capture key press for global hotkeys."""
    key = keyList[0]
    char = str(key)
    if char not in mw.currentlyPressed:
        mw.currentlyPressed.append(char)

def releaseKey(keyList):
    """Release key for global hotkeys."""
    key = keyList[0]
    char = str(key)
    if char in mw.currentlyPressed:
        mw.currentlyPressed.remove(char)

def getWelcomeScreen():
    """Get welcome screen HTML."""
    htmlPath = join(addon_path, 'welcome.html')
    with open(htmlPath, 'r', encoding="utf-8") as fh:
        file = fh.read()
    return file

def getMacWelcomeScreen():
    """Get Mac-specific welcome screen HTML."""
    htmlPath = join(addon_path, 'macwelcome.html')
    with open(htmlPath, 'r', encoding="utf-8") as fh:
        file = fh.read()
    return file

def showAfterGlobalSearch():
    """Show dictionary after global search."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.activateWindow()
        if not is_win:
            mw.ankiDictionary.setWindowState(mw.ankiDictionary.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            mw.ankiDictionary.raise_()
        else:
            mw.ankiDictionary.setWindowFlags(mw.ankiDictionary.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            mw.ankiDictionary.show()
            mw.ankiDictionary.setWindowFlags(mw.ankiDictionary.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            mw.ankiDictionary.show()

def dictionaryInit(terms=False):
    """Initialize or toggle the dictionary window."""
    if terms and isinstance(terms, str):
        terms = [terms]
    
    shortcut = '(Ctrl+W)'
    if is_mac:
        shortcut = '⌘W'
    
    # Get welcome screen
    if is_mac:
        welcomeScreen = getMacWelcomeScreen()
    else:
        welcomeScreen = getWelcomeScreen()
    
    if not mw.ankiDictionary:
        mw.ankiDictionary = DictInterface(mw.miDictDB, mw, addon_path, welcomeScreen, terms=terms)
        mw.openMiDict.setText("Close Dictionary " + shortcut)
        showAfterGlobalSearch()
    elif not mw.ankiDictionary.isVisible():
        mw.ankiDictionary.show()
        mw.ankiDictionary.resetConfiguration(terms)
        mw.openMiDict.setText("Close Dictionary " + shortcut)
        showAfterGlobalSearch()
    else:
        mw.ankiDictionary.hide()

def openDictionarySettings():
    """Open dictionary settings window."""
    if not mw.dictSettings:
        mw.dictSettings = SettingsGui(mw, addon_path, openDictionarySettings)
    mw.dictSettings.show()
    if mw.dictSettings.windowState() == Qt.WindowState.WindowMinimized:
        mw.dictSettings.setWindowState(Qt.WindowState.WindowNoState)
    mw.dictSettings.setFocus()
    mw.dictSettings.activateWindow()

def setup_gui_menu():
    """Setup GUI menu items."""
    addMenu = False
    if not hasattr(mw, 'DictMainMenu'):
        mw.DictMainMenu = QMenu('Dict', mw)
        addMenu = True
    if not hasattr(mw, 'DictMenuSettings'):
        mw.DictMenuSettings = []
    if not hasattr(mw, 'DictMenuActions'):
        mw.DictMenuActions = []

    setting = QAction("Dictionary Settings", mw)
    setting.triggered.connect(openDictionarySettings)
    mw.DictMenuSettings.append(setting)

    mw.openMiDict = QAction("Open Dictionary (Ctrl+W)", mw)
    mw.openMiDict.triggered.connect(dictionaryInit)
    mw.DictMenuActions.append(mw.openMiDict)

    mw.DictMainMenu.clear()
    for act in mw.DictMenuSettings:
        mw.DictMainMenu.addAction(act)
    mw.DictMainMenu.addSeparator()
    for act in mw.DictMenuActions:
        mw.DictMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.DictMainMenu)

    # Setup global hotkeys
    mw.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), mw)
    mw.hotkeyW.activated.connect(dictionaryInit)
    
    mw.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), mw)
    mw.hotkeyS.activated.connect(lambda: searchTerm(mw.web))
    mw.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), mw)
    mw.hotkeyS.activated.connect(lambda: searchCol(mw.web))

def searchTermList(terms):
    """Search for a list of terms."""
    limit = mw.AnkiDictConfig.get("unknownsToSearch", 3)
    terms = terms[:limit]
    if not mw.ankiDictionary or not mw.ankiDictionary.isVisible():
        dictionaryInit(terms)
    else:
        for term in terms:
            mw.ankiDictionary.initSearch(term)
        showAfterGlobalSearch()

def extensionFileNotFound():
    """Handle extension file not found."""
    miInfo("The media files were not found in your \"Download Directory\", please make sure you have selected the correct directory.")

def initGlobalHotkeys():
    """Initialize global hotkey thread."""
    mw.hkThread = ClipThread(mw, addon_path)
    mw.hkThread.sentence.connect(exportSentence)
    mw.hkThread.search.connect(trySearch)
    mw.hkThread.colSearch.connect(performColSearch)
    mw.hkThread.image.connect(exportImage)
    mw.hkThread.bulkTextExport.connect(extensionBulkTextExport)
    mw.hkThread.add.connect(attemptAddCard)
    mw.hkThread.test.connect(captureKey)
    mw.hkThread.release.connect(releaseKey)
    mw.hkThread.pageRefreshDuringBulkMediaImport.connect(cancelBulkMediaExport)
    mw.hkThread.bulkMediaExport.connect(extensionBulkMediaExport)
    mw.hkThread.extensionCardExport.connect(extensionCardExport)
    mw.hkThread.searchFromExtension.connect(searchTermList)
    mw.hkThread.extensionFileNotFound.connect(extensionFileNotFound)
    mw.hkThread.run()

def selectedText(page):
    """Get selected text from a web page."""
    text = page.selectedText()
    return text.strip() if text else None

def searchTerm(webview):
    """Search selected text in dictionary."""
    from ..core.hooks import getTarget
    
    text = selectedText(webview)
    if text:
        text = re.sub(r'\[[^\]]+?\]', '', text)
        text = text.strip()
        if not mw.ankiDictionary or not mw.ankiDictionary.isVisible():
            dictionaryInit([text])
        mw.ankiDictionary.ensureVisible()
        mw.ankiDictionary.initSearch(text)
        if webview.title == 'main webview':
            if mw.state == 'review':
                mw.ankiDictionary.dict.setReviewer(mw.reviewer)
        elif webview.title == 'editor':
            target = getTarget(type(webview.parentEditor.parentWindow).__name__)
            mw.ankiDictionary.dict.setCurrentEditor(webview.parentEditor, target)
        showAfterGlobalSearch()

def searchCol(webview):
    """Search selected text in collection."""
    text = selectedText(webview)
    performColSearch(text)

# Make functions available globally
mw.dictionaryInit = dictionaryInit
mw.searchTerm = searchTerm
mw.searchCol = searchCol

# TODO: These functions need to be implemented or imported from other modules
def exportSentence(*args):
    """Export sentence - placeholder."""
    pass

def trySearch(*args):
    """Try search - placeholder."""
    pass

def exportImage(*args):
    """Export image - placeholder."""
    pass

def extensionBulkTextExport(*args):
    """Extension bulk text export - placeholder."""
    pass

def attemptAddCard(*args):
    """Attempt add card - placeholder."""
    pass

def cancelBulkMediaExport(*args):
    """Cancel bulk media export - placeholder."""
    pass

def extensionBulkMediaExport(*args):
    """Extension bulk media export - placeholder."""
    pass

def extensionCardExport(*args):
    """Extension card export - placeholder."""
    pass
