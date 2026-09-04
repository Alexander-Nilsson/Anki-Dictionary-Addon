from __future__ import annotations

import json
import os
import re
from os.path import dirname, exists, join

from anki.utils import is_mac
from aqt.qt import (
    QColor,  # noqa: F401 — needed at runtime by downstream importers
    QComboBox,
    QFrame,
    QHBoxLayout,
    QIcon,
    QImage,
    QKeySequence,
    QLabel,
    QLineEdit,
    QPalette,
    QPixmap,  # noqa: F401 — needed at runtime by downstream importers
    QPushButton,
    QShortcut,
    QSize,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
)
from aqt.utils import (
    ensureWidgetInScreenBoundaries,
)
from aqt.webview import AnkiWebView
from PyQt6.QtCore import QThreadPool, QUrl

from ..utils.history import HistoryBrowser, HistoryModel
from ..utils.logger import get_logger
from .card_handler import CardCreationHandler
from .search.pipeline import SearchPipeline

logger = get_logger(__name__.split(".")[-1])

import codecs
import datetime

from PyQt6.QtSvgWidgets import QSvgWidget

from ..ui import theme_controller
from ..ui.dialogs.theme_editor import ThemeEditorDialog
from ..ui.settings.settings_gui import SettingsGui
from ..ui.themes import ThemeManager


