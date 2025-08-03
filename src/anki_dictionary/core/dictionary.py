# -*- coding: utf-8 -*-
#

from aqt.utils import (
    shortcut,
    saveGeom,
    saveSplitter,
    showInfo,
    askUser,
    ensureWidgetInScreenBoundaries,
)
import json
import sys
import math
import base64
from anki.hooks import runHook
from aqt.qt import *
from PyQt6.QtCore import QUrl
from aqt.utils import openLink, tooltip
from anki.utils import is_mac, is_win, is_lin
from anki.lang import _
from aqt.webview import AnkiWebView
import re
from shutil import copyfile
import os, shutil
from os.path import join, exists, dirname
import ssl
import subprocess
from typing import List, Dict, Optional, Tuple, Any, Union

try:
    from PIL import Image
except ImportError:
    # Fallback for systems where PIL is not available
    Image = None

from ..utils.history import HistoryBrowser, HistoryModel
from aqt.editor import Editor
from ..exporters.card_exporter import CardExporter
import time
from . import database as dictdb


# Suppress Qt SVG warnings about path data
def qt_message_handler(mode, context, message):
    if "Invalid path data; path truncated" in message:
        return  # Suppress this specific warning
    # Let other messages through normally
    if mode == QtMsgType.QtWarningMsg:
        if not ("Invalid path data" in message or "path truncated" in message):
            print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")


# Install the message handler
qInstallMessageHandler(qt_message_handler)
import aqt
from ..integrations.japanese import miJHandler
from urllib.request import Request, urlopen
import requests
import urllib.request
from ..integrations import image_search as duckduckgoimages
from ..ui.settings.settings_gui import SettingsGui
import datetime
import codecs
from ..integrations.forvo import Forvo
import ntpath
from ..utils.common import miInfo
from PyQt6.QtSvgWidgets import QSvgWidget
from ..ui.dialogs.theme_editor import *
from ..ui.themes import *
from PyQt6.QtWebEngineWidgets import QWebEngineView


