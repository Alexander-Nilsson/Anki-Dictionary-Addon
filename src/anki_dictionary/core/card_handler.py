# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import base64
import re
import time
import os
import shutil
from os.path import join
from typing import List, Tuple, Any, Union
from urllib.request import Request, urlopen

from aqt.qt import QImage, QMimeData, QPixmap, QSize, QUrl, Qt, QLabel, QWidget
from aqt.qt import QHBoxLayout, QVBoxLayout
from aqt.utils import tooltip
from aqt.operations.note import update_note

from ..utils.logger import get_logger
from ..exporters.card_exporter import CardExporter

logger = get_logger(__name__.split(".")[-1])


class CardCreationHandler:
    """Handles card creation/export and field operations."""

    def __init__(self, midict):
        self.midict = midict

    @staticmethod
    def _img_ext_from_url(url: str) -> str:
        if url.startswith("data:"):
            return "avif"
        cleaned = re.sub(r"\?.*$", "", url)
        _, ext = os.path.splitext(cleaned.strip().split("/")[-1])
        ext = ext.lower().lstrip(".")
        return (
            ext
            if ext in {"jpg", "jpeg", "png", "gif", "webp", "avif", "bmp"}
            else "avif"
        )

    def addImgsToExportWindow(self, word: str, urls: List[str]) -> None:
        self.initCardExporterIfNeeded()
        imgSeparator = ""
        imgs: List[str] = []
        rawPaths: List[str] = []
        auto_convert = self.midict.config.get("imageAutoConvert", True)
        for imgurl in urls:
            try:
                ext = self._img_ext_from_url(imgurl) if not auto_convert else "avif"
                if imgurl.startswith("data:"):
                    filename = str(time.time())[:-4].replace(".", "") + "base64." + ext
                else:
                    url = re.sub(r"\?.*$", "", imgurl)
                    base_name = re.sub(r"\..*$", "", url.strip().split("/")[-1])
                    filename = (
                        str(time.time())[:-4].replace(".", "") + base_name + "." + ext
                    )
                fullpath = join(self.midict.dictInt.mw.col.media.dir(), filename)
                self.saveQImage(imgurl, fullpath)
                rawPaths.append(fullpath)
                imgs.append('<img src="' + filename + '">')
            except Exception:
                continue
        if len(imgs) > 0:
            self.midict.addWindow.addImgs(
                word, imgSeparator.join(imgs), self.getThumbs(rawPaths)
            )

    def saveQImage(self, url: str, filename: str) -> None:
        if url.startswith("data:"):
            try:
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

        auto_convert = self.midict.config.get("imageAutoConvert", True)

        if auto_convert:
            image = QImage()
            image.loadFromData(file)
            if not image.isNull():
                image = image.scaled(
                    QSize(self.midict.maxW, self.midict.maxH),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if filename.lower().endswith(".avif"):
                    image.save(filename, "AVIF")
                else:
                    image.save(filename)
        else:
            with open(filename, "wb") as f:
                f.write(file)

    def copyImagesToClipboard(self, urls_json: str) -> None:
        try:
            urls = json.loads(urls_json)
            if not urls:
                return

            from urllib.request import Request, urlopen

            mime_data = QMimeData()
            urls_list = []

            first_image = None

            for idx, url in enumerate(urls):
                try:
                    if url.startswith("data:"):
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

                        temp_path = join(
                            self.midict.temp_dir, f"clipboard_img_{idx}.{ext}"
                        )
                        image.save(temp_path)
                        urls_list.append(QUrl.fromLocalFile(temp_path))
                except Exception as e:
                    logger.error(f"Error processing image {idx} for clipboard: {e}")

            if urls_list:
                mime_data.setUrls(urls_list)
                if first_image:
                    mime_data.setImageData(first_image)

                self.midict.dictInt.mw.app.clipboard().setMimeData(mime_data)
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
        self.midict.addWindow.addDefinition(dictName, word, text)

    def exportImage(self, pathAndName: Tuple[str, str]) -> None:
        self.midict.dictInt.ensureVisible()
        path, name = pathAndName
        self.initCardExporterIfNeeded()
        self.midict.addWindow.scrollArea.show()
        self.midict.addWindow.exportImage(path, name)

    def initCardExporterIfNeeded(self) -> None:
        if not self.midict.addWindow:
            self.midict.addWindow = CardExporter(self.midict.dictInt, self.midict)

    def bulkTextExport(self, cards: List[Any]) -> None:
        self.initCardExporterIfNeeded()
        self.midict.addWindow.bulkTextExport(cards)

    def bulkMediaExport(self, card: Any) -> None:
        self.initCardExporterIfNeeded()
        self.midict.addWindow.bulkMediaExport(card)

    def cancelBulkMediaExport(self) -> None:
        if self.midict.addWindow:
            self.midict.addWindow.bulkMediaExportCancelledByBrowserRefresh()

    def exportAudio(self, audioList: Tuple[str, str, str]) -> None:
        self.midict.dictInt.ensureVisible()
        temp, tag, name = audioList
        self.initCardExporterIfNeeded()
        self.midict.addWindow.scrollArea.show()
        self.midict.addWindow.exportAudio(temp, tag, name)

    def exportSentence(self, sentence: str, secondary: str = "") -> None:
        self.midict.dictInt.ensureVisible()
        self.initCardExporterIfNeeded()
        self.midict.addWindow.scrollArea.show()
        self.midict.addWindow.exportSentence(sentence)
        self.midict.addWindow.exportSecondary(secondary)

    def exportWord(self, word: str) -> None:
        self.midict.dictInt.ensureVisible()
        self.initCardExporterIfNeeded()
        self.midict.addWindow.scrollArea.show()
        self.midict.addWindow.exportWord(word)

    def attemptAutoAdd(self, bulkExport: Any) -> None:
        self.midict.addWindow.attemptAutoAdd(bulkExport)

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
        if (self.midict.reviewer and self.midict.reviewer.card) or (
            self.midict.currentEditor and self.midict.currentEditor.note
        ):
            urlsList: List[str] = []
            imgSeparator = ""
            urls_list = json.loads(urls)
            auto_convert = self.midict.config.get("imageAutoConvert", True)

            for imgurl in urls_list:
                try:
                    if os.path.exists(imgurl):
                        filename = os.path.basename(imgurl)
                        dest_path = join(
                            self.midict.dictInt.mw.col.media.dir(), filename
                        )

                        if imgurl != dest_path:
                            shutil.copy2(imgurl, dest_path)

                        urlsList.append(f'<img src="{filename}">')

                    else:
                        ext = (
                            self._img_ext_from_url(imgurl)
                            if not auto_convert
                            else "avif"
                        )
                        if imgurl.startswith("data:"):
                            filename = (
                                str(time.time())[:-4].replace(".", "") + "base64." + ext
                            )
                        else:
                            url = re.sub(r"\?.*$", "", imgurl)
                            base_name = re.sub(r"\..*$", "", url.strip().split("/")[-1])
                            filename = (
                                str(time.time())[:-4].replace(".", "")
                                + base_name
                                + "."
                                + ext
                            )

                        self.saveQImage(
                            imgurl,
                            join(self.midict.dictInt.mw.col.media.dir(), filename),
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
        self.initCardExporterIfNeeded()
        try:
            filename = str(time.time()).replace(".", "") + ".mp3"
            fullpath = join(self.midict.temp_dir, filename)

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
            self.midict.addWindow.exportWord(word)
        except Exception as e:
            logger.error(f"Error downloading Forvo audio: {e}")
            tooltip(f"Failed to download audio: {e}")

    def sendAudioToField(self, url: str) -> None:
        if not (self.midict.reviewer and self.midict.reviewer.card) and not (
            self.midict.currentEditor and self.midict.currentEditor.note
        ):
            tooltip("No active reviewer or editor found.")
            return

        try:
            filename = str(time.time()).replace(".", "") + ".mp3"
            fullpath = join(self.midict.dictInt.mw.col.media.dir(), filename)

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
        try:
            filename = "temp_forvo_play.mp3"
            fullpath = join(self.midict.temp_dir, filename)

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
        clean_name = self.midict.db.cleanDictName(name)
        display_name = clean_name.replace("_", " ")
        if not (self.midict.reviewer and self.midict.reviewer.card) and not (
            self.midict.currentEditor and self.midict.currentEditor.note
        ):
            tooltip(
                "No active reviewer or editor found. Please open a card to send definitions to a field."
            )
            return

        if clean_name == "Images":
            tFields = self.midict.config.get("ImageFields", [])
            addType = self.midict.config.get("ImageAddType", "add")
        elif clean_name == "LLM":
            tFields = self.midict.config.get("LLMFields", [])
            addType = self.midict.config.get("LLMAddType", "add")
        elif clean_name == "Forvo":
            tFields = self.midict.config.get("ForvoFields", [])
            addType = self.midict.config.get("ForvoAddType", "add")
        else:
            res = self.midict.db.getAddTypeAndFields(clean_name)
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
        if self.midict.reviewer and self.midict.reviewer.card:
            note = self.midict.reviewer.card.note()
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

            update_note(parent=self.midict.dictInt.mw, note=note).run_in_background()
            if self.midict.reviewer.state == "answer":
                self.midict.reviewer._showAnswer()
            elif self.midict.reviewer.state == "question":
                self.midict.reviewer._showQuestion()
            if hasattr(self.midict.dictInt.mw, "DictReloadEditorAndBrowser"):
                self.midict.dictInt.mw.DictReloadEditorAndBrowser(note)

        if self.midict.currentEditor and self.midict.currentEditor.note:
            note = self.midict.currentEditor.note
            items = note.items()
            currentNoteId = note.id
            for idx, item in enumerate(items):
                noteField = item[0]
                if noteField in tFields:
                    found_field = True
                    self.midict.currentEditor.web.eval(
                        self.midict.dictInt.insertHTMLJS
                        % (
                            definition.replace('"', '\\"'),
                            str(idx),
                            addType,
                            currentNoteId,
                        )
                    )
            if not found_field:
                tooltip(
                    f"None of the selected fields for '{display_name}' were found in the current card."
                )
                return
