# -*- coding: utf-8 -*-
"""
Anki integration hooks for the Dictionary Addon.

This module handles all the integration points with Anki, including:
- Menu setup and context menus
- Editor hooks and functionality
- Keyboard shortcuts and hotkeys
- Window wrapping and event handling
"""

import os
import re
import json
from typing import Optional
from anki.hooks import addHook, wrap
from anki.utils import is_win, is_mac, is_lin
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.reviewer import Reviewer
from aqt.previewer import Previewer
import aqt.editor

from ..utils.common import miInfo

# Get addon path
addon_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def closeDictionary():
    """Close dictionary when profile is unloaded."""
    if hasattr(mw, 'ankiDictionary') and mw.ankiDictionary:
        mw.ankiDictionary.hide()

def dictOnStart():
    """Initialize dictionary when profile is loaded."""
    from ..ui.main_window import removeTempFiles, initGlobalHotkeys
    removeTempFiles()
    # Uncomment if global hotkeys are enabled
    # if mw.addonManager.getConfig(__name__)['globalHotkeys']:
    #     initGlobalHotkeys()

def addToContextMenu(webview, menu):
    """Add dictionary search to context menu."""
    from ..ui.main_window import searchTerm, searchCol
    
    action1 = menu.addAction("Search in Dictionary")
    action1.triggered.connect(lambda: searchTerm(webview))
    
    action2 = menu.addAction("Search in Collection")
    action2.triggered.connect(lambda: searchCol(webview))

def setupMenu(browser):
    """Setup browser menu items."""
    from ..ui.main_window import dictionaryInit, openDictionarySettings
    
    dict_menu = browser.form.menuEdit.addMenu("Dictionary")
    
    action1 = dict_menu.addAction("Search Dictionary")
    action1.triggered.connect(lambda: dictionaryInit())
    
    action2 = dict_menu.addAction("Dictionary Settings")
    action2.triggered.connect(openDictionarySettings)

def selectedText(page):
    """Get selected text from a web page."""
    text = page.selectedText()
    return text.strip() if text else None

def searchCol(webview):
    """Search selected text in collection."""
    from ..ui.main_window import performColSearch
    text = selectedText(webview)
    performColSearch(text)

def searchTerm(webview):
    """Search selected text in dictionary."""
    from ..ui.main_window import dictionaryInit, showAfterGlobalSearch
    
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

def getTarget(name):
    """Get target window type."""
    if name == 'AddCards':
        return 'Add'
    elif name == "EditCurrent" or name == "DictEditCurrent":
        return 'Edit'
    elif name == 'Browser':
        return name
    return name

def gt(obj):
    """Get type name of object."""
    return type(obj).__name__

def announceParent(self, event=False):
    """Announce parent window to dictionary."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        parent = self.parentWidget().parentWidget().parentWidget()
        pName = gt(parent)
        if gt(parent) not in ['AddCards', 'EditCurrent']:
            parent = aqt.DialogManager._dialogs["Browser"][1]
            pName = 'Browser'
            if not parent:
                return
        mw.ankiDictionary.dict.setCurrentEditor(parent.editor, getTarget(pName))

def addEditActivated(self, event=False):
    """Handle editor activation."""
    announceParent(self, event)

def setBrowserEditor(self):
    """Set browser editor in dictionary."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.setCurrentEditor(self.editor, 'Browser')

def checkCurrentEditor(self):
    """Check current editor when closing."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.checkCurrentEditor()

def addBodyClick(self):
    """Add body click functionality."""
    if hasattr(self, 'web') and hasattr(self.web, 'parentEditor'):
        pass  # Already has parent editor

def addHotkeys(self):
    """Add hotkeys to editor."""
    from ..ui.main_window import dictionaryInit
    
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self.parentWindow)
    self.parentWindow.hotkeyS.activated.connect(lambda: searchTerm(self.web))
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), self.parentWindow)
    self.parentWindow.hotkeyS.activated.connect(lambda: searchCol(self.web))
    self.parentWindow.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self.parentWindow)
    self.parentWindow.hotkeyW.activated.connect(dictionaryInit)

def addHotkeysToPreview(self):
    """Add hotkeys to preview window."""
    from ..ui.main_window import dictionaryInit
    
    self._web.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self._web)
    self._web.hotkeyS.activated.connect(lambda: searchTerm(self._web))
    self._web.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), self._web)
    self._web.hotkeyS.activated.connect(lambda: searchCol(self._web))
    self._web.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self._web)
    self._web.hotkeyW.activated.connect(dictionaryInit)

def addEditorFunctionality(self):
    """Add functionality to editor."""
    self.web.parentEditor = self
    addBodyClick(self)
    addHotkeys(self)

def miLinks(self, cmd):
    """Handle reviewer links."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.setReviewer(self)
    return ogLinks(self, cmd)

def setup_hooks():
    """Setup all Anki hooks and wrapping."""
    global ogLinks
    
    # Profile hooks
    addHook("unloadProfile", closeDictionary)
    addHook("profileLoaded", dictOnStart)
    
    # Context menu hooks
    addHook("EditorWebView.contextMenuEvent", addToContextMenu)
    addHook("AnkiWebView.contextMenuEvent", addToContextMenu)
    
    # Browser menu hook
    addHook("browser.setupMenus", setupMenu)
    
    # Wrap browser methods
    Browser.on_current_row_changed = wrap(Browser.on_current_row_changed, setBrowserEditor)
    Browser._closeWindow = wrap(Browser._closeWindow, checkCurrentEditor)
    
    # Wrap add cards methods
    AddCards._close = wrap(AddCards._close, checkCurrentEditor)
    AddCards.addCards = wrap(AddCards.addCards, addEditActivated)
    AddCards.onHistory = wrap(AddCards.onHistory, addEditActivated)
    AddCards.mousePressEvent = addEditActivated
    
    # Wrap edit current methods
    EditCurrent._saveAndClose = wrap(EditCurrent._saveAndClose, checkCurrentEditor)
    EditCurrent.mousePressEvent = addEditActivated
    
    # Wrap editor setup
    aqt.editor.Editor.setupWeb = wrap(aqt.editor.Editor.setupWeb, addEditorFunctionality)
    
    # Wrap tag edit
    TagEdit.focusInEvent = wrap(TagEdit.focusInEvent, announceParent)
    
    # Wrap preview
    Previewer.open = wrap(Previewer.open, addHotkeysToPreview)
    
    # Wrap reviewer
    ogLinks = Reviewer._linkHandler
    Reviewer._linkHandler = miLinks
    Reviewer.show = wrap(Reviewer.show, addBodyClick)
