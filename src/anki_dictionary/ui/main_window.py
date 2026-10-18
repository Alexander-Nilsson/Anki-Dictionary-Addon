"""
Main window and UI management for the Dictionary Addon.

This module contains the main dictionary interface initialization,
window management, global hotkeys, and UI helper functions.
"""

import json
import os
import re

import aqt
from anki.utils import is_mac, is_win
from aqt import mw

from ..utils.logger import get_logger

log = get_logger("main_window")
from aqt.qt import Qt
from aqt.utils import showInfo

from ..core.clip_thread import ClipThread
from ..core.dictionary import DictInterface
from ..ui.settings.settings_gui import SettingsGui
from ..utils.config import get_session_terms
from ..utils.paths import get_addon_root, get_templates_dir

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


def _with_setup_cta(html: str) -> str:
    """Prepend a one-click setup card while no languages are installed."""
    try:
        db = getattr(mw, "miDictDB", None)
        if db is not None and db.getCurrentDbLangs():
            return html
    except Exception:
        return html
    cta = (
        '<div class="setup-cta" style="margin:0 auto 12px;max-width:1200px;'
        "padding:14px 18px;border:1px solid var(--border);border-radius:8px;"
        'background:var(--background-secondary);text-align:center">'
        '<p style="margin:0 0 8px;font-size:var(--font-size-lg);color:var(--text)">'
        "No dictionaries are installed yet.</p>"
        '<button type="button" onclick="if(window.pycmd)pycmd(\'openSettings:dictionaries\')" '
        'style="padding:8px 16px;border:1px solid var(--search_term);border-radius:6px;'
        "background:var(--search_term);color:var(--definition_background);"
        'font-size:var(--font-size-base);cursor:pointer">Set up dictionaries</button>'
        "</div>"
    )
    return cta + html


def getWelcomeScreen():
    """Get welcome screen HTML with platform-adaptive modifier badges.

    The template carries ``{{MOD_KEY}}`` placeholders (``⌘`` on macOS,
    ``Ctrl`` on Linux/Windows) rendered here, plus a ``data-mod-key``
    attribute so the web UI can re-resolve them at runtime as well.
    """
    from ..utils.shortcuts import render_shortcut_badges

    htmlPath = os.path.join(get_templates_dir(), "welcome.html")
    try:
        with open(htmlPath, encoding="utf-8") as fh:
            file = fh.read()
        return _with_setup_cta(render_shortcut_badges(file, bool(is_mac)))
    except Exception as e:
        log.error(f"Error loading welcome screen from {htmlPath}: {e}")
        return ""


def getMacWelcomeScreen():
    """Get Mac-specific welcome screen HTML (kept for backward compatibility).

    Delegates to the shared template renderer with the macOS modifier so
    both entry points stay in sync.
    """
    from ..utils.shortcuts import render_shortcut_badges

    htmlPath = os.path.join(get_templates_dir(), "macwelcome.html")
    try:
        with open(htmlPath, encoding="utf-8") as fh:
            file = fh.read()
        # The mac template shares the same placeholder; force the mac modifier
        # even if the file still contains a literal.
        rendered = render_shortcut_badges(file, True)
        if "{{MOD_KEY}}" not in file:
            rendered = rendered.replace(">Ctrl<", ">\u2318<")
        return _with_setup_cta(rendered)
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

    from ..utils.shortcuts import format_menu_shortcut

    shortcut = format_menu_shortcut("W", bool(is_mac))

    # Get welcome screen - Show shortcuts and help inside dictionary
    if is_mac:
        welcomeScreen = getMacWelcomeScreen()
    else:
        welcomeScreen = getWelcomeScreen()

    if not mw.ankiDictionary:  # ty:ignore[unresolved-attribute]
        # A5: when no explicit search terms were given and session restore is
        # enabled, reopen the tabs from the previous session. The config is read
        # directly (like ``searchTerm``) because the instance does not exist
        # at this point.
        if not terms:
            restored = get_session_terms(mw.AnkiDictConfig)  # ty:ignore[unresolved-attribute]
            if restored:
                terms = restored
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


def openDictionarySettings(tab: str | None = None):
    """Open dictionary settings, optionally on a specific tab."""
    if not mw.dictSettings:  # ty:ignore[unresolved-attribute]
        mw.dictSettings = SettingsGui(mw, addon_path, openDictionarySettings)  # ty:ignore[unresolved-attribute]
    mw.dictSettings.show()  # ty:ignore[unresolved-attribute]
    if tab:
        mw.dictSettings.show_tab(tab)  # ty:ignore[unresolved-attribute]
    if mw.dictSettings.windowState() == Qt.WindowState.WindowMinimized:  # ty:ignore[unresolved-attribute]
        mw.dictSettings.setWindowState(Qt.WindowState.WindowNoState)  # ty:ignore[unresolved-attribute]
    mw.dictSettings.setFocus()  # ty:ignore[unresolved-attribute]
    mw.dictSettings.activateWindow()  # ty:ignore[unresolved-attribute]


def initGlobalHotkeys():
    """Initialize the global hotkey listener (idempotent)."""
    if getattr(mw, "hkThread", None) is not None:  # ty:ignore[unresolved-attribute]
        return
    mw.hkThread = ClipThread(mw, addon_path)  # ty:ignore[unresolved-attribute]
    mw.hkThread.search.connect(trySearch)  # ty:ignore[unresolved-attribute]
    mw.hkThread.test.connect(captureKey)  # ty:ignore[unresolved-attribute]
    mw.hkThread.release.connect(releaseKey)  # ty:ignore[unresolved-attribute]
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
        # Whether the dictionary window already existed decides who runs the
        # search. Opening a new one hands the term to DictInterface, which
        # searches it once the page announces itself — so searching again here
        # would run every lookup twice, external requests included. Two
        # identical Forvo fetches ~400ms apart is enough to trip its Cloudflare
        # rate limiting, and it doubled every LLM and image request too.
        existing = bool(mw.ankiDictionary)  # ty:ignore[unresolved-attribute]
        if not existing or not mw.ankiDictionary.isVisible():  # ty:ignore[unresolved-attribute]
            dictionaryInit([text])
        mw.ankiDictionary.ensureVisible()  # ty:ignore[unresolved-attribute]
        if existing:
            # Re-showing an existing window queues nothing, so search here.
            mw.ankiDictionary.initSearch(text, source="browser")  # ty:ignore[unresolved-attribute]
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


# Global search entry points
def trySearch(text):
    """Try to search text in the dictionary (clipboard/global-hotkey path)."""
    if not text:
        return
    if not mw.ankiDictionary:  # ty:ignore[unresolved-attribute]
        # A global search is an explicit action; open the window for it.
        dictionaryInit([text])
        return
    # U2: honour the one-click clipboard-monitor pause (in-web pill). When
    # paused, ignore clipboard-derived searches so users can stop hotkey-
    # triggered lookups without disabling the addon.
    if not mw.ankiDictionary.config.get("clipboard_monitor_enabled", True):  # ty:ignore[unresolved-attribute]
        return
    mw.ankiDictionary.initSearch(text, source="clipboard")  # ty:ignore[unresolved-attribute]
