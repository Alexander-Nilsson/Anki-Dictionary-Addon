# -*- coding: utf-8 -*-
"""
Anki integration hooks for the Dictionary Addon.

This module handles all the integration points with Anki, including:
- Menu setup and context menus
- Editor hooks and functionality
- Keyboard shortcuts and hotkeys
- Window wrapping and event handling
"""

import re
from typing import Optional

try:
    from anki.hooks import addHook, wrap
    from anki.utils import is_win, is_mac, is_lin
except ImportError:
    # Fallback for testing
    addHook = lambda *args: None
    wrap = lambda *args: lambda *a, **k: None
    is_win = is_mac = is_lin = False

try:
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
except ImportError:
    # Fallback for testing - use real PyQt if possible
    try:
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *
    except ImportError:
        pass
    mw = None
    showInfo = lambda *args: None
    AddCards = EditCurrent = Browser = TagEdit = Reviewer = Previewer = object
    import sys

    aqt = sys.modules.get("aqt") or object()

from ..utils.common import miInfo, getTarget, gt
from ..utils.paths import get_addon_root

# Store the original link handler - will be set on first hook setup
_original_link_handler = None
_hooks_setup = False


def closeDictionary():
    """Close dictionary when profile is unloaded."""
    if hasattr(mw, "ankiDictionary") and mw.ankiDictionary:
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
        text = re.sub(r"\[[^\]]+?\]", "", text)
        text = text.strip()
        if not mw.ankiDictionary or not mw.ankiDictionary.isVisible():
            dictionaryInit([text])
        mw.ankiDictionary.ensureVisible()
        mw.ankiDictionary.initSearch(text)

        if webview.title == "main webview":
            if mw.state == "review":
                mw.ankiDictionary.dict.setReviewer(mw.reviewer)
        elif webview.title == "editor":
            target = getTarget(type(webview.parentEditor.parentWindow).__name__)
            mw.ankiDictionary.dict.setCurrentEditor(webview.parentEditor, target)
        showAfterGlobalSearch()


def announceParent(self, event=False):
    """Announce parent window to dictionary."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        # Safely traverse up to find the main window/editor container
        parent = self
        for _ in range(3):
            if parent:
                try:
                    parent = parent.parentWidget()
                except (TypeError, AttributeError):
                    parent = None

        if not parent:
            return

        pName = gt(parent)
        if gt(parent) not in ["AddCards", "EditCurrent"]:
            parent = aqt.DialogManager._dialogs["Browser"][1]
            pName = "Browser"
            if not parent:
                return
        mw.ankiDictionary.dict.setCurrentEditor(parent.editor, getTarget(pName))


def addEditActivated(self, event=False):
    """Handle editor activation."""
    announceParent(self, event)


def setBrowserEditor(self):
    """Set browser editor in dictionary."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.setCurrentEditor(self.editor, "Browser")