class MIDict(AnkiWebView):
    def __init__(self, dictInt, db, path, terms=False):
        AnkiWebView.__init__(self)
        self.page().profile().setHttpUserAgent(  # ty:ignore[unresolved-attribute]
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
        )
        self.terms = terms
        self.dictInt = dictInt
        self.config = self.dictInt.getConfig()
        self.maxW = self.config.get("maxWidth", 1500)
        self.maxH = self.config.get("maxHeight", 400)
        self.onBridgeCmd = self.handleDictAction
        self.db = db
        self.sType = False
        self.radioCount = 0
        self.homeDir = path
        self.addonPath = path
        self.addon_root = dirname(dirname(dirname(dirname(__file__))))
        self.temp_dir = join(self.addon_root, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.deinflect = True
        self.addWindow = False
        self.currentEditor = False
        self.reviewer = False
        self.threadpool = QThreadPool()
        self.customFontsLoaded = []

        self.search_pipeline = SearchPipeline(self)
        self.card_handler = CardCreationHandler(self)

        self.termHeaders = self.search_pipeline.formatTermHeaders(
            self.db.getTermHeaders() or {}
        )
        self.conjugations = self.search_pipeline.loadConjugations()

    def loadHTMLURL(self, html, url):
        self.page().setHtml(html, url)

    def setSType(self, sType):
        self.sType = sType

    def addNewTab(self, term, selectedGroup):
        return self.search_pipeline.addNewTab(term, selectedGroup)

    def maybeSearchTerms(self, terms: str) -> None:
        if self.terms:
            for t in self.terms:  # ty:ignore[not-iterable]
                self.dictInt.initSearch(t)
            self.terms = False

    def handleDictAction(self, dAct):
        if dAct.startswith("AnkiDictionaryLoaded"):
            self.maybeSearchTerms(dAct)
        elif dAct.startswith("updateTerm:"):
            term = dAct[11:]
            self.dictInt.search.setText(term)
        elif dAct.startswith("saveFS:"):
            f1, f2 = dAct[7:].split(":")
            self.dictInt.writeConfig("fontSizes", [int(f1), int(f2)])
        elif dAct.startswith("openSettings"):
            self.dictInt.openDictionarySettings()
        elif dAct.startswith("saveSidebarWidth:"):
            width = max(int(dAct[17:]), 20)
            self.dictInt.writeConfig("sidebarWidth", width)
        elif dAct.startswith("fieldsSetting:"):
            fields = json.loads(dAct[14:])
            logger.debug(f"Received fieldsSetting command: {fields}")
            if fields["dictName"] == "Images":
                self.dictInt.writeConfig("ImageFields", fields["fields"])
            elif fields["dictName"] == "LLM":
                self.dictInt.writeConfig("LLMFields", fields["fields"])
            elif fields["dictName"] == "Forvo":
                self.dictInt.writeConfig("ForvoFields", fields["fields"])
            else:
                self.dictInt.updateFieldsSetting(fields["dictName"], fields["fields"])
        elif dAct.startswith("overwriteSetting:"):
            addType = json.loads(dAct[17:])
            if addType["name"] == "Images":
                self.dictInt.writeConfig("ImageAddType", addType["type"])
            elif addType["name"] == "LLM":
                self.dictInt.writeConfig("LLMAddType", addType["type"])
            elif addType["name"] == "Forvo":
                self.dictInt.writeConfig("ForvoAddType", addType["type"])
            else:
                self.dictInt.updateAddType(addType["name"], addType["type"])
        elif dAct.startswith("clipped:"):
            text = dAct[8:]
            self.dictInt.mw.app.clipboard().setText(text.replace("<br>", "\n"))
        elif dAct.startswith("clipped_images:"):
            urls_json = dAct[15:]
            self.card_handler.copyImagesToClipboard(urls_json)
        elif dAct.startswith("sendToField:"):
            name, text = dAct[12:].split("\u25f3\u25f4")
            self.card_handler.sendToField(name, text)
        elif dAct.startswith("sendAudioToField:"):
            urls = dAct[17:]
            self.card_handler.sendAudioToField(urls)
        elif dAct.startswith("sendImgToField:"):
            urls = dAct[15:]
            self.card_handler.sendImgToField(urls)
        elif dAct.startswith("playAudio:"):
            url = dAct[10:]
            self.card_handler.playAudio(url)
        elif dAct.startswith("addDef:"):
            dictName, word, text = dAct[7:].split("\u25f3\u25f4")
            self.card_handler.addDefToExportWindow(dictName, word, text)
        elif dAct.startswith("audioExport:"):
            word, urls = dAct[12:].split("\u25f3\u25f4")
            self.card_handler.addAudioToExportWindow(word, urls)
        elif dAct.startswith("imgExport:"):
            word, urls = dAct[10:].split("\u25f3\u25f4")
            self.card_handler.addImgsToExportWindow(word, json.loads(urls))
        elif dAct.startswith("load_more_images:"):
            search_term = dAct[17:]
            self.search_pipeline.loadMoreImages(search_term)
        elif dAct.startswith("getMoreImages::"):
            search_term = dAct[15:]
            self.search_pipeline.loadMoreImages(search_term)

    def setCurrentEditor(self, editor, target=""):
        if editor != self.currentEditor:
            self.currentEditor = editor
            self.reviewer = False
            self.dictInt.currentTarget.setText(target)

    def setReviewer(self, reviewer):
        self.reviewer = reviewer
        self.currentEditor = False
        self.dictInt.currentTarget.setText("Reviewer")

    def checkEditorClose(self, editor):
        if self.currentEditor == editor:
            self.closeEditor()

    def closeEditor(self):
        self.reviewer = False
        self.currentEditor = False
        self.dictInt.currentTarget.setText("")


class HoverButton(QPushButton):
    mouseHover = pyqtSignal(bool)
    mouseOut = pyqtSignal(bool)

    def __init__(self, parent=None):
        QPushButton.__init__(self, parent)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.mouseHover.emit(True)

    def leaveEvent(self, event):  # ty:ignore[invalid-method-override]
        self.mouseHover.emit(False)
        self.mouseOut.emit(True)


# Refactor imageResizer to use QImage for better portability
def imageResizer(img_path):
    """
    Resizes an image at img_path to fit within 300x300 using QImage.
    Returns True if success, False otherwise.
    Note: In this addon, resizing is usually done during download.
    """
    try:
        image = QImage(img_path)
        if image.isNull():
            return False

        max_size = 300
        if image.width() > max_size or image.height() > max_size:
            image = image.scaled(
                QSize(max_size, max_size),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            return image.save(img_path)
        return True
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        return False


class DictInterface(QWidget):
    def __init__(self, dictdb, mw, path, welcome, parent=None, terms=False):
        super().__init__()
        self.db = dictdb
        self.verticalBar = False
        self.addonPath = path
        self.welcome = welcome
        self.setAutoFillBackground(True)
        self.mw = mw
        self.parent = parent  # ty:ignore[invalid-assignment]
        self.iconpath = join(path, "assets", "icons")

        self.active_theme_file = join(
            self.addonPath, "user_files/themes", "active.json"
        )
        self.theme_manager = ThemeManager(self.addonPath)
        self.theme_editor = ThemeEditorDialog(self.theme_manager, mw, path, self)
        self.theme_editor.applied.connect(self.refresh_application_theme)

        self.startUp(terms)
        self.setHotkeys()
        self.threadpool = QThreadPool()  # Initialize QThreadPool
        ensureWidgetInScreenBoundaries(self)

    def refresh_application_theme(self, reload_html=True):
        self.theme_manager._load_active_theme()
        self.setStyleSheet(self.theme_manager.get_qt_styles())
        theme_controller.apply_child_widget_styles(self, self.theme_manager)
        self.setAllIcons()
        icon_name = theme_controller.get_window_icon_name(self.theme_manager)
        self.setWindowIcon(QIcon(join(self.iconpath, icon_name)))
        if reload_html:
            html, url = self.getHTMLURL(False)
            self.dict.loadHTMLURL(html, url)
        if hasattr(self, "historyBrowser") and self.historyBrowser:
            self.historyBrowser.setColors()

    def getPalette(self, color):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, color)
        return pal

    def setHotkeys(self):
        """Set up keyboard shortcuts for the dictionary window."""
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)

    def getFontColor(self, color):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Base, color)
        return pal

    def getStretchLay(self):
        stretch = QHBoxLayout()
        stretch.setContentsMargins(0, 0, 0, 0)
        stretch.addStretch()
        return stretch

    def setAlwaysOnTop(self):
        if self.alwaysOnTop:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
            )
            self.show()

    def reloadConfig(self, config):
        self.config = config
        self.dict.config = config

    def startUp(self, terms):
        terms = self.refineToValidSearchTerms(terms)
        willSearch = False
        if terms is not False:
            willSearch = True
        self.config = self.getConfig()
        self.allGroups = self.getAllGroups()
        self.defaultGroups = self.db.getDefaultGroups()
        self.userGroups = self.getUserGroups()
        self.searchOptions = [
            "Forward",
            "Backward",
            "Exact",
            "Anywhere",
            "Definition",
            "Example",
            "Pronunciation",
        ]
        self.setWindowTitle("Anki Dictionary")
        self.dictGroups = self.setupDictGroups()
        # self.nightModeToggler = self.setupNightModeToggle()
        self.themeSettings = self.setupThemes()
        # self.setSvg(self.nightModeToggler, 'theme')
        self.dict = MIDict(self, self.db, self.addonPath, terms)
        self.conjToggler = self.setupConjugationMode()
        self.minusB = self.setupMinus()
        self.plusB = self.setupPlus()
        self.tabB = self.setupTabMode()
        self.histB = self.setupOpenHistory()
        self.setB = self.setupOpenSettings()
        self.searchButton = self.setupSearchButton()
        self.insertHTMLJS = self.getInsertHTMLJS()
        self.search = self.setupSearch()
        self.sType = self.setupSearchType()
        self.openSB = self.setupOpenSB()
        self.openSB.opened = False
        self.currentTarget = QLabel("")
        self.targetLabel = QLabel(" Target:")
        self.stretch1 = self.getStretchLay()
        self.stretch2 = self.getStretchLay()
        self.layoutH2 = QHBoxLayout()
        self.mainHLay = QHBoxLayout()
        self.mainLayout = self.setupView()
        self.dict.setSType(self.sType)
        self.setLayout(self.mainLayout)
        self.resize(800, 600)
        self.setMinimumSize(350, 350)
        self.sbOpened = False
        self.historyModel = HistoryModel(self.getHistory(), self)
        self.historyBrowser = HistoryBrowser(self.historyModel, self)
        icon_name = theme_controller.get_window_icon_name(self.theme_manager)
        self.setWindowIcon(QIcon(join(self.iconpath, icon_name)))
        self.readyToSearch = False
        self.restoreSizePos()
        self.initTooltips()
        self.show()
        self.search.setFocus()
        self.refresh_application_theme()
        # if self.nightModeToggler.day:
        #     self.refresh_application_theme()
        # else:
        #     self.refresh_application_theme()
        html, url = self.getHTMLURL(willSearch)
        self.dict.loadHTMLURL(html, url)
        self.alwaysOnTop = self.config["dictAlwaysOnTop"]
        self.maybeSetToAlwaysOnTop()

    def maybeSetToAlwaysOnTop(self):
        if self.alwaysOnTop:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.show()

    def initTooltips(self):
        if self.config["tooltips"]:
            self.dictGroups.setToolTip("Select the dictionary group.")
            self.sType.setToolTip(
                "Select the search type (e.g., Forward, Backward, Exact, Definition, etc.).\n"
                "Hover over individual options in the list for more details."
            )
            self.openSB.setToolTip("Open/Close the definition sidebar.")
            self.minusB.setToolTip("Decrease the dictionary's font size.")
            self.plusB.setToolTip("Increase the dictionary's font size.")
            self.tabB.setToolTip("Switch between single and multi-tab modes.")
            self.histB.setToolTip("Open the history viewer.")
            self.conjToggler.setToolTip("Turn deinflection mode on/off.")
            # self.nightModeToggler.setToolTip('Enable/Disable night-mode.')
            self.setB.setToolTip("Open the dictionary settings.")

    def restoreSizePos(self):
        sizePos = self.config["dictSizePos"]
        if sizePos:
            self.resize(sizePos[2], sizePos[3])
            self.move(sizePos[0], sizePos[1])
        #     self.resize(800, 600)
        #     self.move(100, 100)

    def refineToValidSearchTerms(self, terms):
        if terms:
            validTerms = []
            for term in terms:
                term = term.strip()
                term = self.cleanTermBrackets(term)
                if term != "":
                    validTerms.append(term)
            if len(validTerms) > 0:
                return validTerms
        return False

    def _get_font_sizes(self) -> tuple[int, int]:
        font_sizes = self.config.get("fontSizes", [12, 22])
        fefs = font_sizes[0] if len(font_sizes) > 0 else 12
        dbfs = font_sizes[1] if len(font_sizes) > 1 else 22
        return int(fefs), int(dbfs)

    def _get_sidebar_width(self) -> int:
        """Saved sidebar width in px (0 = unset, keep the CSS default)."""
        return max(int(self.config.get("sidebarWidth", 0) or 0), 0)

    def _svelte_dictionary_path(self) -> str | None:
        """Locate the built Svelte UI bundle.

        In a source checkout it lives at ``web/dist/dictionary.html``; in a
        packaged addon it is copied to ``assets/web/dictionary.html`` by
        ``build.py``. Returns ``None`` when the web UI has not been built so
        callers can fall back to the legacy static assets.
        """
        candidates = (
            join(self.addonPath, "web", "dist", "dictionary.html"),
            join(self.addonPath, "assets", "web", "dictionary.html"),
        )
        for candidate in candidates:
            if exists(candidate):
                return candidate
        return None

    def getHTMLURL(self, _willSearch):
        active_theme_dict = theme_controller.get_theme_dict(self.theme_manager)
        qss = theme_controller.generate_qt_stylesheet(active_theme_dict)
        self.setStyleSheet(qss)
        custom_theme_css = theme_controller.generate_html_css(active_theme_dict)
        fefs, dbfs = self._get_font_sizes()
        sidebar_width = self._get_sidebar_width()

        svelte_path = self._svelte_dictionary_path()
        if svelte_path:
            html, url = self._get_html_url_svelte(
                svelte_path, custom_theme_css, fefs, dbfs, sidebar_width
            )
        else:
            html, url = self._get_html_url_legacy(
                custom_theme_css, fefs, dbfs, sidebar_width
            )
        return html, url

    def _get_html_url_svelte(
        self,
        html_path: str,
        custom_theme_css: str,
        fefs: int,
        dbfs: int,
        sidebar_width: int,
    ) -> tuple[str, QUrl]:
        """Load the Svelte-built shell and apply the Python-side injections.

        The Svelte ``index.html`` keeps the same placeholder hooks as the
        legacy template (``customThemeCss``, ``welcomeBackground`` and a
        ``FONT_SIZES`` marker) so the UI is configured identically.
        """
        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()

        # Font sizes + saved sidebar width: the Svelte app reads
        # window.fefs / window.dbfs / window.sidebarWidth.
        font_size_init = (
            f"<script>window.fefs = {fefs}; window.dbfs = {dbfs};"
            f" window.sidebarWidth = {sidebar_width};</script>"
        )
        html = html.replace("<!-- FONT_SIZES -->", font_size_init)

        # Theme CSS.
        html = html.replace('<style id="customThemeCss"></style>', custom_theme_css)

        # Welcome screen content.
        if self.welcome and self.welcome.strip():
            html = html.replace(
                '<div id="welcomeBackground"></div>',
                f'<div id="welcomeBackground">{self.welcome}</div>',
            )

        # Welcome visibility is fully reactive in the Svelte shell; nothing
        # else needs to be injected.
        self.svelte_shell = True
        return html, QUrl.fromLocalFile(html_path)

    def _get_html_url_legacy(
        self, custom_theme_css: str, fefs: int, dbfs: int, sidebar_width: int
    ) -> tuple[str, QUrl]:
        html_path = join(self.addonPath, "assets", "templates", "dictionary.html")
        js_path = join(self.addonPath, "assets", "scripts", "dictionary.js")

        with open(js_path, encoding="utf-8") as js_file:
            js_content = js_file.read()

        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()
            font_size_init = (
                f"<script>var fefs = {fefs}, dbfs = {dbfs},"
                f" sidebarWidth = {sidebar_width};</script>"
            )
            html = html.replace(
                '<script src="../scripts/dictionary.js"></script>',
                f"{font_size_init}<script>{js_content}</script>",
            )
            html = html.replace('<style id="customThemeCss"></style>', custom_theme_css)
            if self.welcome and self.welcome.strip():
                html = html.replace(
                    '<div id="welcomeBackground"></div>',
                    f'<div id="welcomeBackground">{self.welcome}</div>',
                )
            # Don't add a Welcome tab anymore, just show the background.
            html = html.replace(
                '<script id="initialValue"></script>',
                '<script id="initialValue">updateWelcomeVisibility();</script>',
            )
            url = QUrl.fromLocalFile(html_path)
        self.svelte_shell = False
        return html, url

    def getAllGroups(self):
        allGroups = {}
        dicts = self.db.getAllDictsWithLang()
        dicts.append({"dict": "Images", "lang": ""})
        if self.config.get("llm_enabled", False):
            dicts.append({"dict": "LLM", "lang": ""})
        allGroups["dictionaries"] = dicts
        allGroups["customFont"] = False
        allGroups["font"] = False
        return allGroups

    def getInsertHTMLJS(self):
        insertHTML = join(self.addonPath, "assets", "scripts", "insertHTML.js")
        with open(insertHTML, encoding="utf-8") as insertHTMLFile:
            return insertHTMLFile.read()

    def focusWindow(self):
        self.show()
        if self.windowState() == Qt.WindowState.WindowMinimized:
            self.setWindowState(Qt.WindowState.WindowNoState)
        self.setFocus()
        self.activateWindow()

    def closeEvent(self, event):  # ty:ignore[invalid-method-override]
        self.hide()

    def hideEvent(self, event):  # ty:ignore[invalid-method-override]
        self.saveSizeAndPos()
        shortcut = "(Ctrl+W)"
        if is_mac:
            shortcut = "⌘W"
        self.mw.openMiDict.setText("Open Dictionary " + shortcut)
        event.accept()

    def resetConfiguration(self, terms=False):
        if not isinstance(terms, (list, tuple)):
            terms = False

        if terms:
            terms = self.refineToValidSearchTerms(terms)

        willSearch = False
        if terms is not False:
            willSearch = True
        self.search.setText("")
        self.config = self.getConfig()
        self.allGroups = self.getAllGroups()
        self.defaultGroups = self.db.getDefaultGroups()
        self.userGroups = self.getUserGroups()

        # Update dictionary groups combo box
        if hasattr(self, "dictGroups"):
            self.dictGroups.blockSignals(True)
            newDictGroupsCombo = self.setupDictGroups()
            if hasattr(self, "toolbar"):
                self.toolbar.replaceWidget(self.dictGroups, newDictGroupsCombo)
            self.dictGroups.deleteLater()
            self.dictGroups = newDictGroupsCombo
        else:
            self.dictGroups = self.setupDictGroups()

        # Update search type combo box (to reflect any language-specific search options if they were added)
        if hasattr(self, "sType"):
            self.sType.blockSignals(True)
            newSType = self.setupSearchType()
            if hasattr(self, "toolbar"):
                self.toolbar.replaceWidget(self.sType, newSType)
            self.sType.deleteLater()
            self.sType = newSType
        else:
            self.sType = self.setupSearchType()

        # Fixed sizes for header elements
        header_height = 36
        for widget in [self.dictGroups, self.sType]:
            widget.setFixedHeight(header_height)
        self.dictGroups.setFixedWidth(120)
        self.sType.setFixedWidth(100)

        previouslyOnTop = self.alwaysOnTop
        self.alwaysOnTop = self.config["dictAlwaysOnTop"]
        if previouslyOnTop != self.alwaysOnTop:
            self.setAlwaysOnTop()
        self.setAlwaysOnTop()

        if not self.config["showTarget"]:
            self.currentTarget.hide()
            self.targetLabel.hide()
        else:
            self.targetLabel.show()
            self.currentTarget.show()

        if self.config["tooltips"]:
            self.dictGroups.setToolTip("Select the dictionary group.")

        self.resetDict(willSearch, terms)

    def resetDict(self, willSearch, terms):
        newDict = MIDict(self, self.db, self.addonPath, terms)
        newDict.setSType(self.sType)
        html, url = self.getHTMLURL(willSearch)
        newDict.loadHTMLURL(html, url)
        newDict.setSType(self.sType)
        if self.dict.addWindow and self.dict.addWindow.scrollArea.isVisible():  # ty:ignore[unresolved-attribute]
            self.dict.addWindow.saveSizeAndPos()  # ty:ignore[unresolved-attribute]
            self.dict.addWindow.scrollArea.close()  # ty:ignore[unresolved-attribute]
            self.dict.addWindow.scrollArea.deleteLater()  # ty:ignore[unresolved-attribute]
        self.currentTarget.setText("")
        self.dict.currentEditor = False
        self.dict.reviewer = False
        self.mainLayout.replaceWidget(self.dict, newDict)
        self.dict.close()
        self.dict.deleteLater()
        self.dict = newDict
        if self.config["deinflect"]:
            self.dict.deinflect = True
        else:
            self.dict.deinflect = False

    def saveSizeAndPos(self):
        pos = self.pos()
        x = pos.x()
        y = pos.y()
        size = self.size()
        width = size.width()
        height = size.height()
        posSize = [x, y, width, height]
        self.writeConfig("dictSizePos", posSize)

    def getUserGroups(self):
        groups = self.config.get("DictionaryGroups", {})
        userGroups = {}
        for name, group in groups.items():
            dicts = group.get("dictionaries", [])
            userGroups[name] = {}
            userGroups[name]["dictionaries"] = self.db.getUserGroups(dicts)
            userGroups[name]["customFont"] = group.get("customFont", False)
            userGroups[name]["font"] = group.get("font", False)
        return userGroups

    def getConfig(self):
        from anki_dictionary.utils.config import get_addon_config

        config = get_addon_config()
        # Ensure required keys exist with defaults
        if "DictionaryGroups" not in config:
            config["DictionaryGroups"] = {}
        if "currentGroup" not in config:
            config["currentGroup"] = "All"
        if "searchMode" not in config:
            config["searchMode"] = "Forward"
        return config

    def setupView(self):
        layoutV = QVBoxLayout()

        # Unified Toolbar
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setSpacing(8)

        # Left side: Combo boxes and Search
        self.toolbar.addWidget(self.dictGroups)
        self.toolbar.addWidget(self.sType)
        self.toolbar.addWidget(self.search)

        # Action buttons
        self.toolbar.addWidget(self.searchButton)
        self.toolbar.addWidget(self.openSB)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.toolbar.addWidget(line)

        # Utility buttons
        self.toolbar.addWidget(self.minusB)
        self.toolbar.addWidget(self.plusB)
        self.toolbar.addWidget(self.tabB)
        self.toolbar.addWidget(self.histB)
        self.toolbar.addWidget(self.conjToggler)
        self.toolbar.addWidget(self.themeSettings)
        self.toolbar.addWidget(self.setB)

        # Target Info (if enabled)
        if self.config["showTarget"]:
            self.toolbar.addSpacing(10)
            self.targetLabel.setStyleSheet("font-weight: bold; opacity: 0.7;")
            self.toolbar.addWidget(self.targetLabel)
            self.currentTarget.setStyleSheet("font-weight: medium;")
            self.toolbar.addWidget(self.currentTarget)

        self.toolbar.addStretch()

        # Fixed sizes for header elements
        header_height = 36
        for widget in [self.dictGroups, self.sType, self.search]:
            widget.setFixedHeight(header_height)

        self.dictGroups.setFixedWidth(120)
        self.sType.setFixedWidth(100)
        self.search.setMinimumWidth(100)
        self.search.setMaximumWidth(250)

        # Set fixed size for all toolbar buttons
        btn_size = 36
        for btn in [
            self.searchButton,
            self.openSB,
            self.minusB,
            self.plusB,
            self.tabB,
            self.histB,
            self.conjToggler,
            self.themeSettings,
            self.setB,
        ]:
            btn.setFixedSize(btn_size, btn_size)

        layoutV.addLayout(self.toolbar)

        # Content Area
        layoutV.addWidget(self.dict)

        layoutV.setContentsMargins(0, 0, 0, 0)
        layoutV.setSpacing(0)

        return layoutV

    def toggleMenuBar(self, vertical):
        # We've improved the layout to be multi-line by default,
        # so we can simplify or remove the responsive toggle if it causes issues.
        pass

    def resizeEvent(self, event):  # ty:ignore[invalid-method-override]
        # Simplified resize event
        event.accept()

    def setupSearchButton(self):
        searchB = SVGPushButton(36, 36)
        self.setSvg(searchB, "search")
        searchB.clicked.connect(self.initSearch)
        return searchB

    def setupOpenSB(self):
        openSB = SVGPushButton(36, 36)
        self.setSvg(openSB, "sidebaropen")
        openSB.clicked.connect(self.toggleSB)
        return openSB

    def toggleSB(self):
        if not self.openSB.opened:
            self.openSB.opened = True
            self.setSvg(self.openSB, "sidebarclose")
        else:
            self.openSB.opened = False
            self.setSvg(self.openSB, "sidebaropen")
        self.dict.eval("openSidebar()")

    def setupTabMode(self):
        TabMode = SVGPushButton(36, 36)
        if self.config["onetab"]:
            TabMode.singleTab = True  # ty:ignore[unresolved-attribute]
            icon = "onetab"
        else:
            TabMode.singleTab = False  # ty:ignore[unresolved-attribute]
            icon = "tabs"
        self.setSvg(TabMode, icon)
        TabMode.clicked.connect(self.toggleTabMode)
        return TabMode

    def toggleTabMode(self):
        try:
            if self.tabB.singleTab:
                self.tabB.singleTab = False
                self.setSvg(self.tabB, "tabs")
                self.writeConfig("onetab", False)
            else:
                self.tabB.singleTab = True
                self.setSvg(self.tabB, "onetab")
                self.writeConfig("onetab", True)

        except Exception as e:
            logger.error(f"Error in toggleTabMode: {e}")
            import traceback

            traceback.print_exc()

    def setupConjugationMode(self):
        conjugationMode = SVGPushButton(36, 36)
        if self.config["deinflect"]:
            self.dict.deinflect = True
            icon = "conjugation"
        else:
            self.dict.deinflect = False
            icon = "closedcube"
        self.setSvg(conjugationMode, icon)
        conjugationMode.clicked.connect(self.toggleConjugationMode)
        return conjugationMode

    def setupOpenHistory(self):
        history = SVGPushButton(36, 36)
        self.setSvg(history, "history")
        history.clicked.connect(self.openHistory)
        return history

    def openHistory(self):
        if not self.historyBrowser.isVisible():
            self.historyBrowser.show()

    def toggleConjugationMode(self):
        if not self.dict.deinflect:
            self.setSvg(self.conjToggler, "conjugation")
            self.dict.deinflect = True
            self.writeConfig("deinflect", True)

        else:
            self.setSvg(self.conjToggler, "closedcube")
            self.dict.deinflect = False
            self.writeConfig("deinflect", False)

    def setTheme(self):
        self.theme_editor.exec()
        # The theme editor might have already triggered a refresh,
        # but we call it here to be sure, with reload_html=True
        # because the user actually changed the theme.
        self.refresh_application_theme(reload_html=True)

    def setSvg(self, widget, name):
        theme_color = theme_controller.load_color(self.theme_manager, "header_text")
        return widget.setSvg(join(self.iconpath, name + ".svg"), theme_color.name())

    def setAllIcons(self):
        self.setSvg(self.setB, "settings")
        self.setSvg(self.plusB, "plus")
        self.setSvg(self.minusB, "minus")
        self.setSvg(self.histB, "history")
        self.setSvg(self.searchButton, "search")
        self.setSvg(self.themeSettings, "themesettings")
        self.setSvg(self.tabB, self.getTabStatus())
        self.setSvg(self.openSB, self.getSBStatus())
        self.setSvg(self.conjToggler, self.getConjStatus())

    def getConjStatus(self):
        if self.dict.deinflect:
            return "conjugation"
        return "closedcube"

    def getSBStatus(self):
        if self.openSB.opened:
            return "sidebarclose"
        return "sidebaropen"

    def getTabStatus(self):
        if self.tabB.singleTab:
            return "onetab"
        return "tabs"

    def setupThemes(self):
        themeButton = SVGPushButton(36, 36)
        # nightToggle.day = self.config['day']
        # themeButton.applied.connect(self.refresh_application_theme)
        self.setSvg(themeButton, "themesettings")
        themeButton.clicked.connect(self.setTheme)
        return themeButton

    def setupOpenSettings(self):
        settings = SVGPushButton(36, 36)
        self.setSvg(settings, "settings")
        settings.clicked.connect(self.openDictionarySettings)
        return settings

    def openDictionarySettings(self):
        if not self.mw.dictSettings:
            self.mw.dictSettings = SettingsGui(
                self.mw, self.addonPath, self.openDictionarySettings
            )
        self.mw.dictSettings.show()
        if self.mw.dictSettings.windowState() == Qt.WindowState.WindowMinimized:
            # Window is minimised. Restore it.
            self.mw.dictSettings.setWindowState(Qt.WindowState.WindowNoState)
        self.mw.dictSettings.setFocus()
        self.mw.dictSettings.activateWindow()

    def setupPlus(self):
        plusB = SVGPushButton(36, 36)
        self.setSvg(plusB, "plus")
        plusB.clicked.connect(self.incFont)
        return plusB

    def setupMinus(self):
        minusB = SVGPushButton(36, 36)
        self.setSvg(minusB, "minus")
        minusB.clicked.connect(self.decFont)
        return minusB

    def decFont(self):
        self.dict.eval("scaleFont(false)")

    def incFont(self):
        self.dict.eval("scaleFont(true)")

    def alignCenter(self, dictGroups):
        for i in range(0, dictGroups.count()):
            dictGroups.model().item(i).setTextAlignment(Qt.AlignmentFlag.alignCenter)  # ty:ignore[unresolved-attribute]

    def setupDictGroups(self, dictGroups=False):
        if not dictGroups:
            dictGroups = QComboBox()
            dictGroups.setFixedHeight(30)
            dictGroups.setFixedWidth(80)
            dictGroups.setContentsMargins(0, 0, 0, 0)
        ug = sorted(list(self.userGroups.keys()))
        dictGroups.addItems(ug)
        dictGroups.addItem("──────")
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)  # ty:ignore[unresolved-attribute]
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(  # ty:ignore[unresolved-attribute]
            Qt.AlignmentFlag.AlignCenter
        )
        defaults = ["All", "Images"]
        if self.config.get("llm_enabled", False):
            defaults.append("LLM")
        if self.config.get("forvo_enabled", False):
            defaults.append("Forvo")
        dictGroups.addItems(defaults)
        dictGroups.addItem("──────")
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)  # ty:ignore[unresolved-attribute]
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(  # ty:ignore[unresolved-attribute]
            Qt.AlignmentFlag.AlignCenter
        )
        dg = sorted(list(self.defaultGroups.keys()))
        dictGroups.addItems(dg)
        current = self.config["currentGroup"]
        if current in dg or current in ug or current in defaults:
            dictGroups.setCurrentText(current)
        dictGroups.currentIndexChanged.connect(
            lambda: self.writeConfig("currentGroup", dictGroups.currentText())
        )
        return dictGroups

    def setupSearchType(self):
        searchTypes = QComboBox()
        searchTypes.addItems(self.searchOptions)

        # Add tooltips for each search option to help users understand how they work
        search_option_tooltips = {
            "Forward": "Find words starting with your search term.",
            "Backward": "Find words ending with your search term (matches words with at least one character before the term).",
            "Exact": "Find words that match your search term exactly.",
            "Anywhere": "Find words containing your search term anywhere in the headword.",
            "Definition": "Search for your term within the dictionary definitions.",
            "Example": "Search for your term within example sentences (looks for text inside 「...」 markers).",
            "Pronunciation": "Find words with pronunciations starting with your search term.",
        }

        for i, option in enumerate(self.searchOptions):
            tooltip = search_option_tooltips.get(option, "")
            if tooltip:
                searchTypes.setItemData(i, tooltip, Qt.ItemDataRole.ToolTipRole)

        current = self.config["searchMode"]
        if current in self.searchOptions:
            searchTypes.setCurrentText(current)
        searchTypes.setFixedHeight(30)
        searchTypes.setFixedWidth(80)
        searchTypes.setContentsMargins(0, 0, 0, 0)
        searchTypes.currentIndexChanged.connect(
            lambda: self.writeConfig("searchMode", searchTypes.currentText())
        )
        return searchTypes

    def writeConfig(self, attribute, value):
        newConfig = self.getConfig()
        newConfig[attribute] = value
        # Use our safe config utility instead of direct addon manager call
        from anki_dictionary.utils.config import save_addon_config

        save_addon_config(newConfig)
        self.reloadConfig(newConfig)

    def getSelectedDictGroup(self):
        cur = self.dictGroups.currentText()
        if cur in self.userGroups:
            return self.userGroups[cur]
        if cur == "All":
            return self.allGroups
        if cur == "Images":
            return {
                "dictionaries": [{"dict": "Images", "lang": ""}],
                "customFont": False,
                "font": False,
            }
        if cur == "LLM":
            return {
                "dictionaries": [{"dict": "LLM", "lang": ""}],
                "customFont": False,
                "font": False,
            }
        if cur == "Forvo":
            return {
                "dictionaries": [{"dict": "Forvo", "lang": ""}],
                "customFont": False,
                "font": False,
            }

        if cur in self.defaultGroups:
            return self.defaultGroups[cur]

    def ensureVisible(self):
        if not self.isVisible():
            self.show()
        if self.windowState() == Qt.WindowState.WindowMinimized:
            self.setWindowState(Qt.WindowState.WindowNoState)
        self.setFocus()
        self.activateWindow()

    def cleanTermBrackets(self, term):
        return re.sub(
            r"(?:\[.*\])|(?:\(.*\))|(?:《.*》)|(?:（.*）)|\(|\)|\[|\]|《|》|（|）",
            "",
            term,
        )[:30]

    def initSearch(self, term=False):
        self.ensureVisible()
        if term is False:
            term = self.search.text()
            term = term.strip()
        term = term.strip()
        term = self.cleanTermBrackets(term)
        if term == "":
            return

        if self.config.get("auto_select_dict_group", True):
            from anki_dictionary.utils.script_detector import find_matching_group

            installed_langs = self.db.getCurrentDbLangs()
            language_defaults = self.config.get("language_defaults", {})
            match = find_matching_group(
                term,
                self.userGroups,
                self.defaultGroups,
                installed_langs=installed_langs,
                language_defaults=language_defaults,
            )
            if match is not None:
                idx = self.dictGroups.findText(match)
                if idx >= 0:
                    self.dictGroups.blockSignals(True)
                    self.dictGroups.setCurrentIndex(idx)
                    self.writeConfig("currentGroup", self.dictGroups.currentText())
                    self.dictGroups.blockSignals(False)

        selectedGroup = self.getSelectedDictGroup()
        self.search.setText(term.strip())
        self.addToHistory(term)
        self.dict.addNewTab(term, selectedGroup)
        self.search.setFocus()

    def addToHistory(self, term):
        date = str(datetime.date.today())
        self.historyModel.insertRows(term=term, date=date)
        self.saveHistory()

    def saveHistory(self):
        path = join(self.mw.col.media.dir(), "_searchHistory.json")
        with codecs.open(path, "w", "utf-8") as outfile:  # ty:ignore[deprecated]
            json.dump(self.historyModel.history, outfile, ensure_ascii=False)
        return

    def getHistory(self):
        path = join(self.mw.col.media.dir(), "_searchHistory.json")
        try:
            if exists(path):
                with open(path, encoding="utf-8") as histFile:
                    return json.loads(histFile.read())
            else:
                # Create empty search history file if it doesn't exist
                empty_history = []
                with codecs.open(path, "w", "utf-8") as outfile:  # ty:ignore[deprecated]
                    json.dump(empty_history, outfile, ensure_ascii=False)
                return empty_history
        except Exception as e:
            logger.warning(f"Could not load search history: {e}")
            return []

    def updateFieldsSetting(self, dictName, fields):
        clean_name = self.db.cleanDictName(dictName)
        logger.debug(f"Updating fields for {dictName} (clean: {clean_name}): {fields}")
        self.db.setFieldsSetting(clean_name, json.dumps(fields, ensure_ascii=False))

    def updateAddType(self, dictName, addType):
        clean_name = self.db.cleanDictName(dictName)
        logger.debug(
            f"Updating addType for {dictName} (clean: {clean_name}): {addType}"
        )
        self.db.setAddType(clean_name, addType)

    def setupSearch(self):
        searchBox = QLineEdit()
        searchBox.setFixedHeight(30)
        searchBox.setFixedWidth(100)
        searchBox.returnPressed.connect(self.initSearch)
        searchBox.setContentsMargins(0, 0, 0, 0)
        return searchBox

    def getMacOtherStyles(self):
        return """
            QLabel {color: black;}
            QLineEdit {color: black; background: white;} 
            QPushButton {border: 1px solid black; border-radius: 5px; color: black; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);} 
            QPushButton:hover{background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver); border-right: 2px solid black; border-bottom: 2px solid black;}"
            """

    def getOtherStyles(self):
        return """
            QLabel {color: white;}
            QLineEdit {color: white; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);} 
            QPushButton {border: 1px solid gray; border-radius: 5px; color: white; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);} 
            QPushButton:hover{background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black); border: 1px solid white;}"
            """

    def getMacComboStyle(self):
        return (
            """
QComboBox {color: black; border-radius: 3px; border: 1px solid black;}
QComboBox:hover {border: 1px solid black;}
QComboBox:editable {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
}

QComboBox:!editable, QComboBox::drop-down:editable {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);

}

QComboBox:!editable:on, QComboBox::drop-down:editable:on {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
}

QComboBox:on { 
    padding-top: 3px;
    padding-left: 4px;

}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    max-width:20px;
    border-top-right-radius: 3px; 
    border-bottom-right-radius: 3px;

}


QComboBox QAbstractItemView 
    {
    min-width: 130px;
    }

QCombobox:selected{
    background: white;
}

QComboBox::down-arrow {
    image: url("""
            + join(self.iconpath, "down.svg").replace("\\", "/")
            + """);
}

QComboBox::down-arrow:on { 
    top: 1px;
    left: 1px;
}

QComboBox QAbstractItemView{ width: 130px !important; background: white; border: 0px;color:black; selection-background-color: silver;}

QAbstractItemView:selected {
background:white;}

QScrollBar:vertical {              
        border: 1px solid black;
        background:white;
        width:17px;    
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
    }
    QScrollBar::add-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
        height: 0 px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }"""
        )

    def getTableStyle(self):
        return """
        QAbstractItemView{color:white;}

        QHeaderView {
            background: black;
            }
        QHeaderView::section
        {
            color:white;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
            border: 1px solid white;
        }
         QTableWidget, QTableView {
         color:white;
         background-color: #272828;
         selection-background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     }
        QTableWidget QTableCornerButton::section, QTableView QTableCornerButton::section{
         background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
         border: 1px solid white;
     }

        """