class MIDict(AnkiWebView):
    def __init__(self, dictInt, db, path, terms=False):
        AnkiWebView.__init__(self)
        self.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
        )
        self.terms = terms
        self.dictInt = dictInt
        self.config = self.dictInt.getConfig()
        self.jSend = self.config["jReadingEdit"]
        self.maxW = self.config["maxWidth"]
        self.maxH = self.config["maxHeight"]
        self.onBridgeCmd = self.handleDictAction
        self.db = db
        self.termHeaders = self.formatTermHeaders(self.db.getTermHeaders())
        self.dupHeaders = self.db.getDupHeaders()
        self.sType = False
        self.radioCount = 0
        self.homeDir = path
        # Set up root addon temp directory path
        self.addon_root = dirname(dirname(dirname(dirname(__file__))))
        self.temp_dir = join(self.addon_root, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.conjugations = self.loadConjugations()
        self.deinflect = True
        self.addWindow = False
        self.currentEditor = False
        self.reviewer = False
        self.threadpool = QThreadPool()
        self.customFontsLoaded = []

    def resetConfiguration(self, config):
        self.config = config
        self.jSend = self.config["jReadingEdit"]
        self.maxW = self.config["maxWidth"]
        self.maxH = self.config["maxHeight"]

    def showGoogleForvoMessage(self, message):
        miInfo(message, level="err")

    def loadImageResults(self, results):
        """
        Loads image search results into the dictionary window
            Args:
                html: HTML string containing image gallery markup
                idName: Unique identifier for the image container
        """
        html, idName = results
        # Use json.dumps to safely encode the HTML for JavaScript
        escaped_html = json.dumps(html)
        escaped_idName = json.dumps(idName)
        self.eval("loadImageForvoHtml(%s, %s);" % (escaped_html, escaped_idName))

    def downloadImage(self, url):
        try:
            filename = str(time.time()).replace(".", "") + ".png"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            file = urlopen(req).read()
            image = QImage()
            image.loadFromData(file)
            if not image.isNull():
                image = image.scaled(
                    QSize(self.config["maxWidth"], self.config["maxHeight"]),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image.save(filename)
                return '<img src="' + filename + '">'
        except:
            return ""

    def loadHTMLURL(self, html, url):
        self.page().setHtml(html, url)

    def getBase64Icon(self, icon_name):
        """Convert icon to base64 data URL for embedding in HTML"""
        try:
            icon_path = join(self.addon_root, "assets", "icons", icon_name)
            with open(icon_path, "rb") as icon_file:
                icon_data = icon_file.read()
                icon_base64 = base64.b64encode(icon_data).decode('utf-8')
                # Determine MIME type based on file extension
                if icon_name.endswith('.png'):
                    mime_type = 'image/png'
                elif icon_name.endswith('.svg'):
                    mime_type = 'image/svg+xml'
                else:
                    mime_type = 'image/png'  # Default fallback
                return f"data:{mime_type};base64,{icon_base64}"
        except Exception as e:
            print(f"Error loading icon {icon_name}: {e}")
            return ""

    def formatTermHeaders(self, ths):
        formattedHeaders = {}
        if not ths:
            return None
        for dictname in ths:
            headerString = ""
            sbHeaderString = ""
            for header in ths[dictname]:
                if header == "term":
                    headerString += '◳f<span class="term mainword">◳t</span>◳b'
                    sbHeaderString += '◳f<span class="listTerm">◳t</span>◳b'
                elif header == "altterm":
                    headerString += '◳x<span class="altterm  mainword">◳a</span>◳y'
                    sbHeaderString += '◳x<span class="listAltTerm">◳a</span>◳y'
                elif header == "pronunciation":
                    headerString += '<span class="pronunciation">◳p</span>'
                    sbHeaderString += '<span class="listPronunciation">◳p</span>'
            formattedHeaders[dictname] = [headerString, sbHeaderString]
        return formattedHeaders

    def setSType(self, sType):
        self.sType = sType

    def loadConjugations(self):
        langs = self.db.getCurrentDbLangs()
        conjugations = {}
        for lang in langs:
            filePath = join(
                self.homeDir, "user_files", "db", "conjugation", "%s.json" % lang
            )
            if not os.path.exists(filePath):
                filePath = join(
                    self.homeDir,
                    "user_files",
                    "dictionaries",
                    lang,
                    "conjugations.json",
                )
                if not os.path.exists(filePath):
                    continue
            with open(filePath, "r", encoding="utf-8") as conjugationsFile:
                conjugations[lang] = json.loads(conjugationsFile.read())
        return conjugations

    def cleanTerm(self, term):
        return (
            term.replace("'", "'")
            .replace("%", "")
            .replace("_", "")
            .replace("「", "")
            .replace("」", "")
        )

    def getFontFamily(self, group):
        if not group["font"]:
            return " "
        if group["customFont"]:
            return ' style="font-family:' + re.sub(r"\..*$", "", group["font"]) + ';" '
        else:
            return ' style="font-family:' + group["font"] + ';" '

    def injectFont(self, font):
        name = re.sub(r"\..*$", "", font)
        self.eval("addCustomFont('%s', '%s');" % (font, name))

    def getTabMode(self):
        if self.dictInt.tabB.singleTab:
            return "true"
        return "false"

    def getHTMLResult(self, term, selectedGroup):
        singleTab = self.getTabMode()
        cleaned = self.cleanTerm(term)
        font = self.getFontFamily(selectedGroup)
        dictDefs = self.config["dictSearch"]
        maxDefs = self.config["maxSearch"]
        html = self.prepareResults(
            self.db.searchTerm(
                term,
                selectedGroup,
                self.conjugations,
                self.sType.currentText(),
                self.deinflect,
                str(dictDefs),
                maxDefs,
            ),
            cleaned,
            font,
        )
        html = html.replace("\n", "")
        return html, cleaned, singleTab

    def addNewTab(self, term, selectedGroup):
        if (
            selectedGroup["customFont"]
            and selectedGroup["font"] not in self.customFontsLoaded
        ):
            self.customFontsLoaded.append(selectedGroup["font"])
            self.injectFont(selectedGroup["font"])
        html, cleaned, singleTab = self.getHTMLResult(term, selectedGroup)
        self.eval(
            "addNewTab('%s', '%s', %s);"
            % (html.replace("\r", "<br>").replace("\n", "<br>"), cleaned, singleTab)
        )

    def addResultWrappers(self, results):
        for idx, result in enumerate(results):
            if "dictionaryTitleBlock" not in result:
                results[idx] = '<div class="definitionBlock">' + result + "</div>"
        return results

    def escapePunctuation(self, term):
        return re.sub(r"([.*+(\[\]{}\\?)!])", "\\\1", term)

    def highlightTarget(self, text, term):
        if self.config["highlightTarget"]:
            if not isinstance(text, str):
                text = str(text) if text is not None else ""
            try:
                # Split text into HTML tags and content
                parts = re.split(r"(<[^>]*>)", text)

                # Only apply highlighting to non-tag parts
                for i in range(0, len(parts), 2):  # Process only non-tag parts
                    if parts[i]:  # Skip empty strings
                        # For Japanese text, we don't need word boundaries
                        if any(
                            "\u4e00" <= c <= "\u9fff"
                            or "\u3040" <= c <= "\u309f"
                            or "\u30a0" <= c <= "\u30ff"
                            for c in term
                        ):
                            pattern = "(" + self.escapePunctuation(term) + ")"
                        else:
                            # For non-Japanese text, keep word boundaries
                            pattern = r"\b(" + self.escapePunctuation(term) + r")\b"

                        parts[i] = re.sub(
                            pattern, r'<span class="targetTerm">\1</span>', parts[i]
                        )

                return "".join(parts)
            except Exception as e:
                print(f"Error during highlightTarget: {e}")
                return text  # Fallback to the original text
        return text

    def highlightExamples(self, text):
        if self.config["highlightSentences"]:
            return re.sub(
                r"「([^」]+)」(?![^<]*>)",
                r'<span class="exampleSentence">「\1」</span>',
                text,
            )
        return text

    def getSideBar(self, results, term, font, frontBracket, backBracket):
        html = "<div" + font + 'class="definitionSideBar"><div class="innerSideBar">'
        dictCount = 0
        entryCount = 0
        for dictName, dictResults in results.items():
            if dictName == "Google Images" or dictName == "Forvo":
                html += (
                    '<div data-index="'
                    + str(dictCount)
                    + '" class="listTitle">'
                    + dictName
                    + '</div><ol class="foundEntriesList"><li data-index="'
                    + str(entryCount)
                    + '">'
                    + self.getPreparedTermHeader(
                        dictName,
                        frontBracket,
                        backBracket,
                        term,
                        term,
                        term,
                        term,
                        True,
                    )
                    + "</li></ol>"
                )
                entryCount += 1
                dictCount += 1
                continue
            html += (
                '<div data-index="'
                + str(dictCount)
                + '" class="listTitle">'
                + dictName
                + '</div><ol class="foundEntriesList">'
            )
            dictCount += 1
            for idx, entry in enumerate(dictResults):
                html += (
                    '<li data-index="'
                    + str(entryCount)
                    + '">'
                    + self.getPreparedTermHeader(
                        dictName,
                        frontBracket,
                        backBracket,
                        term,
                        entry["term"],
                        entry["altterm"],
                        entry["pronunciation"],
                        True,
                    )
                    + "</li>"
                )
                entryCount += 1
            html += "</ol>"
        return (
            html
            + '<br></div><div class="resizeBar" onmousedown="hresize(event)"></div></div>'
        )

    def getPreparedTermHeader(
        self,
        dictName,
        frontBracket,
        backBracket,
        target,
        term,
        altterm,
        pronunciation,
        sb=False,
    ):
        altFB = frontBracket
        altBB = backBracket
        if pronunciation == term:
            pronunciation = ""
        if altterm == term:
            altterm = ""
        if altterm == "":
            altFB = ""
            altBB = ""
        if not self.termHeaders or (dictName == "Google Images" or dictName == "Forvo"):
            if sb:
                header = '◳f<span class="term mainword">◳t</span>◳b◳x<span class="altterm  mainword">◳a</span>◳y<span class="pronunciation">◳p</span>'
            else:
                header = '◳f<span class="listTerm">◳t</span>◳b◳x<span class="listAltTerm">◳a</span>◳y<span class="listPronunciation">◳p</span>'
        else:
            if sb:
                header = self.termHeaders[dictName][1]
            else:
                header = self.termHeaders[dictName][0]

        return (
            header.replace("◳t", self.highlightTarget(term, target))
            .replace("◳a", self.highlightTarget(altterm, target))
            .replace("◳p", self.highlightTarget(pronunciation, target))
            .replace("◳f", frontBracket)
            .replace("◳b", backBracket)
            .replace("◳x", altFB)
            .replace("◳y", altBB)
        )

    def prepareResults(self, results, term, font):
        frontBracket = self.config["frontBracket"]
        backBracket = self.config["backBracket"]
        if len(results) > 0:
            html = self.getSideBar(results, term, font, frontBracket, backBracket)
            html += '<div class="mainDictDisplay">'
            dictCount = 0
            entryCount = 0
            imgTooltip = ""
            clipTooltip = ""
            sendTooltip = ""
            if self.config["tooltips"]:
                imgTooltip = ' title="Add this definition, or any selected text and this definition\'s header to the card exporter (opens the card exporter if it is not yet opened)." '
                clipTooltip = ' title="Copy this definition, or any selected text to the clipboard." '
                sendTooltip = " title=\"Send this definition, or any selected text and this definition's header to the card exporter to this dictionary's target fields. It will send it to the current target window, be it an Editor window, or the Review window.\" "
            for dictName, dictResults in results.items():
                if dictName == "Google Images":
                    html += self.getGoogleDictionaryResults(
                        term, dictCount, frontBracket, backBracket, entryCount, font
                    )
                    dictCount += 1
                    entryCount += 1
                    continue
                if dictName == "Forvo":
                    html += self.getForvoDictionaryResults(
                        term, dictCount, frontBracket, backBracket, entryCount, font
                    )
                    dictCount += 1
                    entryCount += 1
                    continue
                duplicateHeader = self.getDuplicateHeaderCB(dictName)
                overwrite = self.getOverwriteChecks(dictCount, dictName)
                select = self.getFieldChecks(dictName)
                html += (
                    '<div data-index="'
                    + str(dictCount)
                    + '" class="dictionaryTitleBlock"><div  '
                    + font
                    + '  class="dictionaryTitle">'
                    + dictName.replace("_", " ")
                    + '</div><div class="dictionarySettings">'
                    + duplicateHeader
                    + overwrite
                    + select
                    + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
                )
                dictCount += 1

                for idx, entry in enumerate(dictResults):
                    html += (
                        '<div data-index="'
                        + str(entryCount)
                        + '" class="termPronunciation"><span '
                        + font
                        + ' class="tpCont">'
                        + self.getPreparedTermHeader(
                            dictName,
                            frontBracket,
                            backBracket,
                            term,
                            entry["term"],
                            entry["altterm"],
                            entry["pronunciation"],
                        )
                        + ' <span class="starcount">'
                        + entry["starCount"]
                        + '</span></span><div class="defTools"><div onclick="ankiExport(event, \''
                        + dictName
                        + '\')" class="ankiExportButton"><img '
                        + imgTooltip
                        + ' src="' + self.getBase64Icon("anki.png") + '"></div><div onclick="clipText(event)" '
                        + clipTooltip
                        + ' class="clipper">✂</div><div '
                        + sendTooltip
                        + " onclick=\"sendToField(event, '"
                        + dictName
                        + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div'
                        + font
                        + ' class="definitionBlock">'
                        + self.highlightTarget(
                            self.highlightExamples(entry["definition"]), term
                        )
                        + "</div>"
                    )
                    entryCount += 1

        else:
            html = (
                '<style>.noresults{font-family: Arial;}.vertical-center{height: 400px; width: 60%; margin: 0 auto; display: flex; justify-content: center; align-items: center;}</style> </head> <div class="vertical-center noresults"> <div align="center"> <img src="' + self.getBase64Icon("searchzero.svg") + '" width="50px" height="40px"> <h3 align="center">No dictionary entries were found for "'
                + term
                + '".</h3> </div></div>'
            )
        return html.replace("'", "\\'")

    def attemptFetchForvo(self, term, idName):
        forvo = Forvo(self.config["ForvoLanguage"])
        forvo.setTermIdName(term, idName)
        forvo.signals.resultsFound.connect(self.loadForvoResults)
        forvo.signals.noResults.connect(self.showGoogleForvoMessage)
        self.threadpool.start(forvo)
        return "Loading..."

    def loadForvoResults(self, results):
        forvoData, idName = results
        if forvoData:
            html = "<div class=\\'forvo\\'  data-urls=\\'" + forvoData + "\\'></div>"
        else:
            html = '<div class="no-forvo">No Results Found.</div>'
        self.eval(
            "loadImageForvoHtml('%s', '%s');loadForvoDict(false, '%s');"
            % (html.replace('"', '\\"'), idName, idName)
        )

    def getForvoDictionaryResults(
        self, term, dictCount, bracketFront, bracketBack, entryCount, font
    ):
        dictName = "Forvo"
        overwrite = self.getOverwriteChecks(dictCount, dictName)
        select = self.getFieldChecks(dictName)
        idName = "fcon" + str(time.time())
        self.attemptFetchForvo(term, idName)
        html = (
            '<div data-index="'
            + str(dictCount)
            + '" class="dictionaryTitleBlock"><div class="dictionaryTitle">'
            + dictName
            + '</div><div class="dictionarySettings">'
            + overwrite
            + select
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
        )
        html += (
            '<div  data-index="'
            + str(entryCount)
            + '"  class="termPronunciation"><span class="tpCont">'
            + bracketFront
            + "<span "
            + font
            + ' class="terms">'
            + self.highlightTarget(term, term)
            + "</span>"
            + bracketBack
            + ' <span></span></span><div class="defTools"><div onclick="ankiExport(event, \''
            + dictName
            + '\')" class="ankiExportButton"><img src="' + self.getBase64Icon("anki.png") + '"></div><div onclick="clipText(event)" class="clipper">✂</div><div onclick="sendToField(event, \''
            + dictName
            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div id="'
            + idName
            + '" class="definitionBlock">'
        )
        html += "Loading..."
        html += "</div>"
        return html

    def getGoogleDictionaryResults(
        self, term, dictCount, bracketFront, bracketBack, entryCount, font
    ):
        dictName = "Google Images"
        overwrite = self.getOverwriteChecks(dictCount, dictName)
        select = self.getFieldChecks(dictName)
        idName = "gcon" + str(time.time())
        html = (
            '<div data-index="'
            + str(dictCount)
            + '" class="dictionaryTitleBlock"><div class="dictionaryTitle">Google Images</div><div class="dictionarySettings">'
            + overwrite
            + select
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
        )
        html += (
            '<div  data-index="'
            + str(entryCount)
            + '" class="termPronunciation"><span class="tpCont">'
            + bracketFront
            + "<span "
            + font
            + ' class="terms">'
            + self.highlightTarget(term, term)
            + "</span>"
            + bracketBack
            + ' <span></span></span><div class="defTools"><div onclick="ankiExport(event, \''
            + dictName
            + '\')" class="ankiExportButton"><img src="' + self.getBase64Icon("anki.png") + '"></div><div onclick="clipText(event)" class="clipper">✂</div><div onclick="sendToField(event, \''
            + dictName
            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div class="definitionBlock"><div class="imageBlock" id="'
            + idName
            + '">'
            + self.getImages(term, idName)
            + "</div></div>"
        )
        return html

    def getImages(self, term, idName):
        # Track pagination offset per search term
        if not hasattr(self, "image_offsets"):
            self.image_offsets = {}

        # Initialize offset for new terms
        if term not in self.image_offsets:
            self.image_offsets[term] = 0

        # Always create a new DuckDuckGo instance for each search
        # to avoid QRunnable reuse issues
        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(term, idName)
        # Set the search offset for pagination
        imager.search_offset = self.image_offsets[term]
        # imager.setSearchRegion(self.config['googleSearchRegion'])
        # imager.setSafeSearch(self.config["safeSearch"])
        imager.signals.resultsFound.connect(self.loadImageResults)
        imager.signals.noResults.connect(self.showNoImagesMessage)
        self.threadpool.start(imager)

        return "Loading..."

    def showNoImagesMessage(self):
        tooltip("No images found")

    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        return [x.replace("\\", "\\\\") for x in urls]

    def getDuplicateHeaderCB(self, dictName: str) -> str:
        tooltip = ""
        if self.config["tooltips"]:
            tooltip = ' title="Enable this option if this dictionary has the target word\'s header within the definition. Enabling this will prevent the addon from exporting duplicate header."'
        checked = " "
        className = "checkDict" + re.sub(r"\s", "", dictName)
        if dictName in self.dupHeaders:
            num = self.dupHeaders[dictName]
            if num == 1:
                checked = " checked "
        return (
            '<div class="dupHeadCB" data-dictname="'
            + dictName
            + '">Duplicate Header:<input '
            + checked
            + tooltip
            + ' class="'
            + className
            + '" onclick="handleDupChange(this, \''
            + className
            + '\')" type="checkbox"></div>'
        )

    def maybeSearchTerms(self, terms: str) -> None:
        if self.terms:
            for t in self.terms:
                self.dictInt.initSearch(t)
            self.terms = False

    def handleDictAction(self, dAct):
        if dAct.startswith("AnkiDictionaryLoaded"):
            self.maybeSearchTerms(dAct)
        elif dAct.startswith("forvo:"):
            urls = json.loads(dAct[6:])
            self.downloadForvoAudio(urls)
        elif dAct.startswith("updateTerm:"):
            term = dAct[11:]
            self.dictInt.search.setText(term)
        elif dAct.startswith("saveFS:"):
            f1, f2 = dAct[7:].split(":")
            self.dictInt.writeConfig("fontSizes", [int(f1), int(f2)])
        elif dAct.startswith("setDup:"):
            dup, name = dAct[7:].split("◳")
            dup = int(dup)
            self.dictInt.db.setDupHeader(dup, name)
            self.dupHeaders = self.db.getDupHeaders()
        elif dAct.startswith("fieldsSetting:"):
            fields = json.loads(dAct[14:])
            if fields["dictName"] == "Google Images":
                self.dictInt.writeConfig("GoogleImageFields", fields["fields"])
            elif fields["dictName"] == "Forvo":
                self.dictInt.writeConfig("ForvoFields", fields["fields"])
            else:
                self.dictInt.updateFieldsSetting(fields["dictName"], fields["fields"])
        elif dAct.startswith("overwriteSetting:"):
            addType = json.loads(dAct[17:])
            if addType["name"] == "Google Images":
                self.dictInt.writeConfig("GoogleImageAddType", addType["type"])
            elif addType["name"] == "Forvo":
                self.dictInt.writeConfig("ForvoAddType", addType["type"])
            else:
                self.dictInt.updateAddType(addType["name"], addType["type"])
        elif dAct.startswith("clipped:"):
            text = dAct[8:]
            self.dictInt.mw.app.clipboard().setText(text.replace("<br>", "\n"))
        elif dAct.startswith("sendToField:"):
            name, text = dAct[12:].split("◳◴")
            self.sendToField(name, text)
        elif dAct.startswith("sendAudioToField:"):
            urls = dAct[17:]
            self.sendAudioToField(urls)
        elif dAct.startswith("sendImgToField:"):
            urls = dAct[15:]
            self.sendImgToField(urls)
        elif dAct.startswith("addDef:"):
            dictName, word, text = dAct[7:].split("◳◴")
            self.addDefToExportWindow(dictName, word, text)
        elif dAct.startswith("audioExport:"):
            word, urls = dAct[12:].split("◳◴")
            self.addAudioToExportWindow(word, urls)
        elif dAct.startswith("imgExport:"):
            word, urls = dAct[10:].split("◳◴")
            self.addImgsToExportWindow(word, json.loads(urls))
        elif dAct.startswith("load_more_images:"):
            search_term = dAct[17:]
            self.loadMoreImages(search_term)
        elif dAct.startswith("getMoreImages::"):
            search_term = dAct[15:]
            self.loadMoreImages(search_term)

    def loadMoreImages(self, search_term: str) -> None:
        """
        Load more images for a search term by performing a new search
        """
        # Track pagination offset per search term
        if not hasattr(self, "image_offsets"):
            self.image_offsets = {}

        # Increment offset for this term to get next page
        if search_term in self.image_offsets:
            self.image_offsets[search_term] += 15
        else:
            self.image_offsets[search_term] = 15  # Start from second page

        # Always create a new DuckDuckGo instance for each search
        # to avoid QRunnable reuse issues
        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(search_term, "load_more")
        # Set the search offset for pagination
        imager.search_offset = self.image_offsets[search_term]
        # Connect to a different handler for load more results
        imager.signals.resultsFound.connect(self.loadMoreImageResults)
        imager.signals.noResults.connect(self.showNoMoreImagesMessage)
        self.threadpool.start(imager)

    def loadMoreImageResults(self, results: Tuple[str, str]) -> None:
        """
        Handle results from load more images request
        """
        html, idName = results

        # Handle empty results
        if not html or html.strip() == "":
            self.showNoMoreImagesMessage()
            return

        # Use json.dumps to safely encode the HTML for JavaScript
        escaped_html = json.dumps(html)

        # Use the appendNewImages JavaScript function to add the new images
        try:
            js_code = f"appendNewImages({escaped_html});"
            self.eval(js_code)
        except Exception as e:
            print(f"Error in loadMoreImageResults: {e}")
            self.showNoMoreImagesMessage()

    def showNoMoreImagesMessage(self) -> None:
        """
        Show message when no more images are available
        """
        self.eval(
            "var btn = document.querySelector('.imageLoader'); if(btn) { btn.textContent = 'No more images'; btn.disabled = true; }"
        )

    def addImgsToExportWindow(self, word: str, urls: List[str]) -> None:
        self.initCardExporterIfNeeded()
        imgSeparator = ""
        imgs: List[str] = []
        rawPaths: List[str] = []
        for imgurl in urls:
            try:
                url = re.sub(r"\?.*$", "", imgurl)
                filename = (
                    str(time.time())[:-4].replace(".", "")
                    + re.sub(r"\..*$", "", url.strip().split("/")[-1])
                    + ".jpg"
                )
                fullpath = join(self.dictInt.mw.col.media.dir(), filename)
                self.saveQImage(imgurl, filename)
                rawPaths.append(fullpath)
                # imgs.append('<img ankiDict="' + filename + '">')
                imgs.append('<img src="' + filename + '">')
            except:
                continue
        if len(imgs) > 0:
            self.addWindow.addImgs(
                word, imgSeparator.join(imgs), self.getThumbs(rawPaths)
            )

    def saveQImage(self, url: str, filename: str) -> None:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
            },
        )
        file = urlopen(req).read()
        image = QImage()
        image.loadFromData(file)
        image = image.scaled(
            QSize(self.maxW, self.maxH),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image.save(filename)

    def getThumbs(self, paths: List[str]) -> QWidget:
        thumbCase = QWidget()
        thumbCase.setContentsMargins(0, 0, 0, 0)
        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0, 0, 0, 0)
        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addLayout(hLayout)
        for idx, path in enumerate(paths):
            image = QPixmap(path)
            image = image.scaled(
                QSize(50, 50),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label = QLabel("")
            label.setPixmap(image)
            label.setFixedSize(40, 40)
            hLayout.addWidget(label)
            if idx > 0 and idx % 4 == 0:
                hLayout = QHBoxLayout()
                hLayout.setContentsMargins(0, 0, 0, 0)
                vLayout.addLayout(hLayout)
        thumbCase.setLayout(vLayout)
        return thumbCase

    def addDefToExportWindow(self, dictName: str, word: str, text: str) -> None:
        self.initCardExporterIfNeeded()
        self.addWindow.addDefinition(dictName, word, text)

    def exportImage(self, pathAndName: Tuple[str, str]) -> None:
        self.dictInt.ensureVisible()
        path, name = pathAndName
        self.initCardExporterIfNeeded()
        self.addWindow.scrollArea.show()
        self.addWindow.exportImage(path, name)

    def initCardExporterIfNeeded(self) -> None:
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)

    def bulkTextExport(self, cards: List[Any]) -> None:
        self.initCardExporterIfNeeded()
        self.addWindow.bulkTextExport(cards)

    def bulkMediaExport(self, card: Any) -> None:
        self.initCardExporterIfNeeded()
        self.addWindow.bulkMediaExport(card)

    def cancelBulkMediaExport(self) -> None:
        if self.addWindow:
            self.addWindow.bulkMediaExportCancelledByBrowserRefresh()

    def exportAudio(self, audioList: Tuple[str, str, str]) -> None:
        self.dictInt.ensureVisible()
        temp, tag, name = audioList
        self.initCardExporterIfNeeded()
        self.addWindow.scrollArea.show()
        self.addWindow.exportAudio(temp, tag, name)

    def exportSentence(self, sentence: str, secondary: str = "") -> None:
        self.dictInt.ensureVisible()
        self.initCardExporterIfNeeded()
        self.addWindow.scrollArea.show()
        self.addWindow.exportSentence(sentence)
        self.addWindow.exportSecondary(secondary)

    def exportWord(self, word: str) -> None:
        self.dictInt.ensureVisible()
        self.initCardExporterIfNeeded()
        self.addWindow.scrollArea.show()
        self.addWindow.exportWord(word)

    def attemptAutoAdd(self, bulkExport: Any) -> None:
        self.addWindow.attemptAutoAdd(bulkExport)

    def getFieldContent(
        self, fContent: str, definition: str, addType: str
    ) -> Union[str, bool]:
        fieldText = False
        if addType == "overwrite":
            fieldText = definition

        elif addType == "add":
            if fContent == "":
                fieldText = definition
            else:
                fieldText = fContent + "<br><br>" + definition
        elif addType == "no":
            if fContent == "":
                fieldText = definition
        return fieldText

    def addAudioToExportWindow(self, word: str, urls: str) -> None:
        self.initCardExporterIfNeeded()
        audioSeparator = ""
        soundFiles = self.downloadForvoAudio(json.loads(urls))
        if len(soundFiles) > 0:
            self.addWindow.addDefinition("Forvo", word, audioSeparator.join(soundFiles))

    def sendAudioToField(self, urls: str) -> None:
        audioSeparator = ""
        soundFiles = self.downloadForvoAudio(json.loads(urls))
        self.sendToField("Forvo", audioSeparator.join(soundFiles))

    def downloadForvoAudio(self, urls: List[str]) -> List[str]:
        tags: List[str] = []
        for url in urls:
            try:
                req = Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                    },
                )
                file = urlopen(req).read()
                filename = str(time.time()) + ".mp3"
                open(join(self.dictInt.mw.col.media.dir(), filename), "wb").write(file)
                tags.append("[sound:" + filename + "]")
            except:
                continue
        return tags

    def sendImgToField(self, urls: str) -> None:
        # print("sendImgToField midict.py")

        if (self.reviewer and self.reviewer.card) or (
            self.currentEditor and self.currentEditor.note
        ):
            urlsList: List[str] = []
            imgSeparator = ""
            urls_list = json.loads(urls)

            for imgurl in urls_list:
                try:
                    # Check if it's a local file path
                    if os.path.exists(imgurl):
                        # Handle local file
                        filename = os.path.basename(imgurl)
                        dest_path = join(self.dictInt.mw.col.media.dir(), filename)

                        # Copy file if needed
                        if imgurl != dest_path:
                            shutil.copy2(imgurl, dest_path)

                        urlsList.append(f'<img src="{filename}">')

                    else:
                        # Handle remote URL
                        url = re.sub(r"\?.*$", "", imgurl)
                        filename = (
                            str(time.time())[:-4].replace(".", "")
                            + re.sub(r"\..*$", "", url.strip().split("/")[-1])
                            + ".jpg"
                        )

                        self.saveQImage(
                            imgurl, join(self.dictInt.mw.col.media.dir(), filename)
                        )
                        urlsList.append(f'<img src="{filename}">')

                except Exception as e:
                    print(f"Failed to process image: {imgurl}")
                    print(f"Error: {str(e)}")
                    continue
            if len(urlsList) > 0:
                self.sendToField("Google Images", imgSeparator.join(urlsList))

        else:
            print("no reviewer or editor")
            tooltip(
                "No active reviewer or editor found. Please open a card to send images to a field."
            )

    def sendToField(self, name: str, definition: str) -> None:
        if self.reviewer and self.reviewer.card:
            if name == "Google Images":
                tFields = self.config["GoogleImageFields"]
                addType = self.config["GoogleImageAddType"]
            elif name == "Forvo":
                tFields = self.config["ForvoFields"]
                addType = self.config["ForvoAddType"]
            else:
                tFields, addType = self.db.getAddTypeAndFields(name)
            note = self.reviewer.card.note()
            model = note.model()
            fields = model["flds"]
            changed = False
            for field in fields:
                if field["name"] in tFields:
                    newField = self.getFieldContent(
                        note[field["name"]], definition, addType
                    )
                    if newField is not False:
                        changed = True
                        if self.jSend:
                            note[field["name"]] = (
                                self.dictInt.jHandler.attemptFieldGenerate(
                                    newField, field["name"], model["name"], note
                                )
                            )
                        else:
                            note[field["name"]] = newField
            if not changed:
                return
            # note.flush()
            self.dictInt.mw.col.update_note(note, skip_undo_entry=True)
            # self.reviewer.card.load()
            # self.reviewer.
            if self.reviewer.state == "answer":
                self.reviewer._showAnswer()
            elif self.reviewer.state == "question":
                self.reviewer._showQuestion()
            if hasattr(self.dictInt.mw, "DictReloadEditorAndBrowser"):
                self.dictInt.mw.DictReloadEditorAndBrowser(note)
        if self.currentEditor and self.currentEditor.note:
            if name == "Google Images":
                tFields = self.config["GoogleImageFields"]
                addType = self.config["GoogleImageAddType"]
            elif name == "Forvo":
                tFields = self.config["ForvoFields"]
                addType = self.config["ForvoAddType"]
            else:
                tFields, addType = self.db.getAddTypeAndFields(name)
            note = self.currentEditor.note

            items = note.items()
            for idx, item in enumerate(items):
                noteField = item[0]
                if noteField in tFields:
                    # Get the current note ID
                    currentNoteId = (
                        note.id
                    )  # Assuming `note` is the current note object
                    self.currentEditor.web.eval(
                        self.dictInt.insertHTMLJS
                        % (
                            definition.replace('"', '\\"'),
                            str(idx),  # Field index
                            addType,  # Action type
                            currentNoteId,  # Pass the note ID to JavaScript
                        )
                    )

    def getOverwriteChecks(self, dictCount: int, dictName: str) -> str:
        if dictName == "Google Images":
            addType = self.config["GoogleImageAddType"]
        elif dictName == "Forvo":
            addType = self.config["ForvoAddType"]
        else:
            addType = self.db.getAddType(dictName)
        tooltip = ""
        if self.config["tooltips"]:
            tooltip = " title=\"This determines the conditions for sending a definition (or a Google Image) to a field. Overwrite the target field's content. Add to the target field's current contents. Only add definitions to the target field if it is empty.\""
        if addType == "add":
            typeName = "&nbsp;Add"
        elif addType == "overwrite":
            typeName = "&nbsp;Overwrite"
        elif addType == "no":
            typeName = "&nbsp;If Empty"
        select = (
            '<div class="overwriteSelectCont"><div '
            + tooltip
            + ' class="overwriteSelect" onclick="showCheckboxes(event)">'
            + typeName
            + "</div>"
            + self.getSelectedOverwriteType(dictName, addType)
            + "</div>"
        )
        return select

    def getSelectedOverwriteType(self, dictName: str, addType: str) -> str:
        count = str(self.radioCount)
        checked = ""
        if addType == "add":
            checked = " checked"
        add = (
            '<label class="inCheckBox"><input'
            + checked
            + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio'
            + dictName
            + '" type="radio" name="'
            + count
            + dictName
            + '" value="add"/>Add</label>'
        )
        checked = ""
        if addType == "overwrite":
            checked = " checked"
        overwrite = (
            '<label class="inCheckBox"><input'
            + checked
            + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio'
            + dictName
            + '" type="radio" name="'
            + count
            + dictName
            + '" value="overwrite"/>Overwrite</label>'
        )
        checked = ""
        if addType == "no":
            checked = " checked"
        ifempty = (
            '<label class="inCheckBox"><input'
            + checked
            + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio'
            + dictName
            + '" type="radio" name="'
            + count
            + dictName
            + '" value="no"/>If Empty</label>'
        )
        checks = (
            '<div class="overwriteCheckboxes" data-dictname="'
            + dictName
            + '">'
            + add
            + overwrite
            + ifempty
            + "</div>"
        )
        self.radioCount += 1
        return checks

    def getFieldChecks(self, dictName):
        if dictName == "Google Images":
            selF = self.config["GoogleImageFields"]
        elif dictName == "Forvo":
            selF = self.config["ForvoFields"]
        else:
            selF = self.db.getFieldsSetting(dictName)
        tooltip = ""
        if self.config["tooltips"]:
            tooltip = ' title="Select this dictionary\'s target fields for when sending a definition(or a Google Image) to a card. If a field does not exist in the target card, then it is ignored, otherwise the definition is added to all fields that exist within the target card."'
        title = "&nbsp;Select Fields ▾"
        length = len(selF)
        if length > 0:
            title = "&nbsp;" + str(length) + " Selected"
        select = (
            '<div class="fieldSelectCont"><div class="fieldSelect" '
            + tooltip
            + ' onclick="showCheckboxes(event)">'
            + title
            + "</div>"
            + self.getCheckBoxes(dictName, selF)
            + "</div>"
        )
        return select

    def getCheckBoxes(self, dictName, selF):
        fields = self.getFieldNames()
        options = '<div class="fieldCheckboxes"  data-dictname="' + dictName + '">'
        for f in fields:
            checked = ""
            if f in selF:
                checked = " checked"
            options += (
                '<label class="inCheckBox"><input'
                + checked
                + ' onclick="handleFieldCheck(this)" class="inCheckBox" type="checkbox" value="'
                + f
                + '" />'
                + f
                + "</label>"
            )
        return options + "</div>"

    def getFieldNames(self):
        mw = self.dictInt.mw
        models = mw.col.models.all()
        fields = []
        for model in models:
            for fld in model["flds"]:
                if fld["name"] not in fields:
                    fields.append(fld["name"])
        fields.sort()
        return fields

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

    def leaveEvent(self, event):
        self.mouseHover.emit(False)
        self.mouseOut.emit(True)