def checkCurrentEditor(self):
    """Check current editor when closing."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.checkEditorClose(self)


def addBodyClick(self):
    """Add body click functionality - handled by parent editor setup."""
    pass


def addHotkeys(self):
    """Hotkeys handled by setup_gui_menu() with ApplicationShortcut context."""
    pass


def addHotkeysToPreview(self):
    """Hotkeys handled by setup_gui_menu() with ApplicationShortcut context."""
    pass


def addEditorFunctionality(self):
    """Add functionality to editor."""
    self.web.parentEditor = self
    addBodyClick(self)
    addHotkeys(self)


def miLinks(self, cmd):
    """Handle reviewer links."""
    if mw.ankiDictionary and mw.ankiDictionary.isVisible():
        mw.ankiDictionary.dict.setReviewer(self)
    return _original_link_handler(self, cmd)


def setup_hooks():
    """Setup all Anki hooks and wrapping."""
    global _original_link_handler, _hooks_setup

    # Prevent double-wrapping
    if _hooks_setup:
        return
    _hooks_setup = True

    # Profile hooks
    addHook("unloadProfile", closeDictionary)
    addHook("profileLoaded", dictOnStart)

    # Context menu hooks
    addHook("EditorWebView.contextMenuEvent", addToContextMenu)
    addHook("AnkiWebView.contextMenuEvent", addToContextMenu)

    # Browser menu hook
    addHook("browser.setupMenus", setupMenu)

    # Wrap browser methods
    Browser.on_current_row_changed = wrap(
        Browser.on_current_row_changed, setBrowserEditor
    )
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
    aqt.editor.Editor.setupWeb = wrap(
        aqt.editor.Editor.setupWeb, addEditorFunctionality
    )

    # Wrap tag edit
    TagEdit.focusInEvent = wrap(TagEdit.focusInEvent, announceParent)

    # Wrap preview
    Previewer.open = wrap(Previewer.open, addHotkeysToPreview)

    # Wrap reviewer - store original BEFORE wrapping
    _original_link_handler = Reviewer._linkHandler
    Reviewer._linkHandler = miLinks
    Reviewer.show = wrap(Reviewer.show, addBodyClick)


from ..utils.logger import get_logger

logger = get_logger("Hooks")

# ... (middle of file)


def setup_gui_menu():
    """Setup GUI menu items."""
    logger.debug("--- Anki Dictionary: Setting up GUI menu ---")

    # Defer imports of main_window functions to avoid circularity during initialization
    def trigger_dictionary_init(terms=False):
        logger.debug("Action triggered: Opening Dictionary")
        from ..ui.main_window import dictionaryInit

        dictionaryInit(terms)

    def trigger_open_settings():
        logger.debug("Action triggered: Opening Settings")
        from ..ui.main_window import openDictionarySettings

        openDictionarySettings()

    def trigger_search_term():
        logger.debug("Action triggered: Search Term")
        from ..ui.main_window import searchTerm

        focused_widget = mw.app.focusWidget()

        # Check if dictionary window is focused and visible
        if mw.ankiDictionary and mw.ankiDictionary.isVisible():
            if focused_widget and (
                focused_widget == mw.ankiDictionary.dict
                or mw.ankiDictionary.isAncestorOf(focused_widget)
            ):
                # Search within the dictionary
                searchTerm(mw.ankiDictionary.dict)
                return

        # Check if an Editor is focused
        if focused_widget:
            # Check for Editor (AddCards, EditCurrent, Browser editor)
            parent = focused_widget
            while parent:
                if hasattr(parent, "editor") and parent.editor:
                    searchTerm(parent.editor.web)
                    return
                if hasattr(parent, "web") and parent.web:
                    # Generic web view (Reviewer, Browser card list if it's a webview, etc)
                    searchTerm(parent.web)
                    return
                try:
                    parent = parent.parent()
                except (TypeError, AttributeError):
                    parent = None

        # Fallback to main webview (Reviewer)
        searchTerm(mw.web)

    def trigger_search_col():
        logger.debug("Action triggered: Search Collection")
        from ..ui.main_window import searchCol

        focused_widget = mw.app.focusWidget()

        if focused_widget:
            parent = focused_widget
            while parent:
                if hasattr(parent, "editor") and parent.editor:
                    searchCol(parent.editor.web)
                    return
                if hasattr(parent, "web") and parent.web:
                    searchCol(parent.web)
                    return
                try:
                    parent = parent.parent()
                except (TypeError, AttributeError):
                    parent = None

        searchCol(mw.web)

    # Use a more stable location for the menu to avoid issues with standard shortcuts
    if not hasattr(mw, "DictMainMenu"):
        logger.debug("Creating new DictMainMenu")
        mw.DictMainMenu = QMenu("Anki Dictionary", mw)
        # Insert before Help menu
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.DictMainMenu)
    else:
        logger.debug("Updating existing DictMainMenu")
        mw.DictMainMenu.clear()

    # Dictionary Settings Action
    setting_action = QAction("Settings...", mw)
    setting_action.triggered.connect(trigger_open_settings)
    mw.DictMainMenu.addAction(setting_action)

    mw.DictMainMenu.addSeparator()

    # Open Dictionary Action with Shortcut
    open_action = QAction("Open Dictionary", mw)
    open_action.setShortcut(QKeySequence("Ctrl+W"))
    # Ensure the shortcut works throughout the application
    open_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    open_action.triggered.connect(lambda: trigger_dictionary_init())
    mw.DictMainMenu.addAction(open_action)

    # Store actions on mw to prevent garbage collection
    # Also set legacy openMiDict attribute for toggle functionality in main_window.py
    mw.openMiDict = open_action
    mw.dict_actions = {"settings": setting_action, "open": open_action}

    # Search Actions
    search_term_action = QAction("Search Selected Term", mw)
    search_term_action.setShortcut(QKeySequence("Ctrl+S"))
    search_term_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    search_term_action.triggered.connect(trigger_search_term)
    mw.DictMainMenu.addAction(search_term_action)
    mw.dict_actions["search_term"] = search_term_action

    search_col_action = QAction("Search in Collection", mw)
    search_col_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
    search_col_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
    search_col_action.triggered.connect(trigger_search_col)
    mw.DictMainMenu.addAction(search_col_action)
    mw.dict_actions["search_col"] = search_col_action

    logger.debug("Menu setup completed with shortcuts: Ctrl+W, Ctrl+S, Ctrl+Shift+B")