class DictSVG(QSvgWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QSvgWidget.__init__(self, parent)

    def mousePressEvent(self, ev):  # ty:ignore[invalid-method-override]
        self.clicked.emit()


class SVGPushButton(QPushButton):
    def __init__(self, width, height):
        super().__init__()
        self.setFixedSize(width, height)
        self.layout = QHBoxLayout(self)  # ty:ignore[invalid-assignment]
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(0)
        self.svgWidget = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setSvg(self, svgPath, color="#ffffff"):
        if self.svgWidget:
            self.layout.removeWidget(self.svgWidget)  # ty:ignore[unresolved-attribute]
            self.svgWidget.deleteLater()

        # Read SVG file and replace color placeholders with the theme color
        try:
            with open(svgPath, encoding="utf-8") as f:
                svg_data = f.read()
                svg_data = svg_data.replace('fill="currentColor"', f'fill="{color}"')
                svg_data = svg_data.replace(
                    'stroke="currentColor"', f'stroke="{color}"'
                )
                svg_data = svg_data.replace('fill="{header_text}"', f'fill="{color}"')

                # If neither is found, try to force a fill on paths
                if 'fill="' not in svg_data:
                    svg_data = svg_data.replace("<path ", f'<path fill="{color}" ')

            self.svgWidget = QSvgWidget()
            self.svgWidget.load(svg_data.encode("utf-8"))
            self.svgWidget.setFixedSize(self.width() - 12, self.height() - 12)
            self.layout.addWidget(self.svgWidget, 0, Qt.AlignmentFlag.AlignCenter)  # ty:ignore[unresolved-attribute]
        except Exception as e:
            logger.error(f"Error loading SVG {svgPath}: {e}")
