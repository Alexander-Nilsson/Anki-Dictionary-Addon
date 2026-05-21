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
from typing import List, Dict, Optional, Tuple, Any, Union
from urllib.request import Request, urlopen

from ..utils.history import HistoryBrowser, HistoryModel
from aqt.editor import Editor
from aqt.operations.note import update_note
from ..exporters.card_exporter import CardExporter
import time
from . import database as dictdb
from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


# Suppress Qt SVG and other noisy warnings
def qt_message_handler(mode, context, message):
    suppress_patterns = [
        "Invalid path data; path truncated",
        "QObject::disconnect",
        "zwp_text_input_v3",
        "Got leave event for surface",
        "GPUInfo not initialized on GpuInfoUpdate",
        "Autofill.enable",
        "Autofill.setAddresses",
    ]
    if any(pattern in message for pattern in suppress_patterns):
        return  # Suppress these specific warnings

    # Let other messages through normally
    if mode == QtMsgType.QtWarningMsg:
        logger.warning(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        logger.critical(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        logger.critical(f"Qt Fatal: {message}")


# Install the message handler
qInstallMessageHandler(qt_message_handler)
import aqt
from ..integrations import image_search as duckduckgoimages
from ..integrations import llm as llm_integration
from ..integrations import forvo as forvo_integration
from ..ui.settings.settings_gui import SettingsGui
import datetime
import codecs
import ntpath
from ..utils.common import miInfo
from ..web.icons import get_base64_icon
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
        self.maxW = self.config.get("maxWidth", 1500)
        self.maxH = self.config.get("maxHeight", 400)
        self.onBridgeCmd = self.handleDictAction
        self.db = db
        self.termHeaders = self.formatTermHeaders(self.db.getTermHeaders() or {})
        self.dupHeaders = self.db.getDupHeaders() or {}
        self.sType = False
        self.radioCount = 0
        self.homeDir = path
        self.addonPath = path
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
        self.maxW = self.config.get("maxWidth", 1500)
        self.maxH = self.config.get("maxHeight", 400)
        self.termHeaders = self.formatTermHeaders(self.db.getTermHeaders() or {})
        self.dupHeaders = self.db.getDupHeaders() or {}

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
        self.eval("loadImageHtml(%s, %s);" % (escaped_html, escaped_idName))

    def downloadImage(self, url):
        try:
            filename = str(time.time()).replace(".", "") + ".avif"
            if url.startswith("data:"):
                # Handle data:image/xxx;base64,xxxx
                header, encoded = url.split(",", 1)
                file = base64.b64decode(encoded)
            else:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                file = urlopen(req, timeout=30).read()

            image = QImage()
            image.loadFromData(file)
            if not image.isNull():
                image = image.scaled(
                    QSize(self.maxW, self.maxH),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image.save(filename, "AVIF")
                return '<img src="' + filename + '">'
        except:
            return ""

    def loadHTMLURL(self, html, url):
        self.page().setHtml(html, url)

    def getBase64Icon(self, icon_name):
        """Convert icon to base64 data URL for embedding in HTML, handling dark theme if needed"""
        if self.dictInt.theme_manager.is_dark:
            # Handle special cases first
            if icon_name == "anki.svg":
                icon_name = "nightanki.svg"
            elif "." in icon_name:
                name, ext = icon_name.rsplit(".", 1)
                # Avoid adding "night" twice
                if not name.endswith("night"):
                    night_name = f"{name}night.{ext}"
                    # Check if the night version exists in the icons directory
                    if exists(join(self.dictInt.iconpath, night_name)):
                        icon_name = night_name

        return get_base64_icon(icon_name)

    def formatTermHeaders(self, ths):
        formattedHeaders = {}
        if not ths:
            return None
        for dictname in ths:
            headerString = ""
            sbHeaderString = ""
            for header in ths[dictname]:
                if header == "term":
                    headerString += '◳f<span class="term mainword">◳t</span>◳b '
                    sbHeaderString += '◳f<span class="listTerm">◳t</span>◳b '
                elif header == "altterm":
                    headerString += '◳x<span class="altterm  mainword">◳a</span>◳y '
                    sbHeaderString += '◳x<span class="listAltTerm">◳a</span>◳y '
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
            term.replace("%", "").replace("_", "").replace("「", "").replace("」", "")
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
        js_font = json.dumps(font)
        js_name = json.dumps(name)
        self.eval(f"addCustomFont({js_font}, {js_name});")

    def getTabMode(self):
        if self.dictInt.tabB.singleTab:
            return "true"
        return "false"

    def getHTMLResult(self, term, selectedGroup, idName=""):
        singleTab = self.getTabMode()
        cleaned = self.cleanTerm(term)
        font = self.getFontFamily(selectedGroup)
        dictDefs = self.config["dictSearch"]
        maxDefs = self.config["maxSearch"]

        # Fetch standard results first to get potential starCount
        results = self.db.searchTerm(
            term,
            selectedGroup,
            self.conjugations,
            self.sType.currentText(),
            self.deinflect,
            str(dictDefs),
            maxDefs,
        )

        group_dicts = [d["dict"] for d in selectedGroup["dictionaries"]]

        # Trigger LLM search if enabled and in selected group
        if self.config.get("llm_enabled", False) and "LLM" in group_dicts:
            # Find the best frequency/level info from results to reuse it for LLM
            star_count = ""
            hsk_level = ""
            for d_name, d_results in results.items():
                if not isinstance(d_results, list):
                    continue
                for entry in d_results:
                    # Collect starCount
                    s = entry.get("starCount", "")
                    if s:
                        # Prioritize stars but keep other formats if stars aren't found yet
                        if s.startswith("★"):
                            if not star_count.startswith("★") or len(s) > len(
                                star_count
                            ):
                                star_count = s
                        elif not star_count:
                            star_count = s

                    # Collect hskLevel
                    hsk = entry.get("hskLevel", "")
                    if hsk and len(hsk) > len(hsk_level):
                        hsk_level = hsk

            # If still empty, try a direct DB lookup for the term's frequency/level
            if not star_count and not hsk_level:
                # Find any language associated with this group
                for d in selectedGroup["dictionaries"]:
                    lang = d.get("lang")
                    if lang:
                        freq_info = self.db.get_term_frequency_info(
                            cleaned, lang, self.config
                        )
                        if freq_info.get("starCount"):
                            star_count = freq_info["starCount"]
                        if freq_info.get("hskLevel"):
                            hsk_level = freq_info["hskLevel"]
                        if star_count or hsk_level:
                            break

            self.triggerLLMSearch(cleaned, star_count, hsk_level, idName)

        # Trigger Forvo search if enabled and in selected group
        forvoId = ""
        if self.config.get("forvo_enabled", False) and "Forvo" in group_dicts:
            # Find the language for Forvo in this group
            forvo_lang = self.config.get("forvo_language", "ja")
            for d in selectedGroup["dictionaries"]:
                if d["dict"] == "Forvo" and d.get("lang"):
                    forvo_lang = d["lang"]
                    break

            forvoId = f"forvo-loader-{int(time.time() * 1000)}"
            self.triggerForvoSearch(cleaned, forvoId, forvo_lang)

        html = self.prepareResults(results, cleaned, font, idName, forvoId)
        html = html.replace("\n", "")
        return html, cleaned, singleTab

    def addNewTab(self, term, selectedGroup):
        if (
            selectedGroup["customFont"]
            and selectedGroup["font"] not in self.customFontsLoaded
        ):
            self.customFontsLoaded.append(selectedGroup["font"])
            self.injectFont(selectedGroup["font"])

        # Generate a unique idName for this search to track LLM results across tabs
        import time

        idName = f"llm-loader-{int(time.time() * 1000)}"

        html, cleaned, singleTab = self.getHTMLResult(term, selectedGroup, idName)

        # Use json.dumps for all string arguments to safely handle single quotes,
        # newlines, and other special characters in the HTML or term.
        js_html = json.dumps(html.replace("\r", "").replace("\n", ""))
        js_cleaned = json.dumps(cleaned)
        js_singleTab = "true" if singleTab == "true" else "false"
        js_idName = json.dumps(idName)

        self.eval(f"addNewTab({js_html}, {js_cleaned}, {js_singleTab}, {js_idName});")

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
                logger.error(f"Error during highlightTarget: {e}")
                return text  # Fallback to the original text
        return text

    def processDefinitionHTML(self, text):
        """Process HTML tags in dictionary definitions for proper display."""
        if not isinstance(text, str):
            text = str(text) if text is not None else ""

        # Handle <br> tags that might be in definitions
        # Convert any existing <br> or <br/> or <BR> tags to proper HTML line breaks
        text = re.sub(r"<br\s*/?>", "<br>", text, flags=re.IGNORECASE)

        # Handle other common HTML entities that might appear in definitions
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

        # Ensure proper line spacing for better readability
        # Replace multiple consecutive <br> tags with proper spacing
        text = re.sub(r"(<br>\s*){2,}", "<br><br>", text)

        # Strip leading and trailing <br> tags
        text = re.sub(r"^(<br>\s*)+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(<br>\s*)+$", "", text, flags=re.IGNORECASE)

        return text.strip()

    def getSideBar(self, results, term, font, frontBracket, backBracket):
        html = "<div" + font + 'class="definitionSideBar"><div class="innerSideBar">'
        dictCount = 0
        entryCount = 0
        for dictName, dictResults in results.items():
            display_name = self.db.cleanDictName(dictName).replace("_", " ")
            if dictName in ["Images", "LLM", "Forvo"]:
                html += (
                    '<div data-index="'
                    + str(dictCount)
                    + '" class="listTitle">'
                    + display_name
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
                + display_name
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

    def getTooltips(self):
        """Get consistent tooltips for dictionary header buttons."""
        if not self.config.get("tooltips", True):
            return "", "", ""

        imgTooltip = ' title="Add this definition, or any selected text to the card exporter (opens the card exporter if it is not yet opened)." '
        clipTooltip = (
            ' title="Copy this definition, or any selected text to the clipboard." '
        )
        sendTooltip = ' title="Send this definition, or any selected text to this dictionary\'s target fields. It will send it to the current target window" '

        return imgTooltip, clipTooltip, sendTooltip

    def getStarTooltip(self, starCount: str) -> str:
        """Get tooltip for star rating."""
        if not starCount or not isinstance(starCount, str):
            return ""

        # Mapping stars to rank info
        ranks = {
            "★★★★★": "Top 1,500",
            "★★★★": "Top 5,000",
            "★★★": "Top 15,000",
            "★★": "Top 30,000",
            "★": "Top 60,000",
        }

        # Extract just the stars if it's an LLM result (e.g. "LLM ★★★★★")
        lookup_stars = starCount
        if " " in starCount:
            lookup_stars = starCount.split(" ")[-1]

        rank = ranks.get(lookup_stars, "")
        if rank:
            return f' title="Frequency: {rank}" '
        return ""

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

        clean_name = self.db.cleanDictName(dictName)

        if (
            not self.termHeaders
            or dictName in ["Images", "LLM", "Forvo"]
            or clean_name in ["Images", "LLM", "Forvo"]
        ):
            if sb:
                header = '◳f<span class="listTerm">◳t</span>◳b ◳x<span class="listAltTerm">◳a</span>◳y <span class="listPronunciation">◳p</span>'
            else:
                header = '◳f<span class="term mainword">◳t</span>◳b ◳x<span class="altterm  mainword">◳a</span>◳y <span class="pronunciation">◳p</span>'
        else:
            # Try both original and clean name to be safe
            lookup_name = dictName if dictName in self.termHeaders else clean_name
            if lookup_name in self.termHeaders:
                if sb:
                    header = self.termHeaders[lookup_name][1]
                else:
                    header = self.termHeaders[lookup_name][0]
            else:
                # Fallback to default if still not found
                if sb:
                    header = '◳f<span class="listTerm">◳t</span>◳b ◳x<span class="listAltTerm">◳a</span>◳y <span class="listPronunciation">◳p</span>'
                else:
                    header = '◳f<span class="term mainword">◳t</span>◳b ◳x<span class="altterm  mainword">◳a</span>◳y <span class="pronunciation">◳p</span>'

        return (
            header.replace("◳t", self.highlightTarget(term, target))
            .replace("◳a", self.highlightTarget(altterm, target))
            .replace("◳p", self.highlightTarget(pronunciation, target))
            .replace("◳f", frontBracket)
            .replace("◳b", backBracket)
            .replace("◳x", altFB)
            .replace("◳y", altBB)
        )

    def prepareResults(self, results, term, font, idName="", forvoId=""):
        frontBracket = self.config["frontBracket"]
        backBracket = self.config["backBracket"]

        # Determine if we should show results (standard dicts OR special virtual dicts)
        has_special = any(
            special in self.dictInt.getSelectedDictGroup()["dictionaries"]
            for special in [
                {"dict": "Images", "lang": ""},
                {"dict": "LLM", "lang": ""},
                {"dict": "Forvo", "lang": ""},
            ]
        )
        # A more robust check for special dictionaries being present in the current group
        group_dicts = [
            d["dict"] for d in self.dictInt.getSelectedDictGroup()["dictionaries"]
        ]
        has_special = any(d in ["Images", "LLM", "Forvo"] for d in group_dicts)

        if len(results) > 0 or has_special:
            html = self.getSideBar(results, term, font, frontBracket, backBracket)
            html += '<div class="mainDictDisplay">'
            dictCount = 0
            entryCount = 0
            imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

            group = self.dictInt.getSelectedDictGroup()
            for dInfo in group["dictionaries"]:
                dictName = dInfo["dict"]
                if dictName == "Images":
                    html += self.getGoogleDictionaryResults(
                        term, dictCount, frontBracket, backBracket, entryCount, font
                    )
                    dictCount += 1
                    entryCount += 1
                    continue
                if dictName == "LLM":
                    if self.config.get("llm_enabled", False):
                        duplicateHeader = self.getDuplicateHeaderCB(dictName)
                        overwrite = self.getOverwriteChecks(dictCount, dictName)
                        select = self.getFieldChecks(dictName)
                        # Use the unique idName for the loader container
                        loaderId = idName if idName else "llm-loader"
                        html += (
                            f'<div id="{loaderId}">'
                            '<div data-index="'
                            + str(dictCount)
                            + '" class="dictionaryTitleBlock"><div '
                            + font
                            + ' class="dictionaryTitle">LLM</div><div class="dictionarySettings">'
                            + duplicateHeader
                            + overwrite
                            + select
                            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
                            '<div class="definitionBlock llm-loading-placeholder"><i>Loading LLM definition...</i></div>'
                            "</div>"
                        )
                    dictCount += 1
                    entryCount += 1
                    continue
                if dictName == "Forvo":
                    if self.config.get("forvo_enabled", False):
                        duplicateHeader = self.getDuplicateHeaderCB(dictName)
                        overwrite = self.getOverwriteChecks(dictCount, dictName)
                        select = self.getFieldChecks(dictName)
                        # Use the unique forvoId for the loader container
                        loaderId = forvoId if forvoId else "forvo-loader"
                        html += (
                            f'<div id="{loaderId}">'
                            '<div data-index="'
                            + str(dictCount)
                            + '" class="dictionaryTitleBlock"><div '
                            + font
                            + ' class="dictionaryTitle">Forvo</div><div class="dictionarySettings">'
                            + duplicateHeader
                            + overwrite
                            + select
                            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
                            '<div class="definitionBlock"><i>Loading Forvo pronunciations...</i></div>'
                            "</div>"
                        )
                    dictCount += 1
                    entryCount += 1
                    continue

                # Robust result lookup: check original name, clean name, and normalized name
                cleanName = self.db.cleanDictName(dictName)
                normalizedName = self.db.normalize_dict_name(dictName)

                dictResults = None
                if dictName in results:
                    dictResults = results[dictName]
                elif cleanName in results:
                    dictResults = results[cleanName]
                elif normalizedName in results:
                    dictResults = results[normalizedName]

                if dictResults is not None:
                    duplicateHeader = self.getDuplicateHeaderCB(dictName)
                    overwrite = self.getOverwriteChecks(dictCount, dictName)
                    select = self.getFieldChecks(dictName)
                    html += (
                        '<div data-index="'
                        + str(dictCount)
                        + '" class="dictionaryTitleBlock"><div  '
                        + font
                        + '  class="dictionaryTitle">'
                        + cleanName.replace("_", " ")
                        + '</div><div class="dictionarySettings">'
                        + duplicateHeader
                        + overwrite
                        + select
                        + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
                    )
                    dictCount += 1

                    for idx, entry in enumerate(dictResults):
                        # Extract frequency data and clean definition
                        # Pattern: 【word】[freq]
                        extracted_freq = ""
                        definition = entry["definition"].strip()

                        # Loop to remove all leading 【...】 blocks and leading <br> tags
                        while True:
                            # 0. Strip leading/trailing <br> tags and whitespace that might be left from previous iterations
                            definition = re.sub(
                                r"^(<br>\s*)+|(<br>\s*)+$",
                                "",
                                definition,
                                flags=re.IGNORECASE,
                            ).strip()

                            # 1. Match 【word】[freq]
                            freq_match = re.search(
                                r"^【[^】]+】\s*\[([\dk+]+)\]\s*", definition
                            )
                            if freq_match:
                                if not extracted_freq:
                                    extracted_freq = freq_match.group(1)
                                definition = definition[freq_match.end() :].strip()
                                continue

                            # 2. Match 【word】 pattern without frequency
                            head_match = re.search(r"^【[^】]+】\s*", definition)
                            if head_match:
                                definition = definition[head_match.end() :].strip()
                                continue

                            break

                        # 3. Remove other bracketed headword repeats: (word), （word）, [word], ［word］
                        # Also handles cases like (Simplified, Traditional) if the term is part of it
                        term_escaped = re.escape(entry["term"])
                        # Matches (anything term anything) where brackets are () or （） or [] or ［］
                        repeat_pattern = (
                            r"^\s*[\(\（\[［][^）\)]*?"
                            + term_escaped
                            + r"[^）\)]*?[\)\）\]］]\s*"
                        )
                        definition = re.sub(repeat_pattern, "", definition)

                        # Final strip of leading/trailing <br> and whitespace
                        definition = re.sub(
                            r"^(<br>\s*)+|(<br>\s*)+$",
                            "",
                            definition,
                            flags=re.IGNORECASE,
                        ).strip()

                        if not extracted_freq and entry.get("frequency"):
                            extracted_freq = str(entry["frequency"])

                        # Update the entry's definition with the cleaned version
                        entry["definition"] = definition

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
                            + ' <span class="starcount"'
                            + self.getStarTooltip(entry["starCount"])
                            + ">"
                            + entry["starCount"]
                            + "</span>"
                            + (
                                f' <span class="starcount frequency-rank">[{extracted_freq}]</span>'
                                if extracted_freq
                                else ""
                            )
                            + (
                                f' <span class="starcount hsk-level">{entry["hskLevel"]}</span>'
                                if entry.get("hskLevel")
                                else ""
                            )
                            + '</span><div class="defTools"><div onclick="ankiExport(event, \''
                            + cleanName
                            + '\')" class="ankiExportButton"><img '
                            + imgTooltip
                            + ' src="'
                            + self.getBase64Icon("anki.svg")
                            + '"></div><div onclick="clipText(event)" '
                            + clipTooltip
                            + ' class="clipper">✂</div><div '
                            + sendTooltip
                            + " onclick=\"sendToField(event, '"
                            + cleanName
                            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div'
                            + font
                            + ' class="definitionBlock">'
                            + self.highlightTarget(
                                self.processDefinitionHTML(entry["definition"]),
                                term,
                            )
                            + "</div>"
                        )
                        entryCount += 1

        else:
            html = (
                '<style>.noresults{font-family: Arial;}.vertical-center{height: 400px; width: 60%; margin: 0 auto; display: flex; justify-content: center; align-items: center;}</style> </head> <div class="vertical-center noresults"> <div align="center"> <img src="'
                + self.getBase64Icon("search.svg")
                + '" width="50px" height="40px"> <h3 align="center">No dictionary entries were found for "'
                + term
                + '".</h3> </div></div>'
            )
        return html

    def getGoogleDictionaryResults(
        self, term, dictCount, bracketFront, bracketBack, entryCount, font
    ):
        dictName = "Images"
        overwrite = self.getOverwriteChecks(dictCount, dictName)
        select = self.getFieldChecks(dictName)
        # Sanitize idName by removing dots to prevent JS selector issues
        idName = "gcon" + str(time.time()).replace(".", "")
        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()
        html = (
            '<div data-index="'
            + str(dictCount)
            + '" class="dictionaryTitleBlock"><div class="dictionaryTitle">Images</div><div class="dictionarySettings">'
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
            + '\')" class="ankiExportButton"><img '
            + imgTooltip
            + ' src="'
            + self.getBase64Icon("anki.svg")
            + '"></div><div onclick="clipText(event)" '
            + clipTooltip
            + ' class="clipper">✂</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
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
        # Set search region based on configuration
        imager.setSearchRegion(self.config.get("imageSearchRegion", "United States"))
        imager.signals.resultsFound.connect(self.loadImageResults)
        imager.signals.noResults.connect(self.showNoImagesMessage)
        self.threadpool.start(imager)

        return "Loading..."

    def showNoImagesMessage(self):
        tooltip("No images found")

    def triggerLLMSearch(self, term, star_count="", hsk_level="", idName=""):
        """Initiate an asynchronous LLM search."""
        worker = llm_integration.LLMWorker(
            term, self.config, star_count, hsk_level, idName
        )
        worker.signals.result_ready.connect(self.loadLLMResults)
        worker.signals.error_occurred.connect(self.showLLMError)
        self.threadpool.start(worker)

    def loadLLMResults(self, result):
        """Handle result from LLM and inject into the UI."""
        dictName = result.get("dictName", "LLM")
        # Handle both missing key and empty string for idName
        idName = result.get("idName") or "llm-loader"
        font = self.getFontFamily({"font": False, "customFont": False})

        # Format just the content part (without header and title block)
        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

        frontBracket = self.config["frontBracket"]
        backBracket = self.config["backBracket"]

        html = (
            '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + self.getPreparedTermHeader(
                dictName,
                frontBracket,
                backBracket,
                result["term"],
                result["term"],
                result.get("altterm", ""),
                result.get("pronunciation", ""),
            )
            + ' <span class="starcount"'
            + self.getStarTooltip(str(result.get("starCount", "")))
            + ">"
            + str(result.get("starCount", ""))
            + "</span>"
            + (
                f' <span class="starcount hsk-level">{result["hskLevel"]}</span>'
                if result.get("hskLevel")
                else ""
            )
            + '</span><div class="defTools"><div onclick="ankiExport(event, \''
            + dictName
            + '\')" class="ankiExportButton"><img '
            + imgTooltip
            + ' src="'
            + self.getBase64Icon("anki.svg")
            + '"></div><div onclick="clipText(event)" '
            + clipTooltip
            + ' class="clipper">✂</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div>'
        )

        # Process markdown and clean up the definition
        definition = result["definition"]

        # Simple Markdown-like processing
        # Bold: **text**, __text__, or ★★text★★
        definition = re.sub(r"(\*\*|__|★★)(.*?)\1", r"<b>\2</b>", definition)
        # Italic: *text* or _text_
        definition = re.sub(r"(\*|_)(.*?)\1", r"<i>\2</i>", definition)
        # Support for common dictionary stars
        definition = definition.replace("★", "<b>★</b>")
        # Lists: - item or * item
        definition = re.sub(r"^\s*[-*+]\s+", r"• ", definition, flags=re.MULTILINE)

        # Remove a duplicate header if the LLM repeats the term at the beginning or end
        # This addresses the user report about duplicate headers (one before, one after)
        term = result["term"].lower()
        lines = definition.split("\n")
        if len(lines) > 1:
            # Check for header at the start (e.g. "**Word**\nDefinition")
            first_line = (
                lines[0]
                .strip()
                .lower()
                .replace("<b>", "")
                .replace("</b>", "")
                .replace("**", "")
                .replace("#", "")
                .strip()
            )
            if first_line == term:
                definition = "\n".join(lines[1:]).strip()

            # Re-check for header at the end (e.g. "Definition\n**Word**")
            lines = definition.split("\n")
            if len(lines) > 1:
                last_line = (
                    lines[-1]
                    .strip()
                    .lower()
                    .replace("<b>", "")
                    .replace("</b>", "")
                    .replace("**", "")
                    .replace("#", "")
                    .strip()
                )
                if last_line == term:
                    definition = "\n".join(lines[:-1]).strip()

        # Remove bracketed headword repeats: (word), （word）, [word], ［word］
        # Also handles cases like (Simplified, Traditional) if the term is part of it
        term_escaped = re.escape(result["term"])
        # Matches (anything term anything) where brackets are () or （） or [] or ［］
        repeat_pattern = (
            r"^\s*[\(\（\[［][^）\)]*?" + term_escaped + r"[^）\)]*?[\)\）\]］]\s*"
        )
        definition = re.sub(repeat_pattern, "", definition).strip()

        html += (
            "<div"
            + font
            + ' class="definitionBlock">'
            + self.highlightTarget(
                self.processDefinitionHTML(definition),
                result["term"],
            )
            + "</div>"
        )
        # Inject into the webview by replacing only the loading placeholder
        escaped_html = json.dumps(html)
        self.eval(
            f"console.log('LLM: Starting injection for ID: {idName}'); "
            f"var loader = document.getElementById('{idName}'); "
            f"if(loader) {{ "
            f"  console.log('LLM: Found loader element'); "
            f"  var placeholder = loader.querySelector('.llm-loading-placeholder'); "
            f"  if(placeholder) {{ "
            f"    console.log('LLM: Found placeholder, replacing with content'); "
            f"    placeholder.outerHTML = {escaped_html}; "
            f"  }} else {{ "
            f"    console.log('LLM: Placeholder not found, looking for definitionBlock'); "
            f"    var oldContent = loader.querySelector('.definitionBlock'); "
            f"    if(oldContent) {{ "
            f"      console.log('LLM: Removing old definitionBlock'); "
            f"      oldContent.remove(); "
            f"    }} "
            f"    var titleBlock = loader.querySelector('.dictionaryTitleBlock'); "
            f"    if(titleBlock) {{ "
            f"       console.log('LLM: Injecting after titleBlock'); "
            f"       titleBlock.insertAdjacentHTML('afterend', {escaped_html}); "
            f"    }} else {{ "
            f"       console.log('LLM: Title block not found, appending to loader'); "
            f"       loader.insertAdjacentHTML('beforeend', {escaped_html}); "
            f"    }} "
            f"  }} "
            f"}} else {{ "
            f"  console.error('LLM: Container ID not found in DOM: {idName}'); "
            f"}}"
        )

    def formatSingleEntry(self, result, dictName, font, frontBracket, backBracket):
        """Helper to format a single dictionary entry (LLM or other) to HTML."""
        # result now contains 'dictName' from LLMWorker
        dictCount = 999  # Large index to avoid conflict
        duplicateHeader = self.getDuplicateHeaderCB(dictName)
        overwrite = self.getOverwriteChecks(dictCount, dictName)
        select = self.getFieldChecks(dictName)

        html = (
            '<div class="dictionaryTitleBlock"><div '
            + font
            + ' class="dictionaryTitle">'
            + dictName
            + '</div><div class="dictionarySettings">'
            + duplicateHeader
            + overwrite
            + select
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
        )

        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

        html += (
            '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + self.getPreparedTermHeader(
                dictName,
                frontBracket,
                backBracket,
                result["term"],
                result["term"],
                result.get("altterm", ""),
                result.get("pronunciation", ""),
            )
            + ' <span class="starcount"'
            + self.getStarTooltip(str(result.get("starCount", "")))
            + ">"
            + str(result.get("starCount", ""))
            + "</span>"
            + (
                f' <span class="starcount hsk-level">{result["hskLevel"]}</span>'
                if result.get("hskLevel")
                else ""
            )
            + '</span><div class="defTools"><div onclick="ankiExport(event, \''
            + dictName
            + '\')" class="ankiExportButton"><img '
            + imgTooltip
            + ' src="'
            + self.getBase64Icon("anki.svg")
            + '"></div><div onclick="clipText(event)" '
            + clipTooltip
            + ' class="clipper">✂</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div>'
        )

        # Process markdown and clean up the definition
        definition = result["definition"]

        # Simple Markdown-like processing
        # Bold: **text**, __text__, or ★★text★★
        definition = re.sub(r"(\*\*|__|★★)(.*?)\1", r"<b>\2</b>", definition)
        # Italic: *text* or _text_
        definition = re.sub(r"(\*|_)(.*?)\1", r"<i>\2</i>", definition)
        # Support for common dictionary stars
        definition = definition.replace("★", "<b>★</b>")
        # Lists: - item or * item
        definition = re.sub(r"^\s*[-*+]\s+", r"• ", definition, flags=re.MULTILINE)

        # Remove a duplicate header if the LLM repeats the term at the beginning or end
        term = result["term"].lower()
        lines = definition.split("\n")
        if len(lines) > 1:
            # Check for header at the start (e.g. "**Word**\nDefinition")
            first_line = (
                lines[0]
                .strip()
                .lower()
                .replace("<b>", "")
                .replace("</b>", "")
                .replace("**", "")
                .replace("#", "")
                .strip()
            )
            if first_line == term:
                definition = "\n".join(lines[1:]).strip()

            # Re-check for header at the end (e.g. "Definition\n**Word**")
            lines = definition.split("\n")
            if len(lines) > 1:
                last_line = (
                    lines[-1]
                    .strip()
                    .lower()
                    .replace("<b>", "")
                    .replace("</b>", "")
                    .replace("**", "")
                    .replace("#", "")
                    .strip()
                )
                if last_line == term:
                    definition = "\n".join(lines[:-1]).strip()

        # Remove bracketed headword repeats: (word), （word）, [word], ［word］
        # Also handles cases like (Simplified, Traditional) if the term is part of it
        term_escaped = re.escape(result["term"])
        # Matches (anything term anything) where brackets are () or （） or [] or ［］
        repeat_pattern = (
            r"^\s*[\(\（\[［][^）\)]*?" + term_escaped + r"[^）\)]*?[\)\）\]］]\s*"
        )
        definition = re.sub(repeat_pattern, "", definition).strip()

        html += (
            "<div"
            + font
            + ' class="definitionBlock">'
            + self.highlightTarget(
                self.processDefinitionHTML(definition),
                result["term"],
            )
            + "</div>"
        )
        return html

    def showLLMError(self, result):
        """Show LLM error in the UI."""
        error_msg = result.get("error", "Unknown LLM error")
        # Handle both missing key and empty string for idName
        idName = result.get("idName") or "llm-loader"

        # Use consistent logic with loadLLMResults to ensure the loading state is cleared
        escaped_msg = json.dumps(
            f'<div class="definitionBlock llm-error" style="color: #ff5555; border: 1px solid #ff5555; padding: 15px; border-radius: 8px; background-color: rgba(255, 85, 85, 0.05);">'
            f'<div style="font-weight: bold; margin-bottom: 8px; font-size: 1.1em;">LLM Connection Error</div>'
            f'<div style="margin-bottom: 12px; font-family: monospace; font-size: 0.9em; opacity: 0.9; word-break: break-all;">{error_msg}</div>'
            f'<div style="font-size: 0.85em; opacity: 0.8;">'
            f"Possible causes:<ul>"
            f"<li>Local LLM (like Ollama) is not running</li>"
            f"<li>Wrong API key or Base URL</li>"
            f'<li>Network timeout (current timeout: {self.config.get("llm_timeout", 15)}s)</li>'
            f"</ul></div></div>"
        )
        self.eval(
            f"var loader = document.getElementById('{idName}'); "
            f"if(loader) {{ "
            f"  console.log('LLM Error ID found: ' + '{idName}'); "
            f"  var oldContent = loader.querySelector('.definitionBlock'); "
            f"  if(oldContent) oldContent.remove(); "
            f"  var titleBlock = loader.querySelector('.dictionaryTitleBlock'); "
            f"  if(titleBlock) {{ "
            f"    titleBlock.insertAdjacentHTML('afterend', {escaped_msg}); "
            f"  }} else {{ "
            f"    loader.insertAdjacentHTML('beforeend', {escaped_msg}); "
            f"  }} "
            f"}} else {{ "
            f"  console.warn('LLM Error ID not found: ' + '{idName}'); "
            f"}}"
        )

    def triggerForvoSearch(self, term, idName="", language=None):
        """Initiate an asynchronous Forvo search."""
        if not language:
            language = self.config.get("forvo_language", "ja")
        worker = forvo_integration.ForvoWorker(term, language, self.config, idName)
        worker.signals.result_ready.connect(self.onForvoResult)
        worker.signals.error_occurred.connect(self.onForvoError)
        self.threadpool.start(worker)

    def onForvoResult(self, result):
        """Handle results from Forvo search and inject into the UI."""
        # Handle both missing key and empty string for idName
        idName = result.get("idName") or "forvo-loader"
        term = result.get("term", "")
        items = result.get("items", [])

        if not items:
            group = self.dictInt.getSelectedDictGroup()
            if len(group.get("dictionaries", [])) > 1:
                # If there are other dictionaries, just remove the Forvo section entirely
                self.eval(
                    f"var el = document.getElementById('{idName}'); "
                    f"if(el) el.remove(); "
                    f"var titles = document.querySelectorAll('.listTitle'); "
                    f"for (var i = 0; i < titles.length; i++) {{ "
                    f"  if (titles[i].textContent === 'Forvo') {{ "
                    f"    var list = titles[i].nextElementSibling; "
                    f"    if (list && list.classList.contains('foundEntriesList')) list.remove(); "
                    f"    titles[i].remove(); "
                    f"    break; "
                    f"  }} "
                    f"}}"
                )
                return
            else:
                self.onForvoError(
                    {"error": "No pronunciations found on Forvo.", "idName": idName}
                )
                return

        font = self.getFontFamily({"font": False, "customFont": False})
        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

        # Header part (only once)
        frontBracket = self.config["frontBracket"]
        backBracket = self.config["backBracket"]
        dictName = "Forvo"

        header_html = (
            f'<div class="termPronunciation"><span {font} class="tpCont">'
            f'{frontBracket}<span class="terms">{self.highlightTarget(term, term)}</span>{backBracket} '
            f'</span><div class="defTools">'
            f'<div onclick="ankiExport(event, \'{dictName}\')" class="ankiExportButton"><img '
            + imgTooltip
            + ' src="'
            + self.getBase64Icon("anki.svg")
            + '"></div><div onclick="clipText(event)" '
            + clipTooltip
            + ' class="clipper">✂</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div>'
        )

        # Content part (pronunciations with limit)
        forvo_limit = self.config.get("forvo_limit", 3)
        content_html = f'<div {font} class="definitionBlock"><div class="forvo-container" style="padding: var(--spacing-sm) 0;">'

        for idx, item in enumerate(items):
            user = item.get("user", "Unknown")
            votes = item.get("votes", 0)
            origin = item.get("origin", "")
            audio_url = item.get("audio_url", "")

            # Hide items beyond the limit
            item_style = "display: flex; align-items: center; margin-bottom: var(--spacing-sm); padding: var(--spacing-sm); border-bottom: 1px solid var(--border);"
            extra_class = ""
            if idx >= forvo_limit:
                item_style += " display: none;"
                extra_class = "forvo-extra"

            content_html += (
                f'<div class="forvo-item {extra_class}" style="{item_style}">'
                f'<div onclick="animateForvoPlay(this); playAudio(\'{audio_url}\')" style="cursor:pointer; font-size: 20px; margin-right: var(--spacing-md); color: var(--primary); width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary-light, rgba(33, 150, 243, 0.1)); transition: transform var(--transition-fast);" title="Play Pronunciation" onmouseover="this.style.transform=\'scale(1.1)\'" onmouseout="this.style.transform=\'scale(1)\'">'
                f'<span class="forvo-icon">▶</span>'
                f'<span class="equalizer-bar"></span>'
                f'<span class="equalizer-bar"></span>'
                f'<span class="equalizer-bar"></span>'
                f"</div>"
                f'<div style="flex-grow: 1;">'
                f'<b style="color: var(--text);">{user}</b> <span style="font-size: 0.85em; color: var(--text-muted, #666);">{origin}</span>'
                f'<div style="font-size: 0.8em; color: var(--text-muted, #666); opacity: 0.8;">Votes: {votes}</div>'
                f"</div>"
                f'<div class="defTools" style="margin-left: auto; display: flex; gap: var(--spacing-sm);">'
                f'<div onclick="ankiAudioExport(\'{term}\', \'{audio_url}\')" class="ankiExportButton" title="Export Audio">'
                f'<img {imgTooltip} src="{self.getBase64Icon("anki.svg")}" style="width: 18px; height: 18px;"></div>'
                f'<div onclick="sendAudioToField(\'{audio_url}\')" {sendTooltip} class="sendToField" title="Send Audio to Field" style="font-size: 16px;">➠</div>'
                f"</div>"
                f"</div>"
            )

        # Add "Load More" button if there are more items
        if len(items) > forvo_limit:
            content_html += (
                f'<div onclick="showMoreForvo(this)" class="forvo-load-more" style="text-align: center; padding: var(--spacing-sm); cursor: pointer; color: var(--primary); font-weight: bold; margin-top: var(--spacing-sm); border: 1px dashed var(--primary); border-radius: var(--border-radius-sm);">'
                f"Load more ({len(items) - forvo_limit})"
                f"</div>"
            )

        content_html += "</div></div>"

        # Combine header and content
        full_html = header_html + content_html
        escaped_html = json.dumps(full_html)

        self.eval(
            f"var loader = document.getElementById('{idName}'); "
            f"if(loader) {{ "
            f"  var titleBlock = loader.querySelector('.dictionaryTitleBlock'); "
            f"  if(titleBlock) {{ "
            f"    loader.innerHTML = ''; "
            f"    loader.appendChild(titleBlock); "
            f"    titleBlock.insertAdjacentHTML('afterend', {escaped_html}); "
            f"  }} "
            f"}}"
        )

    def onForvoError(self, result):
        """Show Forvo error in the UI."""
        error_msg = result.get("error", "Unknown Forvo error")
        # Handle both missing key and empty string for idName
        idName = result.get("idName") or "forvo-loader"
        escaped_msg = json.dumps(
            f'<div class="definitionBlock" style="color: red;">{error_msg}</div>'
        )
        self.eval(
            f"var loader = document.getElementById('{idName}'); if(loader) {{ loader.innerHTML = {escaped_msg}; }}"
        )

    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        return [x.replace("\\", "\\\\") for x in urls]

    def getDuplicateHeaderCB(self, dictName: str) -> str:
        tooltip = ""
        if self.config["tooltips"]:
            tooltip = ' title="Enable this option if this dictionary has the target word\'s header within the definition. Enabling this will prevent the addon from exporting duplicate header."'
        checked = " "

        # Clean name for both internal settings and HTML classes
        clean_name = self.db.cleanDictName(dictName)
        className = "checkDict" + re.sub(r"\s", "", clean_name)

        # Check settings using both original and clean name
        lookup_name = dictName if dictName in self.dupHeaders else clean_name
        if lookup_name in self.dupHeaders:
            num = self.dupHeaders[lookup_name]
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
        elif dAct.startswith("updateTerm:"):
            term = dAct[11:]
            self.dictInt.search.setText(term)
        elif dAct.startswith("saveFS:"):
            f1, f2 = dAct[7:].split(":")
            self.dictInt.writeConfig("fontSizes", [int(f1), int(f2)])
        elif dAct.startswith("setDup:"):
            dup, name = dAct[7:].split("◳")
            dup = int(dup)
            clean_name = self.db.cleanDictName(name)
            self.dictInt.db.setDupHeader(dup, clean_name)
            self.dupHeaders = self.db.getDupHeaders()
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
            self.copyImagesToClipboard(urls_json)
        elif dAct.startswith("sendToField:"):
            name, text = dAct[12:].split("◳◴")
            self.sendToField(name, text)
        elif dAct.startswith("sendAudioToField:"):
            urls = dAct[17:]
            self.sendAudioToField(urls)
        elif dAct.startswith("sendImgToField:"):
            urls = dAct[15:]
            self.sendImgToField(urls)
        elif dAct.startswith("playAudio:"):
            url = dAct[10:]
            self.playAudio(url)
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
        # Set search region based on configuration
        imager.setSearchRegion(self.config.get("imageSearchRegion", "United States"))
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
            logger.error(f"Error in loadMoreImageResults: {e}")
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
                if imgurl.startswith("data:"):
                    filename = str(time.time())[:-4].replace(".", "") + "base64.avif"
                else:
                    url = re.sub(r"\?.*$", "", imgurl)
                    filename = (
                        str(time.time())[:-4].replace(".", "")
                        + re.sub(r"\..*$", "", url.strip().split("/")[-1])
                        + ".avif"
                    )
                fullpath = join(self.dictInt.mw.col.media.dir(), filename)
                self.saveQImage(imgurl, fullpath)
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
        if url.startswith("data:"):
            try:
                # Handle data:image/xxx;base64,xxxx
                header, encoded = url.split(",", 1)
                file = base64.b64decode(encoded)
            except Exception as e:
                logger.error(f"Error decoding data URL: {e}")
                return
        else:
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                },
            )
            file = urlopen(req, timeout=30).read()

        image = QImage()
        image.loadFromData(file)
        if not image.isNull():
            image = image.scaled(
                QSize(self.maxW, self.maxH),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if filename.lower().endswith(".avif"):
                image.save(filename, "AVIF")
            else:
                image.save(filename)

    def copyImagesToClipboard(self, urls_json: str) -> None:
        """Copy images from a list of URLs (data: or http:) to the system clipboard."""
        try:
            urls = json.loads(urls_json)
            if not urls:
                return

            from urllib.request import Request, urlopen
            from aqt.qt import QMimeData, QUrl

            mime_data = QMimeData()
            urls_list = []

            # For a single image, we can also set the image directly for convenience
            first_image = None

            for idx, url in enumerate(urls):
                try:
                    if url.startswith("data:"):
                        # Handle data:image/xxx;base64,xxxx
                        header, encoded = url.split(",", 1)
                        file_data = base64.b64decode(encoded)
                        ext = header.split("/")[1].split(";")[0]
                    else:
                        req = Request(
                            url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                            },
                        )
                        file_data = urlopen(req, timeout=10).read()
                        ext = url.split(".")[-1].split("?")[0]
                        if len(ext) > 4 or "/" in ext:
                            ext = "avif"

                    image = QImage()
                    image.loadFromData(file_data)

                    if not image.isNull():
                        if first_image is None:
                            first_image = image

                        # Save to temp file to provide as URI
                        temp_path = join(self.temp_dir, f"clipboard_img_{idx}.{ext}")
                        image.save(temp_path)
                        urls_list.append(QUrl.fromLocalFile(temp_path))
                except Exception as e:
                    logger.error(f"Error processing image {idx} for clipboard: {e}")

            if urls_list:
                mime_data.setUrls(urls_list)
                if first_image:
                    mime_data.setImageData(first_image)

                self.dictInt.mw.app.clipboard().setMimeData(mime_data)
                logger.debug(
                    f"Successfully copied {len(urls_list)} images to clipboard."
                )
            else:
                logger.warning("No valid images found to copy to clipboard.")

        except Exception as e:
            logger.error(f"Error copying images to clipboard: {e}")

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
                        # Handle remote URL or data URL
                        if imgurl.startswith("data:"):
                            filename = (
                                str(time.time())[:-4].replace(".", "") + "base64.avif"
                            )
                        else:
                            url = re.sub(r"\?.*$", "", imgurl)
                            filename = (
                                str(time.time())[:-4].replace(".", "")
                                + re.sub(r"\..*$", "", url.strip().split("/")[-1])
                                + ".avif"
                            )

                        self.saveQImage(
                            imgurl, join(self.dictInt.mw.col.media.dir(), filename)
                        )
                        urlsList.append(f'<img src="{filename}">')

                except Exception as e:
                    logger.error(f"Failed to process image: {imgurl}")
                    logger.error(f"Error: {str(e)}")
                    continue
            if len(urlsList) > 0:
                self.sendToField("Images", imgSeparator.join(urlsList))

        else:
            logger.warning("no reviewer or editor")
            tooltip(
                "No active reviewer or editor found. Please open a card to send images to a field."
            )

    def addAudioToExportWindow(self, word: str, url: str) -> None:
        """Download audio from URL and add it to the export window."""
        self.initCardExporterIfNeeded()
        try:
            filename = str(time.time()).replace(".", "") + ".mp3"
            fullpath = join(self.temp_dir, filename)

            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                },
            )
            with open(fullpath, "wb") as f:
                f.write(urlopen(req, timeout=30).read())

            tag = f"[sound:{filename}]"
            self.exportAudio((fullpath, tag, filename))
            self.addWindow.exportWord(word)
        except Exception as e:
            logger.error(f"Error downloading Forvo audio: {e}")
            tooltip(f"Failed to download audio: {e}")

    def sendAudioToField(self, url: str) -> None:
        """Download audio from URL and send it to the selected field."""
        if not (self.reviewer and self.reviewer.card) and not (
            self.currentEditor and self.currentEditor.note
        ):
            tooltip("No active reviewer or editor found.")
            return

        try:
            filename = str(time.time()).replace(".", "") + ".mp3"
            fullpath = join(self.dictInt.mw.col.media.dir(), filename)

            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                },
            )
            with open(fullpath, "wb") as f:
                f.write(urlopen(req, timeout=30).read())

            tag = f"[sound:{filename}]"
            self.sendToField("Forvo", tag)
        except Exception as e:
            logger.error(f"Error sending Forvo audio to field: {e}")
            tooltip(f"Failed to send audio to field: {e}")

    def playAudio(self, url: str) -> None:
        """Download and play audio from URL using Anki's sound system."""
        try:
            filename = "temp_forvo_play.mp3"
            fullpath = join(self.temp_dir, filename)

            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36"
                },
            )
            with open(fullpath, "wb") as f:
                f.write(urlopen(req, timeout=30).read())

            from aqt.sound import play

            play(fullpath)
        except Exception as e:
            logger.error(f"Error playing Forvo audio: {e}")
            tooltip(f"Failed to play audio: {e}")

    def sendToField(self, name: str, definition: str) -> None:
        clean_name = self.db.cleanDictName(name)
        display_name = clean_name.replace("_", " ")
        if not (self.reviewer and self.reviewer.card) and not (
            self.currentEditor and self.currentEditor.note
        ):
            tooltip(
                "No active reviewer or editor found. Please open a card to send definitions to a field."
            )
            return

        if clean_name == "Images":
            tFields = self.config.get("ImageFields", [])
            addType = self.config.get("ImageAddType", "add")
        elif clean_name == "LLM":
            tFields = self.config.get("LLMFields", [])
            addType = self.config.get("LLMAddType", "add")
        elif clean_name == "Forvo":
            tFields = self.config.get("ForvoFields", [])
            addType = self.config.get("ForvoAddType", "add")
        else:
            res = self.db.getAddTypeAndFields(clean_name)
            if not res:
                tooltip(f"Configuration for '{display_name}' not found.")
                return
            tFields, addType = res

        if not tFields:
            tooltip(
                f"No fields selected for '{display_name}'. Please select at least one field in the dictionary settings."
            )
            return

        found_field = False
        if self.reviewer and self.reviewer.card:
            note = self.reviewer.card.note()
            model = note.note_type()
            fields = model["flds"]
            changed = False
            for field in fields:
                if field["name"] in tFields:
                    found_field = True
                    newField = self.getFieldContent(
                        note[field["name"]], definition, addType
                    )
                    if newField is not False:
                        changed = True
                        note[field["name"]] = newField
            if not found_field:
                tooltip(
                    f"None of the selected fields for '{display_name}' were found in the current card."
                )
                return

            if not changed:
                if addType == "no":
                    tooltip(
                        f"Field(s) for '{display_name}' already contain content, and the current setting is to only add if empty."
                    )
                return

            update_note(parent=self.dictInt.mw, note=note).run_in_background()
            if self.reviewer.state == "answer":
                self.reviewer._showAnswer()
            elif self.reviewer.state == "question":
                self.reviewer._showQuestion()
            if hasattr(self.dictInt.mw, "DictReloadEditorAndBrowser"):
                self.dictInt.mw.DictReloadEditorAndBrowser(note)

        if self.currentEditor and self.currentEditor.note:
            note = self.currentEditor.note
            items = note.items()
            currentNoteId = note.id
            for idx, item in enumerate(items):
                noteField = item[0]
                if noteField in tFields:
                    found_field = True
                    self.currentEditor.web.eval(
                        self.dictInt.insertHTMLJS
                        % (
                            definition.replace('"', '\\"'),
                            str(idx),  # Field index
                            addType,  # Action type
                            currentNoteId,  # Pass the note ID to JavaScript
                        )
                    )
            if not found_field:
                tooltip(
                    f"None of the selected fields for '{display_name}' were found in the current card."
                )
                return

    def getOverwriteChecks(self, dictCount: int, dictName: str) -> str:
        clean_name = self.db.cleanDictName(dictName)
        if dictName == "Images" or clean_name == "Images":
            addType = self.config.get("ImageAddType", "add")
        elif dictName == "LLM" or clean_name == "LLM":
            addType = self.config.get("LLMAddType", "add")
        elif dictName == "Forvo" or clean_name == "Forvo":
            addType = self.config.get("ForvoAddType", "add")
        else:
            addType = (
                self.db.getAddType(dictName) or self.db.getAddType(clean_name) or "add"
            )

        tooltip = ""
        if self.config["tooltips"]:
            tooltip = " title=\"This determines the conditions for sending a definition (or a Google Image) to a field. Overwrite the target field's content. Add to the target field's current contents. Only add definitions to the target field if it is empty.\""

        typeName = "&nbsp;Add"  # Default
        if addType == "overwrite":
            typeName = "&nbsp;Overwrite"
        elif addType == "no":
            typeName = "&nbsp;If Empty"
        elif addType == "add":
            typeName = "&nbsp;Add"
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
        clean_name = self.db.cleanDictName(dictName)
        logger.debug(f"getFieldChecks: dictName={dictName}, clean_name={clean_name}")
        if dictName == "Images" or clean_name == "Images":
            selF = self.config.get("ImageFields", [])
        elif dictName == "LLM" or clean_name == "LLM":
            selF = self.config.get("LLMFields", [])
        elif dictName == "Forvo" or clean_name == "Forvo":
            selF = self.config.get("ForvoFields", [])
        else:
            selF = (
                self.db.getFieldsSetting(dictName)
                or self.db.getFieldsSetting(clean_name)
                or []
            )

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
        # Create a custom searchable dropdown with checkboxes
        options = (
            '<div class="fieldCheckboxes" data-dictname="' + dictName + '">'
            '<input type="text" class="fieldSearchInput" placeholder="Search fields..." '
            'onclick="event.stopPropagation()" onkeyup="filterFieldOptions(this)" />'
            '<div class="fieldOptionsContainer">'
        )
        for f in fields:
            checked = ""
            if f in selF:
                checked = " checked"
            options += (
                '<label class="fieldCheckboxLabel"><input type="checkbox"'
                + checked
                + ' class="fieldCheckbox" onchange="handleFieldCheckbox(this)" value="'
                + f
                + '" /><span>'
                + f
                + "</span></label>"
            )
        options += "</div></div>"
        return options

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
        super(DictInterface, self).__init__()
        self.db = dictdb
        self.verticalBar = False
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
        self.threadpool = QThreadPool()  # Initialize QThreadPool
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

    def hex_to_rgba(self, hex_color, alpha):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        r_b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {r_b}, {alpha})"

    def refresh_widget(self, widget):
        """
        Recursively refresh a widget and its children.
        """
        widget.update()
        widget.repaint()
        for child in widget.findChildren(QWidget):
            self.refresh_widget(child)

    def update_window_icon(self):
        """Update the window icon based on the current theme."""
        icon_name = "nightanki.svg" if self.theme_manager.is_dark else "anki.svg"
        self.setWindowIcon(QIcon(join(self.iconpath, icon_name)))

    def refresh_application_theme(self, reload_html=True):
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

        # Update all SVG icons with the theme color
        self.setAllIcons()

        self.update_window_icon()

        if reload_html:
            # Simple reload - just reload the dictionary interface completely
            # We assume it's not a search load here, just a theme refresh
            html, url = self.getHTMLURL(False)
            self.dict.loadHTMLURL(html, url)

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

        # Update search bar style
        active_theme = self.theme_manager.get_active_theme()
        search_style = f"""
            QLineEdit {{
                color: {active_theme.header_text};
                background: {active_theme.header_background};
                border: 1.5px solid {active_theme.border};
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 2px solid {active_theme.search_term};
            }}
        """
        self.search.setStyleSheet(search_style)

        # Update button styles
        for button in self.findChildren(QPushButton):
            if not isinstance(button, SVGPushButton):
                button.setStyleSheet(self.theme_manager.get_qt_styles())

        # Update QFrame spacers
        for frame in self.findChildren(QFrame):
            if (
                frame.frameShape() == QFrame.Shape.VLine
                or frame.frameShape() == QFrame.Shape.HLine
            ):
                # Use a translucent version of the border color for the spacer
                border_color = self.load_theme_color("border")
                r = border_color.red()
                g = border_color.green()
                b = border_color.blue()
                frame.setStyleSheet(f"background-color: rgba({r}, {g}, {b}, 50);")

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
        self.update_window_icon()
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
                        background-color: {active_theme_dict["header_background"]};
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 14px;
                    }}
                    QPushButton {{
                        color: {active_theme_dict['header_text']};
                        border: 1.5px solid {active_theme_dict['border']};
                        border-radius: 6px;
                        padding: 8px;
                        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 {active_theme_dict['current_tab_gradient_top']},
                            stop: 1 {active_theme_dict['current_tab_gradient_bottom']});
                    }}
                    QPushButton:hover {{
                        border: 2px solid {active_theme_dict['search_term']};
                        background: {active_theme_dict['tab_hover']};
                    }}
                    QLineEdit, QComboBox {{
                        background-color: {active_theme_dict['header_background']};
                        color: {active_theme_dict['header_text']};
                        border: 1.5px solid {active_theme_dict['border']};
                        border-radius: 6px;
                        padding: 6px 10px;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid {active_theme_dict['search_term']};
                    }}
                    QLabel {{
                        color: {active_theme_dict['header_text']};
                        font-weight: bold;
                    }}
                    QComboBox QAbstractItemView {{
                        background-color: {active_theme_dict['header_background']};
                        color: {active_theme_dict['header_text']};
                        border: 1px solid {active_theme_dict['border']};
                        selection-background-color: {active_theme_dict['search_term']};
                    }}
                """
        self.setStyleSheet(qss)
        custom_theme_css = f"""
            <style id="customThemeCss">
                :root {{
                    --background: {active_theme_dict['header_background']};
                    --selector: {active_theme_dict['selector']};
                    --background-secondary: {active_theme_dict['selector']};
                    --text: {active_theme_dict['header_text']};
                    --header_text: {active_theme_dict['header_text']};
                    --text-secondary: {active_theme_dict['search_term']};
                    --search_term: {active_theme_dict['search_term']};
                    --border: {active_theme_dict['border']};
                    --button-bg: {active_theme_dict['anki_button_background']};
                    --button-text: {active_theme_dict['anki_button_text']};
                    --button-bg-hover: {active_theme_dict['tab_hover']};
                    --tab_hover: {active_theme_dict['tab_hover']};
                    --definition_background: {active_theme_dict['definition_background']};
                    --definition_text: {active_theme_dict['definition_text']};
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
                    background-color: {self.hex_to_rgba(active_theme_dict['example_highlight'], 0.2)};
                    border-radius: 3px;
                    padding: 1px 4px;
                    margin: 0 2px;
                }}
                .definitionBlock {{
                    background-color: {active_theme_dict['definition_background']};
                    color: {active_theme_dict['definition_text']};
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .altterm {{
                    color: {active_theme_dict['pitch_accent_color']};
                }}
                .ankiExportButton {{
                    border: 1.5px solid {active_theme_dict['border']};
                    border-radius: 6px;
                    padding: 6px;
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                        stop: 0 {active_theme_dict['current_tab_gradient_top']},
                        stop: 1 {active_theme_dict['current_tab_gradient_bottom']});
                    transition: all 0.2s;
                }}
                .ankiExportButton:hover {{
                    border-color: {active_theme_dict['search_term']};
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                }}
                .ankiExportButton img {{
                    height: 28px !important;
                    width: 28px !important;
                }}
                .tablinks {{
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 6px 6px 0 0;
                    margin-right: 2px;
                }}
                .tablinks.active {{
                    background-image: linear-gradient(
                        {active_theme_dict['current_tab_gradient_top']},
                        {active_theme_dict['current_tab_gradient_bottom']}
                    );
                    border-bottom: 2px solid {active_theme_dict['search_term']};
                }}
                .tablinks:hover {{
                    background-color: {active_theme_dict['tab_hover']};
                }}
                .overwriteSelect, .fieldSelect {{
                    background-color: {active_theme_dict['selector']};
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: inherit;
                    cursor: pointer;
                }}
                .fieldSelectCont {{
                    position: relative;
                    min-width: 200px;
                    display: inline-block;
                }}
                .fieldCheckboxes, .overwriteCheckboxes {{
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background-color: {active_theme_dict['header_background']};
                    border: 1px solid {active_theme_dict['border']};
                    border-radius: 0 0 6px 6px;
                    display: none;
                    z-index: 1000;
                    min-width: 250px;
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
                    overflow: hidden;
                    flex-direction: column;
                }}
                .fieldCheckboxes.open, .overwriteCheckboxes.open {{
                    display: flex;
                }}
                .fieldSearchInput {{
                    width: 100%;
                    padding: 8px 10px;
                    border: none;
                    border-bottom: 1px solid {active_theme_dict['border']};
                    background-color: {active_theme_dict['selector']};
                    color: {active_theme_dict['header_text']};
                    box-sizing: border-box;
                    font-size: inherit;
                    outline: none;
                    flex-shrink: 0;
                }}
                .fieldSearchInput::placeholder {{
                    color: {active_theme_dict['header_text']};
                    opacity: 0.6;
                }}
                .fieldOptionsContainer {{
                    max-height: 250px;
                    overflow-y: auto;
                    padding: 5px 0;
                    flex: 1;
                    min-height: 0;
                }}
                .fieldCheckboxLabel {{
                    display: flex;
                    align-items: center;
                    padding: 8px 10px;
                    cursor: pointer;
                    color: {active_theme_dict['header_text']};
                    white-space: nowrap;
                    user-select: none;
                }}
                .fieldCheckboxLabel:hover {{
                    background-color: {active_theme_dict['tab_hover']};
                }}
                .fieldCheckboxLabel input[type="checkbox"] {{
                    margin-right: 8px;
                    cursor: pointer;
                }}
                .fieldCheckboxLabel span {{
                    flex: 1;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}
        </style>
        """

        html_path = join(self.addonPath, "assets", "templates", "dictionary.html")
        js_path = join(self.addonPath, "assets", "scripts", "dictionary.js")

        # Read the JavaScript content to inline it
        with open(js_path, "r", encoding="utf-8") as js_file:
            js_content = js_file.read()

        # Get saved font sizes from config, default to [12, 22]
        font_sizes = self.config.get("fontSizes", [12, 22])
        fefs = font_sizes[0] if len(font_sizes) > 0 else 12
        dbfs = font_sizes[1] if len(font_sizes) > 1 else 22

        with open(html_path, "r", encoding="utf-8") as fh:
            html = fh.read()
            # Inject font size variables before the main script
            font_size_init = f"<script>var fefs = {fefs}, dbfs = {dbfs};</script>"
            # Replace the external script tag with inline JavaScript
            html = html.replace(
                '<script src="../scripts/dictionary.js"></script>',
                f"{font_size_init}<script>{js_content}</script>",
            )
            # Inject the custom theme CSS
            html = html.replace('<style id="customThemeCss"></style>', custom_theme_css)
            # Always inject welcome screen content if available
            if self.welcome and self.welcome.strip():
                escaped_welcome = json.dumps(self.welcome)
                html = html.replace(
                    '<div id="welcomeBackground"></div>',
                    f'<div id="welcomeBackground">{self.welcome}</div>',
                )

            if not willSearch:
                # Don't add a Welcome tab anymore, just show the background
                html = html.replace(
                    '<script id="initialValue"></script>',
                    '<script id="initialValue">updateWelcomeVisibility();</script>',
                )
            else:
                # If searching, we still need to clear the initialValue script tag
                html = html.replace(
                    '<script id="initialValue"></script>',
                    '<script id="initialValue">updateWelcomeVisibility();</script>',
                )
            url = QUrl.fromLocalFile(html_path)
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
        try:
            self.dictGroups.currentIndexChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        newDictGroupsCombo = self.setupDictGroups()
        if hasattr(self, "toolbar"):
            self.toolbar.replaceWidget(self.dictGroups, newDictGroupsCombo)
        self.dictGroups.close()
        self.dictGroups.deleteLater()
        self.dictGroups = newDictGroupsCombo

        # Update search type combo box (to reflect any language-specific search options if they were added)
        try:
            self.sType.currentIndexChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        newSType = self.setupSearchType()
        if hasattr(self, "toolbar"):
            self.toolbar.replaceWidget(self.sType, newSType)
        self.sType.close()
        self.sType.deleteLater()
        self.sType = newSType

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

    def resizeEvent(self, event):
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
            TabMode.singleTab = True
            icon = "onetab"
        else:
            TabMode.singleTab = False
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
            print(f"Error in toggleTabMode: {e}")
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
        # Get theme color for icons
        theme_color = self.load_theme_color("header_text")
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
        defaults = ["All", "Images"]
        if self.config.get("llm_enabled", False):
            defaults.append("LLM")
        if self.config.get("forvo_enabled", False):
            defaults.append("Forvo")
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

    def mousePressEvent(self, ev):
        self.clicked.emit()


class SVGPushButton(QPushButton):
    def __init__(self, width, height):
        super().__init__()
        self.setFixedSize(width, height)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(0)
        self.svgWidget = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setSvg(self, svgPath, color="#ffffff"):
        if self.svgWidget:
            self.layout.removeWidget(self.svgWidget)
            self.svgWidget.deleteLater()

        # Read SVG file and replace color placeholders with the theme color
        try:
            with open(svgPath, "r", encoding="utf-8") as f:
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
            self.layout.addWidget(self.svgWidget, 0, Qt.AlignmentFlag.AlignCenter)
        except Exception as e:
            print(f"Error loading SVG {svgPath}: {e}")
