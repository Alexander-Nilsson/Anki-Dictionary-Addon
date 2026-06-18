# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import base64
import re
import time
import os
from os.path import join, exists, dirname
from typing import List, Dict, Optional, Tuple, Any, Union
from urllib.request import Request, urlopen


from ..utils.logger import get_logger
from ..web.icons import get_base64_icon
from ..integrations import image_search as duckduckgoimages
from ..integrations import llm as llm_integration
from ..integrations.llm import split_llm_definitions
from ..integrations import forvo as forvo_integration

logger = get_logger(__name__.split(".")[-1])


class SearchPipeline:
    """Handles dictionary search logic, result preparation, and HTML rendering."""

    def __init__(self, midict):
        self.midict = midict

    def loadImageResults(self, results):
        html, idName = results
        escaped_html = json.dumps(html)
        escaped_idName = json.dumps(idName)
        self.midict.eval("loadImageHtml(%s, %s);" % (escaped_html, escaped_idName))

    def downloadImage(self, url):
        from aqt.qt import QImage, QSize, Qt

        try:
            filename = str(time.time()).replace(".", "") + ".avif"
            if url.startswith("data:"):
                header, encoded = url.split(",", 1)
                file = base64.b64decode(encoded)
            else:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                file = urlopen(req, timeout=30).read()

            image = QImage()
            image.loadFromData(file)
            if not image.isNull():
                image = image.scaled(
                    QSize(self.midict.maxW, self.midict.maxH),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image.save(filename, "AVIF")
                return '<img src="' + filename + '">'
        except Exception:
            return ""

    def getBase64Icon(self, icon_name):
        if self.midict.dictInt.theme_manager.is_dark:
            if icon_name == "anki.svg":
                icon_name = "nightanki.svg"
            elif "." in icon_name:
                name, ext = icon_name.rsplit(".", 1)
                if not name.endswith("night"):
                    night_name = f"{name}night.{ext}"
                    if exists(join(self.midict.dictInt.iconpath, night_name)):
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
                    headerString += (
                        '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b '
                    )
                    sbHeaderString += (
                        '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b '
                    )
                elif header == "altterm":
                    headerString += (
                        '\u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y '
                    )
                    sbHeaderString += (
                        '\u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y '
                    )
                elif header == "pronunciation":
                    headerString += '<span class="pronunciation">\u25f3p</span>'
                    sbHeaderString += '<span class="listPronunciation">\u25f3p</span>'
            formattedHeaders[dictname] = [headerString, sbHeaderString]
        return formattedHeaders

    def loadConjugations(self):
        langs = self.midict.db.getCurrentDbLangs()
        conjugations = {}
        for lang in langs:
            filePath = join(
                self.midict.homeDir, "user_files", "db", "conjugation", "%s.json" % lang
            )
            if not os.path.exists(filePath):
                filePath = join(
                    self.midict.homeDir,
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
            term.replace("%", "")
            .replace("_", "")
            .replace("\u300c", "")
            .replace("\u300d", "")
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
        self.midict.eval(f"addCustomFont({js_font}, {js_name});")

    def getTabMode(self):
        if self.midict.dictInt.tabB.singleTab:
            return "true"
        return "false"

    def getHTMLResult(self, term, selectedGroup, idName=""):
        singleTab = self.getTabMode()
        cleaned = self.cleanTerm(term)
        font = self.getFontFamily(selectedGroup)
        dictDefs = self.midict.config["dictSearch"]
        maxDefs = self.midict.config["maxSearch"]

        results = self.midict.db.searchTerm(
            term,
            selectedGroup,
            self.midict.conjugations,
            self.midict.sType.currentText(),
            self.midict.deinflect,
            str(dictDefs),
            maxDefs,
        )

        group_dicts = [d["dict"] for d in selectedGroup["dictionaries"]]

        if self.midict.config.get("llm_enabled", False) and "LLM" in group_dicts:
            star_count = ""
            level_labels = ""
            for d_name, d_results in results.items():
                if not isinstance(d_results, list):
                    continue
                for entry in d_results:
                    s = entry.get("starCount", "")
                    if s:
                        if s.startswith("\u2605"):
                            if not star_count.startswith("\u2605") or len(s) > len(
                                star_count
                            ):
                                star_count = s
                        elif not star_count:
                            star_count = s

                    ll = entry.get("levelLabels", "")
                    if ll and len(ll) > len(level_labels):
                        level_labels = ll

            if not star_count and not level_labels:
                for d in selectedGroup["dictionaries"]:
                    lang = d.get("lang")
                    if lang:
                        freq_info = self.midict.db.get_term_frequency_info(
                            cleaned, lang, self.midict.config
                        )
                        if freq_info.get("starCount"):
                            star_count = freq_info["starCount"]
                        if freq_info.get("levelLabels"):
                            level_labels = freq_info["levelLabels"]
                        if star_count or level_labels:
                            break

            self.triggerLLMSearch(cleaned, star_count, level_labels, idName)

        forvoId = ""
        if self.midict.config.get("forvo_enabled", False) and "Forvo" in group_dicts:
            forvo_lang = self.midict.config.get("forvo_language", "ja")
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
            and selectedGroup["font"] not in self.midict.customFontsLoaded
        ):
            self.midict.customFontsLoaded.append(selectedGroup["font"])
            self.injectFont(selectedGroup["font"])

        idName = f"llm-loader-{int(time.time() * 1000)}"

        html, cleaned, singleTab = self.getHTMLResult(term, selectedGroup, idName)

        js_html = json.dumps(html.replace("\r", "").replace("\n", ""))
        js_cleaned = json.dumps(cleaned)
        js_singleTab = "true" if singleTab == "true" else "false"
        js_idName = json.dumps(idName)

        self.midict.eval(
            f"addNewTab({js_html}, {js_cleaned}, {js_singleTab}, {js_idName});"
        )

    def addResultWrappers(self, results):
        for idx, result in enumerate(results):
            if "dictionaryTitleBlock" not in result:
                results[idx] = '<div class="definitionBlock">' + result + "</div>"
        return results

    def escapePunctuation(self, term):
        return re.sub(r"([.*+(\[\]{}\\?)!])", "\\\1", term)

    def highlightTarget(self, text, term):
        if self.midict.config["highlightTarget"]:
            if not isinstance(text, str):
                text = str(text) if text is not None else ""
            try:
                parts = re.split(r"(<[^>]*>)", text)

                for i in range(0, len(parts), 2):
                    if parts[i]:
                        if any(
                            "\u4e00" <= c <= "\u9fff"
                            or "\u3040" <= c <= "\u309f"
                            or "\u30a0" <= c <= "\u30ff"
                            for c in term
                        ):
                            pattern = "(" + self.escapePunctuation(term) + ")"
                        else:
                            pattern = r"\b(" + self.escapePunctuation(term) + r")\b"

                        parts[i] = re.sub(
                            pattern, r'<span class="targetTerm">\1</span>', parts[i]
                        )

                return "".join(parts)
            except Exception as e:
                logger.error(f"Error during highlightTarget: {e}")
                return text
        return text

    def processDefinitionHTML(self, text):
        if not isinstance(text, str):
            text = str(text) if text is not None else ""

        text = text.strip()
        text = text.replace("\n", "<br>")

        text = re.sub(r"<br\s*/?>", "<br>", text, flags=re.IGNORECASE)

        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

        text = re.sub(r"(<br>\s*){2,}", "<br><br>", text)

        text = re.sub(r"^(<br>\s*)+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(<br>\s*)+$", "", text, flags=re.IGNORECASE)

        text = re.sub(r"^\[\?\]\s*", "", text)

        return text.strip()

    def getSideBar(self, results, term, font, frontBracket, backBracket):
        html = "<div" + font + 'class="definitionSideBar"><div class="innerSideBar">'
        dictCount = 0
        entryCount = 0
        for dictName, dictResults in results.items():
            display_name = self.midict.db.cleanDictName(dictName).replace("_", " ")
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
        if not self.midict.config.get("tooltips", True):
            return "", "", ""

        imgTooltip = ' title="Add this definition, or any selected text to the card exporter (opens the card exporter if it is not yet opened)." '
        clipTooltip = (
            ' title="Copy this definition, or any selected text to the clipboard." '
        )
        sendTooltip = ' title="Send this definition, or any selected text to this dictionary\'s target fields. It will send it to the current target window" '

        return imgTooltip, clipTooltip, sendTooltip

    def getStarTooltip(self, starCount: str) -> str:
        if not starCount or not isinstance(starCount, str):
            return ""

        ranks = {
            "\u2605\u2605\u2605\u2605\u2605": "Top 1,500",
            "\u2605\u2605\u2605\u2605": "Top 5,000",
            "\u2605\u2605\u2605": "Top 15,000",
            "\u2605\u2605": "Top 30,000",
            "\u2605": "Top 60,000",
        }

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

        clean_name = self.midict.db.cleanDictName(dictName)

        if (
            not self.midict.termHeaders
            or dictName in ["Images", "LLM", "Forvo"]
            or clean_name in ["Images", "LLM", "Forvo"]
        ):
            if sb:
                header = '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b \u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y <span class="listPronunciation">\u25f3p</span>'
            else:
                header = '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b \u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y <span class="pronunciation">\u25f3p</span>'
        else:
            lookup_name = (
                dictName if dictName in self.midict.termHeaders else clean_name
            )
            if lookup_name in self.midict.termHeaders:
                if sb:
                    header = self.midict.termHeaders[lookup_name][1]
                else:
                    header = self.midict.termHeaders[lookup_name][0]
            else:
                if sb:
                    header = '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b \u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y <span class="listPronunciation">\u25f3p</span>'
                else:
                    header = '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b \u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y <span class="pronunciation">\u25f3p</span>'

        return (
            header.replace("\u25f3t", self.highlightTarget(term, target))
            .replace("\u25f3a", self.highlightTarget(altterm, target))
            .replace("\u25f3p", self.highlightTarget(pronunciation, target))
            .replace("\u25f3f", frontBracket)
            .replace("\u25f3b", backBracket)
            .replace("\u25f3x", altFB)
            .replace("\u25f3y", altBB)
        )

    def prepareResults(self, results, term, font, idName="", forvoId=""):
        frontBracket = self.midict.config["frontBracket"]
        backBracket = self.midict.config["backBracket"]

        group_dicts = [
            d["dict"]
            for d in self.midict.dictInt.getSelectedDictGroup()["dictionaries"]
        ]
        has_special = any(d in ["Images", "LLM", "Forvo"] for d in group_dicts)

        if len(results) > 0 or has_special:
            html = self.getSideBar(results, term, font, frontBracket, backBracket)
            html += '<div class="mainDictDisplay">'
            dictCount = 0
            entryCount = 0
            imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

            group = self.midict.dictInt.getSelectedDictGroup()
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
                    if self.midict.config.get("llm_enabled", False):
                        overwrite = self.getOverwriteChecks(dictCount, dictName)
                        select = self.getFieldChecks(dictName)
                        loaderId = idName if idName else "llm-loader"
                        html += (
                            f'<div id="{loaderId}">'
                            '<div data-index="'
                            + str(dictCount)
                            + '" class="dictionaryTitleBlock"><div '
                            + font
                            + ' class="dictionaryTitle">LLM</div><div class="dictionarySettings">'
                            + overwrite
                            + select
                            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div><div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div></div></div></div>'
                            '<div class="definitionBlock llm-loading-placeholder"><i>Loading LLM definition...</i></div>'
                            "</div>"
                        )
                    dictCount += 1
                    entryCount += 1
                    continue
                if dictName == "Forvo":
                    if self.midict.config.get("forvo_enabled", False):
                        overwrite = self.getOverwriteChecks(dictCount, dictName)
                        select = self.getFieldChecks(dictName)
                        loaderId = forvoId if forvoId else "forvo-loader"
                        html += (
                            f'<div id="{loaderId}">'
                            '<div data-index="'
                            + str(dictCount)
                            + '" class="dictionaryTitleBlock"><div '
                            + font
                            + ' class="dictionaryTitle">Forvo</div><div class="dictionarySettings">'
                            + overwrite
                            + select
                            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div><div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div></div></div></div>'
                            '<div class="definitionBlock"><i>Loading Forvo pronunciations...</i></div>'
                            "</div>"
                        )
                    dictCount += 1
                    entryCount += 1
                    continue

                cleanName = self.midict.db.cleanDictName(dictName)
                normalizedName = self.midict.db.normalize_dict_name(dictName)

                dictResults = None
                if dictName in results:
                    dictResults = results[dictName]
                elif cleanName in results:
                    dictResults = results[cleanName]
                elif normalizedName in results:
                    dictResults = results[normalizedName]

                if dictResults is not None:
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
                        + overwrite
                        + select
                        + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div><div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div></div></div></div>'
                    )
                    dictCount += 1

                    for idx, entry in enumerate(dictResults):
                        extracted_freq = ""
                        definition = entry["definition"].strip()

                        while True:
                            definition = re.sub(
                                r"^(<br>\s*)+|(<br>\s*)+$",
                                "",
                                definition,
                                flags=re.IGNORECASE,
                            ).strip()

                            freq_match = re.search(
                                r"^\u3010[^\u3011]+\u3011\s*\[([\dk+]+)\]\s*",
                                definition,
                            )
                            if freq_match:
                                if not extracted_freq:
                                    extracted_freq = freq_match.group(1)
                                definition = definition[freq_match.end() :].strip()
                                continue

                            head_match = re.search(
                                r"^\u3010[^\u3011]+\u3011\s*", definition
                            )
                            if head_match:
                                definition = definition[head_match.end() :].strip()
                                continue

                            break

                        term_escaped = re.escape(entry["term"])
                        repeat_pattern = (
                            r"^\s*[\(\uff08\[[\uff3b][^\uff09\)]*?"
                            + term_escaped
                            + r"[^\uff09\)]*?[\)\uff09\]\uff3b]\s*"
                        )
                        definition = re.sub(repeat_pattern, "", definition)

                        definition = re.sub(
                            r"^(<br>\s*)+|(<br>\s*)+$",
                            "",
                            definition,
                            flags=re.IGNORECASE,
                        ).strip()

                        if not extracted_freq and entry.get("frequency"):
                            extracted_freq = str(entry["frequency"])

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
                                f' <span class="starcount level-label">{entry["levelLabels"]}</span>'
                                if entry.get("levelLabels")
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
                            + ' class="clipper">\u2702</div><div '
                            + sendTooltip
                            + " onclick=\"sendToField(event, '"
                            + cleanName
                            + '\')" class="sendToField">\u279e</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">\u25b2</div><div onclick="navigateDef(event, true)" class="nextDef">\u25bc</div></div></div></div><div'
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
        idName = "gcon" + str(time.time()).replace(".", "")
        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()
        preparedTerm = self.getPreparedTermHeader(
            dictName, bracketFront, bracketBack, term, term, "", ""
        )
        html = (
            '<div data-index="'
            + str(dictCount)
            + '" class="dictionaryTitleBlock"><div class="dictionaryTitle">Images</div><div class="dictionarySettings">'
            + overwrite
            + select
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div><div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div></div></div></div>'
            + '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + preparedTerm
            + '</span><div class="defTools"><div onclick="ankiExport(event, \''
            + dictName
            + '\')" class="ankiExportButton"><img '
            + imgTooltip
            + ' src="'
            + self.getBase64Icon("anki.svg")
            + '"></div><div onclick="clipText(event)" '
            + clipTooltip
            + ' class="clipper">\u2702</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">\u279e</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">\u25b2</div><div onclick="navigateDef(event, true)" class="nextDef">\u25bc</div></div></div></div>'
            + '<div class="definitionBlock"><div class="imageBlock" id="'
            + idName
            + '">'
            + self.getImages(term, idName)
            + "</div></div>"
        )
        return html

    def getImages(self, term, idName):
        if not hasattr(self.midict, "image_offsets"):
            self.midict.image_offsets = {}

        if term not in self.midict.image_offsets:
            self.midict.image_offsets[term] = 0

        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(term, idName)
        imager.search_offset = self.midict.image_offsets[term]
        imager.auto_convert = self.midict.config.get("imageAutoConvert", True)
        imager.setSearchRegion(
            self.midict.config.get("imageSearchRegion", "United States")
        )
        imager.signals.resultsFound.connect(self.loadImageResults)
        imager.signals.noResults.connect(self.showNoImagesMessage)
        self.midict.threadpool.start(imager)

        return "Loading..."

    def showNoImagesMessage(self):
        from aqt.utils import tooltip

        tooltip("No images found")

    def triggerLLMSearch(self, term, star_count="", level_labels="", idName=""):
        worker = llm_integration.LLMWorker(
            term, self.midict.config, star_count, level_labels, idName
        )
        worker.signals.result_ready.connect(self.loadLLMResults)
        worker.signals.error_occurred.connect(self.showLLMError)
        self.midict.threadpool.start(worker)

    def _process_llm_definition(self, definition: str, term: str) -> str:
        """Apply formatting and cleanup to a single LLM definition string."""
        definition = re.sub(r"(\*\*|__|\u2605\u2605)(.*?)\1", r"<b>\2</b>", definition)
        definition = re.sub(r"(\*|_)(.*?)\1", r"<i>\2</i>", definition)
        definition = definition.replace("\u2605", "<b>\u2605</b>")
        definition = re.sub(r"^\s*[-*+]\s+", "\u2022 ", definition, flags=re.MULTILINE)

        term_lower = term.lower()
        lines = definition.split("\n")
        if len(lines) > 1:
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
            if first_line == term_lower:
                definition = "\n".join(lines[1:]).strip()
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
                if last_line == term_lower:
                    definition = "\n".join(lines[:-1]).strip()

        term_escaped = re.escape(term)
        repeat_pattern = (
            r"^\s*[\(\uff08\[[\uff3b][^\uff09\)]*?"
            + term_escaped
            + r"[^\uff09\)]*?[\)\uff09\]\uff3b]\s*"
        )
        definition = re.sub(repeat_pattern, "", definition).strip()
        return definition

    def _render_llm_entry(
        self,
        result: Dict[str, Any],
        font: str,
        imgTooltip: str,
        clipTooltip: str,
        sendTooltip: str,
        dictName: str,
        frontBracket: str,
        backBracket: str,
    ) -> str:
        """Render a single LLM entry (term header + definition block) as HTML."""
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
                f' <span class="starcount level-label">{result["levelLabels"]}</span>'
                if result.get("levelLabels")
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
            + ' class="clipper">\u2702</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">\u279e</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">\u25b2</div><div onclick="navigateDef(event, true)" class="nextDef">\u25bc</div></div></div></div>'
        )
        return html

    def _render_llm_definition_block(
        self, definition: str, font: str, term: str
    ) -> str:
        """Render a processed definition block as HTML."""
        return (
            "<div"
            + font
            + ' class="definitionBlock">'
            + self.highlightTarget(
                self.processDefinitionHTML(definition),
                term,
            )
            + "</div>"
        )

    def loadLLMResults(self, result):
        dictName = result.get("dictName", "LLM")
        idName = result.get("idName") or "llm-loader"
        selected_group = self.midict.dictInt.getSelectedDictGroup()
        font = self.getFontFamily(selected_group)

        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

        frontBracket = self.midict.config["frontBracket"]
        backBracket = self.midict.config["backBracket"]

        # Split the raw response into individual definitions
        definitions = split_llm_definitions(result["definition"])
        if not definitions:
            definitions = [result["definition"]]

        html_entries = ""
        for def_text in definitions:
            processed = self._process_llm_definition(def_text, result["term"])
            html_entries += self._render_llm_entry(
                result,
                font,
                imgTooltip,
                clipTooltip,
                sendTooltip,
                dictName,
                frontBracket,
                backBracket,
            )
            html_entries += self._render_llm_definition_block(
                processed,
                font,
                result["term"],
            )

        escaped_html = json.dumps(html_entries)
        self.midict.eval(
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

    def formatSingleEntry(
        self,
        result: Dict[str, Any],
        dictName: str,
        font: str,
        frontBracket: str,
        backBracket: str,
    ) -> str:
        dictCount = 999
        overwrite = self.getOverwriteChecks(dictCount, dictName)
        select = self.getFieldChecks(dictName)

        html = (
            '<div class="dictionaryTitleBlock"><div '
            + font
            + ' class="dictionaryTitle">'
            + dictName
            + '</div><div class="dictionarySettings">'
            + overwrite
            + select
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div><div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div></div></div></div>'
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
                f' <span class="starcount level-label">{result["levelLabels"]}</span>'
                if result.get("levelLabels")
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
            + ' class="clipper">\u2702</div><div '
            + sendTooltip
            + " onclick=\"sendToField(event, '"
            + dictName
            + '\')" class="sendToField">\u279e</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">\u25b2</div><div onclick="navigateDef(event, true)" class="nextDef">\u25bc</div></div></div></div>'
        )

        definition = self._process_llm_definition(result["definition"], result["term"])

        html += self._render_llm_definition_block(definition, font, result["term"])
        return html

    def showLLMError(self, result):
        error_msg = result.get("error", "Unknown LLM error")
        idName = result.get("idName") or "llm-loader"

        escaped_msg = json.dumps(
            f'<div class="definitionBlock llm-error" style="color: #ff5555; border: 1px solid #ff5555; padding: 15px; border-radius: 8px; background-color: rgba(255, 85, 85, 0.05);">'
            f'<div style="font-weight: bold; margin-bottom: 8px; font-size: 1.1em;">LLM Connection Error</div>'
            f'<div style="margin-bottom: 12px; font-family: monospace; font-size: 0.9em; opacity: 0.9; word-break: break-all;">{error_msg}</div>'
            f'<div style="font-size: 0.85em; opacity: 0.8;">'
            f"Possible causes:<ul>"
            f"<li>Local LLM (like Ollama) is not running</li>"
            f"<li>Wrong API key or Base URL</li>"
            f"<li>Network timeout (current timeout: {self.midict.config.get('llm_timeout', 15)}s)</li>"
            f"</ul></div></div>"
        )
        self.midict.eval(
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
        if not language:
            language = self.midict.config.get("forvo_language", "ja")
        worker = forvo_integration.ForvoWorker(
            term, language, self.midict.config, idName
        )
        worker.signals.result_ready.connect(self.onForvoResult)
        worker.signals.error_occurred.connect(self.onForvoError)
        self.midict.threadpool.start(worker)

    def onForvoResult(self, result):
        idName = result.get("idName") or "forvo-loader"
        term = result.get("term", "")
        items = result.get("items", [])

        if not items:
            group = self.midict.dictInt.getSelectedDictGroup()
            if len(group.get("dictionaries", [])) > 1:
                self._remove_forvo_element(idName)
                return
            else:
                self._remove_forvo_element(idName)
                return

        selected_group = self.midict.dictInt.getSelectedDictGroup()
        font = self.getFontFamily(selected_group)
        imgTooltip, clipTooltip, sendTooltip = self.getTooltips()

        forvo_limit = self.midict.config.get("forvo_limit", 3)
        content_html = f'<div {font} class="definitionBlock"><div class="forvo-container" style="padding: var(--spacing-sm) 0;">'

        for idx, item in enumerate(items):
            user = item.get("user", "Unknown")
            votes = item.get("votes", 0)
            origin = item.get("origin", "")
            audio_url = item.get("audio_url", "")

            item_style = "display: flex; align-items: center; margin-bottom: var(--spacing-sm); padding: var(--spacing-sm); border-bottom: 1px solid var(--border);"
            extra_class = ""
            if idx >= forvo_limit:
                item_style += " display: none;"
                extra_class = "forvo-extra"

            content_html += (
                f'<div class="forvo-item {extra_class}" style="{item_style}">'
                f'<div onclick="animateForvoPlay(this); playAudio(\'{audio_url}\')" style="cursor:pointer; font-size: 20px; margin-right: var(--spacing-md); color: var(--primary); width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary-light, rgba(33, 150, 243, 0.1)); transition: transform var(--transition-fast);" title="Play Pronunciation" onmouseover="this.style.transform=\'scale(1.1)\'" onmouseout="this.style.transform=\'scale(1)\'">'
                f'<span class="forvo-icon">\u25b6</span>'
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
                f'<div onclick="sendAudioToField(\'{audio_url}\')" {sendTooltip} class="sendToField" title="Send Audio to Field" style="font-size: 16px;">\u279e</div>'
                f"</div>"
                f"</div>"
            )

        if len(items) > forvo_limit:
            content_html += (
                f'<div onclick="showMoreForvo(this)" class="forvo-load-more" style="text-align: center; padding: var(--spacing-sm); cursor: pointer; color: var(--primary); font-weight: bold; margin-top: var(--spacing-sm); border: 1px dashed var(--primary); border-radius: var(--border-radius-sm);">'
                f"Load more ({len(items) - forvo_limit})"
                f"</div>"
            )

        content_html += "</div></div>"

        escaped_html = json.dumps(content_html)

        self.midict.eval(
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

    def _remove_forvo_element(self, idName: str) -> None:
        self.midict.eval(
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

    def onForvoError(self, result):
        error_msg = result.get("error", "Unknown Forvo error")
        logger.warning(f"Forvo unavailable: {error_msg}")
        idName = result.get("idName") or "forvo-loader"

        escaped_msg = json.dumps(
            f'<div class="definitionBlock forvo-error" style="color: var(--danger, #ff5555); border: 1px solid var(--danger, #ff5555); padding: 12px; border-radius: 8px; background-color: rgba(255, 85, 85, 0.05); margin: var(--spacing-sm);">'
            f'<div style="font-weight: bold; margin-bottom: 6px;">Forvo Unavailable</div>'
            f'<div style="font-size: 0.85em; opacity: 0.9; word-break: break-all;">{error_msg}</div>'
            f"</div>"
        )
        self.midict.eval(
            f"var loader = document.getElementById('{idName}'); "
            f"if(loader) {{ "
            f"  var oldContent = loader.querySelector('.definitionBlock'); "
            f"  if(oldContent) oldContent.remove(); "
            f"  var titleBlock = loader.querySelector('.dictionaryTitleBlock'); "
            f"  if(titleBlock) {{ "
            f"    titleBlock.insertAdjacentHTML('afterend', {escaped_msg}); "
            f"  }} else {{ "
            f"    loader.insertAdjacentHTML('beforeend', {escaped_msg}); "
            f"  }} "
            f"}}"
        )

    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        return [x.replace("\\", "\\\\") for x in urls]

    def loadMoreImages(self, search_term: str) -> None:
        if not hasattr(self.midict, "image_offsets"):
            self.midict.image_offsets = {}

        if search_term in self.midict.image_offsets:
            self.midict.image_offsets[search_term] += 15
        else:
            self.midict.image_offsets[search_term] = 15

        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(search_term, "load_more")
        imager.search_offset = self.midict.image_offsets[search_term]
        imager.auto_convert = self.midict.config.get("imageAutoConvert", True)
        imager.setSearchRegion(
            self.midict.config.get("imageSearchRegion", "United States")
        )
        imager.signals.resultsFound.connect(self.loadMoreImageResults)
        imager.signals.noResults.connect(self.showNoMoreImagesMessage)
        self.midict.threadpool.start(imager)

    def loadMoreImageResults(self, results: Tuple[str, str]) -> None:
        html, idName = results

        if not html or html.strip() == "":
            self.showNoMoreImagesMessage()
            return

        escaped_html = json.dumps(html)

        try:
            js_code = f"appendNewImages({escaped_html});"
            self.midict.eval(js_code)
        except Exception as e:
            logger.error(f"Error in loadMoreImageResults: {e}")
            self.showNoMoreImagesMessage()

    def showNoMoreImagesMessage(self) -> None:
        self.midict.eval(
            "var btn = document.querySelector('.imageLoader'); if(btn) { btn.textContent = 'No more images'; btn.disabled = true; }"
        )

    def getOverwriteChecks(self, dictCount: int, dictName: str) -> str:
        clean_name = self.midict.db.cleanDictName(dictName)
        if dictName == "Images" or clean_name == "Images":
            addType = self.midict.config.get("ImageAddType", "add")
        elif dictName == "LLM" or clean_name == "LLM":
            addType = self.midict.config.get("LLMAddType", "add")
        elif dictName == "Forvo" or clean_name == "Forvo":
            addType = self.midict.config.get("ForvoAddType", "add")
        else:
            addType = (
                self.midict.db.getAddType(dictName)
                or self.midict.db.getAddType(clean_name)
                or "add"
            )

        tooltip = ""
        if self.midict.config["tooltips"]:
            tooltip = " title=\"This determines the conditions for sending a definition (or a Google Image) to a field. Overwrite the target field's content. Add to the target field's current contents. Only add definitions to the target field if it is empty.\""

        typeName = "&nbsp;Add"
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
        count = str(self.midict.radioCount)
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
        if not hasattr(self.midict, "radioCount"):
            self.midict.radioCount = 0
        self.midict.radioCount += 1
        return checks

    def getFieldChecks(self, dictName):
        clean_name = self.midict.db.cleanDictName(dictName)
        logger.debug(f"getFieldChecks: dictName={dictName}, clean_name={clean_name}")
        if dictName == "Images" or clean_name == "Images":
            selF = self.midict.config.get("ImageFields", [])
        elif dictName == "LLM" or clean_name == "LLM":
            selF = self.midict.config.get("LLMFields", [])
        elif dictName == "Forvo" or clean_name == "Forvo":
            selF = self.midict.config.get("ForvoFields", [])
        else:
            selF = (
                self.midict.db.getFieldsSetting(dictName)
                or self.midict.db.getFieldsSetting(clean_name)
                or []
            )

        tooltip = ""
        if self.midict.config["tooltips"]:
            tooltip = ' title="Select this dictionary\'s target fields for when sending a definition(or a Google Image) to a card. If a field does not exist in the target card, then it is ignored, otherwise the definition is added to all fields that exist within the target card."'
        title = "&nbsp;Select Fields \u25be"
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
        mw = self.midict.dictInt.mw
        models = mw.col.models.all()
        fields = []
        for model in models:
            for fld in model["flds"]:
                if fld["name"] not in fields:
                    fields.append(fld["name"])
        fields.sort()
        return fields

    def resetConfiguration(self, config):
        self.midict.config = config
        self.midict.maxW = config.get("maxWidth", 1500)
        self.midict.maxH = config.get("maxHeight", 400)
        self.midict.termHeaders = self.formatTermHeaders(
            self.midict.db.getTermHeaders() or {}
        )