def imageResizer(img):
    if Image is None:
        # Return original image if PIL is not available
        return img
    width, height = img.size
    maxh = 300
    maxw = 300
    ratio = min(maxw / width, maxh / height)
    height = int(round(ratio * height))
    width = int(round(ratio * width))
    try:
        return img.resize((width, height), Image.ANTIALIAS)
    except AttributeError:
        # Handle newer PIL versions where ANTIALIAS is deprecated
        return img.resize((width, height), Image.Resampling.LANCZOS)


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

    def __init__(self, mw, path):
        try:
            if is_mac:
                import ssl

                ssl._create_default_https_context = ssl._create_unverified_context
                sys.path.insert(0, join(dirname(__file__), "keyboardMac"))
                try:
                    from Quartz import (
                        CGEventGetIntegerValueField,
                        kCGKeyboardEventKeycode,
                    )

                    self.kCGKeyboardEventKeycode = kCGKeyboardEventKeycode
                    self.CGEventGetIntegerValueField = CGEventGetIntegerValueField
                except ImportError:
                    print("Warning: Quartz not available on this system")
                    self.kCGKeyboardEventKeycode = None
                    self.CGEventGetIntegerValueField = None
            elif is_lin:
                sys.path.insert(0, join(dirname(__file__), "linux"))
            sys.path.insert(0, join(dirname(__file__)))

            try:
                from pynput import keyboard

                self.keyboard = keyboard
            except ImportError:
                print("Warning: pynput not available - global hotkeys will not work")
                self.keyboard = None

        except Exception as e:
            print(f"Warning: Error initializing ClipThread: {e}")
            self.keyboard = None

        super(ClipThread, self).__init__(mw)
        self.addonPath = path
        # Set up root addon temp directory path (same as MIDict)
        self.addon_root = dirname(dirname(dirname(dirname(__file__))))
        self.temp_dir = join(self.addon_root, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        # Import here to avoid circular imports
        from anki_dictionary.utils.config import get_addon_config

        self.config = get_addon_config()

    def on_press(self, key):
        self.test.emit([key])

    def on_release(self, key):
        self.release.emit([key])
        return True

    def darwinIntercept(self, event_type, event):
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

    def run(self):
        if not self.keyboard:
            print("Keyboard monitoring not available - skipping hotkey setup")
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
            print(f"Warning: Could not start keyboard listener: {e}")

    def attemptAddCard(self):
        self.add.emit("add")

    def checkDict(self):
        if not self.mw.ankiDictionary or not self.mw.ankiDictionary.isVisible():
            return False
        return True

    def handleExtensionSearch(self, terms):
        self.searchFromExtension.emit(terms)

    def handleSystemSearch(self):
        self.search.emit(self.mw.app.clipboard().text())

    def handleColSearch(self):
        self.colSearch.emit(self.mw.app.clipboard().text())

    def getConfig(self):
        from anki_dictionary.utils.config import get_addon_config

        return get_addon_config()

    def handleBulkTextExport(self, cards):
        self.bulkTextExport.emit(cards)

    def handleExtensionCardExport(self, card):
        config = self.getConfig()
        audioFileName = card["audio"]
        imageFileName = card["image"]
        bulk = card["bulk"]
        if audioFileName:
            audioTempPath = join(self.temp_dir, audioFileName)
            if not self.checkFileExists(audioTempPath):
                self.extensionFileNotFound.emit()
                return
            if config["mp3Convert"]:
                audioFileName = audioFileName.replace(".wav", ".mp3")
                self.moveExtensionMp3ToMediaFolder(audioTempPath, audioFileName)
                card["audio"] = audioFileName
            else:
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

    def saveScaledImage(self, imageTempPath, imageFileName):
        maxW = self.mw.AnkiDictConfig["maxWidth"]
        maxH = self.mw.AnkiDictConfig["maxHeight"]
        path = join(self.mw.col.media.dir(), imageFileName)
        image = QImage(imageTempPath)
        image = image.scaled(
            QSize(maxW, maxH),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image.save(path)

    def removeFile(self, file):
        os.remove(file)

    def checkFileExists(self, source):
        now = time.time()
        while True:
            if exists(source):
                return True
            if time.time() - now > 15:
                return False

    def moveExtensionFileToMediaFolder(self, source, filename):
        if exists(source):
            path = join(self.mw.col.media.dir(), filename)
            if not exists(path):
                copyfile(source, path)
                return True

    def moveExtensionMp3ToMediaFolder(self, source, filename):
        suffix = ""
        if is_win:
            suffix = ".exe"
        ffmpeg = join(
            dirname(dirname(dirname(dirname(__file__)))),
            "user_files",
            "ffmpeg",
            "ffmpeg" + suffix,
        )
        path = join(self.mw.col.media.dir(), filename)
        import subprocess

        subprocess.call([ffmpeg, "-i", source, path])

    def handlePageRefreshDuringBulkMediaImport(self):
        self.pageRefreshDuringBulkMediaImport.emit()

    def handleImageExport(self):
        if self.checkDict():
            mime = self.mw.app.clipboard().mimeData()
            clip = self.mw.app.clipboard().text()

            if not clip.endswith(".mp3") and mime.hasImage():
                image = mime.imageData()
                filename = str(time.time()) + ".png"
                fullpath = join(self.temp_dir, filename)
                maxW = max(self.config["maxWidth"], image.width())
                maxH = max(self.config["maxHeight"], image.height())
                image = image.scaled(
                    QSize(maxW, maxH),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image.save(fullpath)
                self.image.emit([fullpath, filename])
            elif clip.endswith(".mp3"):
                if not is_lin:
                    if is_mac:
                        try:
                            clip = str(
                                self.mw.app.clipboard().mimeData().urls()[0].url()
                            )
                        except:
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
                        except:
                            return

    def moveAudioToTempFolder(self, path):
        try:
            if exists(path):
                filename = str(time.time()).replace(".", "") + ".mp3"
                destpath = join(self.temp_dir, filename)
                if not exists(destpath):
                    copyfile(path, destpath)
                    return destpath, filename
            return False, False
        except:
            return False, False

    def handleSentenceExport(self):
        if self.checkDict():
            self.sentence.emit(self.mw.app.clipboard().text())


class DictInterface(QWidget):
    def __init__(self, dictdb, mw, path, welcome, parent=None, terms=False):
        super(DictInterface, self).__init__()
        self.db = dictdb
        self.verticalBar = False
        self.jHandler = miJHandler(mw)
        self.addonPath = path
        self.welcome = welcome
        self.setAutoFillBackground(True)
        self.mw = mw
        self.parent = parent
        self.iconpath = join(path, "assets", "icons")

        self.active_theme_file = join(
            self.addonPath, "user_files/themes", "active.json"
        )
        self.theme_manager = ThemeManager(self.addonPath)
        self.theme_editor = ThemeEditorDialog(self.theme_manager, mw, path, self)
        self.theme_editor.applied.connect(self.refresh_application_theme)

        self.startUp(terms)
        self.setHotkeys()
        ensureWidgetInScreenBoundaries(self)

    def load_theme_color(self, color_key):
        """
        Load a specific color from the active theme.
        """
        try:
            active_theme = self.theme_manager.get_active_theme()
            color_value = getattr(active_theme, color_key, "#ffffff")
            return QColor(color_value)
        except Exception as e:
            print(f"Error loading active theme color: {e}")
        return QColor("#ffffff")  # Default color if anything fails

    def refresh_widget(self, widget):
        """
        Recursively refresh a widget and its children.
        """
        widget.update()
        widget.repaint()
        for child in widget.findChildren(QWidget):
            self.refresh_widget(child)

    def refresh_application_theme(self):
        """
        Refresh the application theme by updating styles and re-rendering components.
        """
        # Reload the active theme from disk to ensure we have the latest changes
        self.theme_manager._load_active_theme()

        # Load the active theme from theme manager
        try:
            active_theme = self.theme_manager.get_active_theme()
        except Exception as e:
            print(f"Error loading active theme: {e}")
            return

        # Update the stylesheet for the entire widget
        self.setStyleSheet(self.theme_manager.get_qt_styles())

        # Update the stylesheet for child widgets (e.g., combo boxes, buttons, etc.)
        self.update_child_widget_styles()

        # Simple reload - just reload the dictionary interface completely
        html, url = self.getHTMLURL(False)
        self.dict.setHtml(html, url)

        # Update the history browser colors if it exists
        if hasattr(self, "historyBrowser") and self.historyBrowser:
            self.historyBrowser.setColors()

    def update_child_widget_styles(self):
        """
        Update the styles of child widgets to reflect the new theme.
        """
        # Example: Update the combo box styles
        self.dictGroups.setStyleSheet(self.theme_manager.get_combo_style())
        self.sType.setStyleSheet(self.theme_manager.get_combo_style())

        # Update button styles
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(self.theme_manager.get_qt_styles())

    def getPalette(self, color):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, color)
        return pal

    def setHotkeys(self):
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)
        self.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self)
        self.hotkeyW.activated.connect(self.mw.dictionaryInit)
        self.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self)
        self.hotkeyS.activated.connect(lambda: self.mw.searchTerm(self.dict.page()))
        self.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), self)
        self.hotkeyS.activated.connect(lambda: self.mw.searchCol(self.dict.page()))

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
        self.allGroups = self.getAllGroups()
        self.config = self.getConfig()
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
        self.setWindowIcon(QIcon(join(self.iconpath, "dictionary.png")))
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
            self.sType.setToolTip("Select the search type.")
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

    def getHTMLURL(self, willSearch):
        try:
            active_theme = self.theme_manager.get_active_theme()
            active_theme_dict = vars(active_theme)
        except Exception as e:
            print(f"Error loading active theme: {e}")
            active_theme_dict = {
                "header_background": "#51576d",
                "selector": "#949cbb",
                "header_text": "#babbf1",
                "search_term": "#f4b8e4",
                "border": "#babbf1",
                "anki_button_background": "#99d1db",
                "anki_button_text": "#c6d0f5",
                "tab_hover": "#f4b8e4",
                "current_tab_gradient_top": "#737994",
                "current_tab_gradient_bottom": "#414559",
                "example_highlight": "#414559",
                "definition_background": "#51576d",
                "definition_text": "#c6d0f5",
                "pitch_accent_color": "#eebebe",
            }

        qss = f"""
                    QWidget {{
                        background-color: {active_theme_dict["definition_background"]};
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 14px;
                    }}
                    QPushButton {{
                        color: {active_theme_dict['header_text']};
                        border: 1px solid {active_theme_dict['border']};
                        border-radius: 5px;
                        padding: 8px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid {active_theme_dict['border']};
                    }}
                    QLineEdit, QComboBox {{
                        background-color: {active_theme_dict['selector']};
                        color: {active_theme_dict['search_term']};
                        border: 1px solid {active_theme_dict['border']};
                        border-radius: 5px;
                        padding: 8px;
                    }}
                    QLabel {{
                        font-weight: bold;
                        border: 1px solid {active_theme_dict['border']};
                    }}
                    QComboBox QAbstractItemView {{
                        color: {active_theme_dict['header_text']};
                        border: 1px solid {active_theme_dict['border']};
                    }}
                    
                    SVGPushButton{{
                        background-color: {active_theme_dict['selector']};
                        color: {active_theme_dict['header_text']}
                        border: 1px solid {active_theme_dict['border']};
                    }}
                """
        self.setStyleSheet(qss)
        custom_theme_css = f"""
            <style id="customThemeCss">
                :root {{
                    --background: {active_theme_dict['header_background']};
                    --background-secondary: {active_theme_dict['selector']};
                    --text: {active_theme_dict['header_text']};
                    --text-secondary: {active_theme_dict['search_term']};
                    --border: {active_theme_dict['border']};
                    --button-bg: {active_theme_dict['anki_button_background']};
                    --button-text: {active_theme_dict['anki_button_text']};
                    --button-bg-hover: {active_theme_dict['tab_hover']};
                }}
                body {{
                    background-color: {active_theme_dict['header_background']};
                    color: {active_theme_dict['header_text']};
                }}
                .header {{
                    background-color: {active_theme_dict['header_background']};
                    color: {active_theme_dict['header_text']};
                    border-bottom: 2px solid {active_theme_dict['border']};
                }}
                .targetTerm {{
                    color: {active_theme_dict['search_term']} !important;
                }}
                .exampleSentence {{
                    background-color: {active_theme_dict['example_highlight']};
                    border-radius: 3px;
                    padding-top:1px;
                    margin:0 5px;
                }}
                .definitionBlock {{
                    background-color: {active_theme_dict['definition_background']};
                    color: {active_theme_dict['definition_text']};
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 5px;
                    padding: 15px;
                    margin: 10px;
                }}
                .altterm {{
                    color: {active_theme_dict['pitch_accent_color']};
                }}
                .ankiExportButton {{
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 5px;
                    padding: 5px;
                }}
                .ankiExportButton img {{
                    background-color: {active_theme_dict['anki_button_background']};
                }}
                .tablinks {{
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 5px 5px 0 0;
                }}
                .tablinks.active {{
                    background-image: linear-gradient(
                        {active_theme_dict['current_tab_gradient_top']},
                        {active_theme_dict['current_tab_gradient_bottom']}
                    );
                    border-bottom: none;
                }}
                .tablinks:hover {{
                    background-color: {active_theme_dict['tab_hover']};
                }}
                .overwriteSelect, .fieldSelect {{
                    background-color: {active_theme_dict['selector']};
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 5px;
                    padding: 5px;            }}
        </style>
        """

        html_path = join(self.addonPath, "assets", "templates", "dictionary.html")
        js_path = join(self.addonPath, "assets", "scripts", "dictionary.js")

        # Read the JavaScript content to inline it
        with open(js_path, "r", encoding="utf-8") as js_file:
            js_content = js_file.read()

        with open(html_path, "r", encoding="utf-8") as fh:
            html = fh.read()
            # Replace the external script tag with inline JavaScript
            html = html.replace(
                '<script src="../scripts/dictionary.js"></script>',
                f"<script>{js_content}</script>",
            )
            # Inject the custom theme CSS
            html = html.replace('<style id="customThemeCss"></style>', custom_theme_css)
            if not willSearch:
                # Only add welcome screen if it's not empty
                if self.welcome and self.welcome.strip():
                    # Properly escape the HTML content for JavaScript
                    escaped_welcome = json.dumps(self.welcome)
                    html = html.replace(
                        '<script id="initialValue"></script>',
                        f"<script id=\"initialValue\">if (typeof addNewTab === \"function\") {{ addNewTab({escaped_welcome}, \"Welcome\", true); }} if(document.getElementsByClassName('tablinks')[0]) {{ document.getElementsByClassName('tablinks')[0].classList.add('active'); }}</script>",
                    )
                # If welcome is empty, just remove the script tag to avoid showing welcome screen
                else:
                    html = html.replace(
                        '<script id="initialValue"></script>',
                        '<script id="initialValue">console.log("Welcome screen disabled - no welcome content");</script>',
                    )
            url = QUrl.fromLocalFile(html_path)
        return html, url

    def getAllGroups(self):
        allGroups = {}
        allGroups["dictionaries"] = self.db.getAllDictsWithLang()
        allGroups["customFont"] = False
        allGroups["font"] = False
        return allGroups

    def getInsertHTMLJS(self):
        insertHTML = join(self.addonPath, "assets", "scripts", "insertHTML.js")
        with open(insertHTML, "r", encoding="utf-8") as insertHTMLFile:
            return insertHTMLFile.read()

    def focusWindow(self):
        self.show()
        if self.windowState() == Qt.WindowState.WindowMinimized:
            self.setWindowState(Qt.WindowState.WindowNoState)
        self.setFocus()
        self.activateWindow()

    def closeEvent(self, event):
        self.hide()

    def hideEvent(self, event):
        self.saveSizeAndPos()
        shortcut = "(Ctrl+W)"
        if is_mac:
            shortcut = "⌘W"
        self.mw.openMiDict.setText("Open Dictionary " + shortcut)
        event.accept()

    def resetConfiguration(self, terms):
        terms = self.refineToValidSearchTerms(terms)
        willSearch = False
        if terms is not False:
            willSearch = True
        self.search.setText("")
        self.allGroups = self.getAllGroups()
        self.config = self.getConfig()
        self.defaultGroups = self.db.getDefaultGroups()
        self.userGroups = self.getUserGroups()
        self.dictGroups.currentIndexChanged.disconnect()
        newDictGroupsCombo = self.setupDictGroups()
        self.toolbarTopLayout.replaceWidget(self.dictGroups, newDictGroupsCombo)
        self.dictGroups.close()
        self.dictGroups.deleteLater()
        self.dictGroups = newDictGroupsCombo
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
        if not is_win:
            self.dictGroups.setFixedSize(108, 38)
        else:
            self.dictGroups.setFixedSize(110, 38)
        # if self.nightModeToggler.day:
        #     if not is_win:
        #         self.dictGroups.setStyleSheet(self.getMacComboStyle())
        #     else:
        #         self.dictGroups.setStyleSheet('')
        # else:
        #     if not is_win:
        #         self.dictGroups.setStyleSheet(self.getMacNightComboStyle())
        #     else:
        #         self.dictGroups.setStyleSheet(self.getComboStyle())
        self.resetDict(willSearch, terms)

    def resetDict(self, willSearch, terms):
        newDict = MIDict(self, self.db, self.addonPath, terms)
        newDict.setSType(self.sType)
        html, url = self.getHTMLURL(willSearch)
        newDict.loadHTMLURL(html, url)
        newDict.setSType(self.sType)
        if self.dict.addWindow and self.dict.addWindow.scrollArea.isVisible():
            self.dict.addWindow.saveSizeAndPos()
            self.dict.addWindow.scrollArea.close()
            self.dict.addWindow.scrollArea.deleteLater()
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
        layoutH = QHBoxLayout()

        self.toolbarTopLayout = layoutH

        layoutH.addWidget(self.dictGroups)
        layoutH.addWidget(self.sType)
        layoutH.addWidget(self.search)
        layoutH.addWidget(self.searchButton)

        if not is_win:
            self.dictGroups.setFixedSize(120, 40)
            self.search.setFixedSize(120, 40)
            self.sType.setFixedSize(100, 40)
        else:
            self.sType.setFixedHeight(40)
            self.dictGroups.setFixedSize(120, 40)
            self.search.setFixedSize(120, 40)

        layoutH.setContentsMargins(5, 5, 5, 5)
        layoutH.setSpacing(10)

        self.layoutH2.addWidget(self.openSB)
        self.layoutH2.addWidget(self.minusB)
        self.layoutH2.addWidget(self.plusB)
        self.layoutH2.addWidget(self.tabB)
        self.layoutH2.addWidget(self.histB)
        self.layoutH2.addWidget(self.conjToggler)
        self.layoutH2.addWidget(self.themeSettings)
        self.layoutH2.addWidget(self.setB)

        self.targetLabel.setFixedHeight(40)
        self.layoutH2.addWidget(self.targetLabel)
        self.currentTarget.setFixedHeight(40)
        self.layoutH2.addWidget(self.currentTarget)

        if not self.config["showTarget"]:
            self.currentTarget.hide()
            self.targetLabel.hide()

        self.layoutH2.addStretch()
        self.layoutH2.setContentsMargins(5, 5, 5, 5)
        self.layoutH2.setSpacing(10)
        self.mainHLay.setContentsMargins(0, 0, 0, 0)
        self.mainHLay.addLayout(layoutH)
        self.mainHLay.addLayout(self.layoutH2)
        self.mainHLay.addStretch()

        layoutV.addLayout(self.mainHLay)
        layoutV.addWidget(self.dict)
        layoutV.setContentsMargins(0, 0, 0, 0)
        layoutV.setSpacing(5)

        return layoutV

    def toggleMenuBar(self, vertical):
        if vertical:
            self.mainHLay.removeItem(self.layoutH2)
            self.mainLayout.insertLayout(1, self.layoutH2)
        else:
            self.mainLayout.removeItem(self.layoutH2)
            self.mainHLay.insertLayout(1, self.layoutH2)

    def resizeEvent(self, event):
        w = self.width()
        if w < 702 and not self.verticalBar:
            self.verticalBar = True
            self.toggleMenuBar(True)
        elif w > 701 and self.verticalBar:
            self.verticalBar = False
            self.toggleMenuBar(False)
        event.accept()

    def setupSearchButton(self):
        searchB = SVGPushButton(40, 40)
        self.setSvg(searchB, "search")
        searchB.clicked.connect(self.initSearch)
        return searchB

    def setupOpenSB(self):
        openSB = SVGPushButton(40, 40)
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
        TabMode = SVGPushButton(40, 40)
        if self.config["onetab"]:
            TabMode.singleTab = True
            icon = "onetab"
        else:
            TabMode.singleTab = False
            icon = "tabs"
        self.setSvg(TabMode, icon)
        TabMode.clicked.connect(self.toggleTabMode)
        return TabMode

    def toggleTabMode(self):
        if self.tabB.singleTab:
            self.tabB.singleTab = False
            self.setSvg(self.tabB, "tabs")
            self.writeConfig("onetab", False)
        else:
            self.tabB.singleTab = True
            self.setSvg(self.tabB, "onetab")
            self.writeConfig("onetab", True)

    def setupConjugationMode(self):
        conjugationMode = SVGPushButton(40, 40)
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
        history = SVGPushButton(40, 40)
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
        self.refresh_application_theme()

    def setSvg(self, widget, name):
        # if self.nightModeToggler.day:
        #     return widget.setSvg(join(self.iconpath, 'dictsvgs', name + 'day.svg'))
        # return widget.setSvg(join(self.iconpath, 'dictsvgs', name + 'night.svg'))
        return widget.setSvg(join(self.iconpath, "dictsvgs", name + ".svg"))

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
        themeButton = SVGPushButton(40, 40)
        # nightToggle.day = self.config['day']
        # themeButton.applied.connect(self.refresh_application_theme)
        self.setSvg(themeButton, "themesettings")
        themeButton.clicked.connect(self.setTheme)
        themeButton.clicked.connect(self.refresh_application_theme)
        return themeButton

    def setupOpenSettings(self):
        settings = SVGPushButton(40, 40)
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
        plusB = SVGPushButton(40, 40)
        self.setSvg(plusB, "plus")
        plusB.clicked.connect(self.incFont)
        return plusB

    def setupMinus(self):
        minusB = SVGPushButton(40, 40)
        self.setSvg(minusB, "minus")
        minusB.clicked.connect(self.decFont)
        return minusB

    def decFont(self):
        self.dict.eval("scaleFont(false)")

    def incFont(self):
        self.dict.eval("scaleFont(true)")

    def alignCenter(self, dictGroups):
        for i in range(0, dictGroups.count()):
            dictGroups.model().item(i).setTextAlignment(Qt.AlignmentFlag.alignCenter)

    def setupDictGroups(self, dictGroups=False):
        if not dictGroups:
            dictGroups = QComboBox()
            dictGroups.setFixedHeight(30)
            dictGroups.setFixedWidth(80)
            dictGroups.setContentsMargins(0, 0, 0, 0)
        ug = sorted(list(self.userGroups.keys()))
        dictGroups.addItems(ug)
        dictGroups.addItem("──────")
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        defaults = ["All", "Google Images", "Forvo"]
        dictGroups.addItems(defaults)
        dictGroups.addItem("──────")
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(
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
        if cur == "Google Images":
            return {
                "dictionaries": [{"dict": "Google Images", "lang": ""}],
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
        selectedGroup = self.getSelectedDictGroup()
        if term == False:
            term = self.search.text()
            term = term.strip()
        term = term.strip()
        term = self.cleanTermBrackets(term)
        if term == "":
            return
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
        with codecs.open(path, "w", "utf-8") as outfile:
            json.dump(self.historyModel.history, outfile, ensure_ascii=False)
        return

    def getHistory(self):
        path = join(self.mw.col.media.dir(), "_searchHistory.json")
        try:
            if exists(path):
                with open(path, "r", encoding="utf-8") as histFile:
                    return json.loads(histFile.read())
            else:
                # Create empty search history file if it doesn't exist
                empty_history = []
                with codecs.open(path, "w", "utf-8") as outfile:
                    json.dump(empty_history, outfile, ensure_ascii=False)
                return empty_history
        except Exception as e:
            print(f"Warning: Could not load search history: {e}")
            return []

    def updateFieldsSetting(self, dictName, fields):
        self.db.setFieldsSetting(dictName, json.dumps(fields, ensure_ascii=False))

    def updateAddType(self, dictName, addType):
        self.db.setAddType(dictName, addType)

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
            + join(self.iconpath, "blackdown.png").replace("\\", "/")
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

    def mousePressEvent(self, ev):
        self.clicked.emit()


class SVGPushButton(QPushButton):
    def __init__(self, width, height):
        super().__init__()
        self.setFixedSize(width, height)  # Set the fixed size of the button
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.svgWidget = None  # Placeholder for the SVG widget

    def setSvg(self, svgPath):
        # Remove the existing SVG widget if it exists
        if self.svgWidget:
            self.layout.removeWidget(self.svgWidget)
            self.svgWidget.deleteLater()

        # Create a new SVG widget and add it to the layout
        self.svgWidget = QSvgWidget(svgPath)
        self.svgWidget.setFixedSize(
            self.width(), self.height()
        )  # Match the button's size
        self.layout.addWidget(self.svgWidget)
