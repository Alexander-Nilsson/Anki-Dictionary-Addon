from __future__ import annotations

import json
import os
from os.path import join
from typing import Any

from aqt.operations.note import update_note
from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QMimeData,
    QPixmap,
    QSize,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..exporters.card_exporter import CardExporter
from ..utils import media_manager
from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class CardCreationHandler:
    """Handles card creation/export and field operations."""

    def __init__(self, midict):
        self.midict = midict

    def addImgsToExportWindow(self, word: str, urls: list[str]) -> None:
        self.initCardExporterIfNeeded()
        img_separator = ""
        imgs: list[str] = []
        raw_paths: list[str] = []
        auto_convert = self.midict.config.get("imageAutoConvert", True)
        media_dir = self.midict.dictInt.mw.col.media.dir()
        for imgurl in urls:
            try:
                ext = (
                    media_manager.image_ext_from_url(imgurl)
                    if not auto_convert
                    else "avif"
                )
                prefix = "base64" if imgurl.startswith("data:") else ""
                filename = media_manager.unique_filename(prefix=prefix, ext=ext)
                fullpath = join(media_dir, filename)
                media_manager.download_image(
                    imgurl,
                    fullpath,
                    max_w=self.midict.maxW,
                    max_h=self.midict.maxH,
                    auto_convert=auto_convert,
                )
                raw_paths.append(fullpath)
                imgs.append(f'<img src="{filename}">')
            except Exception:
                continue
        if imgs:
            self.midict.addWindow.addImgs(
                word, img_separator.join(imgs), self.getThumbs(raw_paths)
            )

    def copyImagesToClipboard(self, urls_json: str) -> None:
        try:
            urls = json.loads(urls_json)
            if not urls:
                return

            mime_data = QMimeData()
            url_list: list[QUrl] = []
            first_image = None

            for idx, url in enumerate(urls):
                try:
                    image = media_manager.load_image_from_url(url)
                    if image is None:
                        continue
                    if first_image is None:
                        first_image = image
                    ext = media_manager.image_ext_from_url(url)
                    temp_path = join(self.midict.temp_dir, f"clipboard_img_{idx}.{ext}")
                    image.save(temp_path)
                    url_list.append(QUrl.fromLocalFile(temp_path))
                except Exception as e:
                    logger.error(f"Error processing image {idx} for clipboard: {e}")

            if url_list:
                mime_data.setUrls(url_list)
                if first_image:
                    mime_data.setImageData(first_image)
                self.midict.dictInt.mw.app.clipboard().setMimeData(mime_data)
                logger.debug(f"Copied {len(url_list)} images to clipboard.")
            else:
                logger.warning("No valid images found to copy to clipboard.")
        except Exception as e:
            logger.error(f"Error copying images to clipboard: {e}")

    def getThumbs(self, paths: list[str]) -> QWidget:
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

    def exportImage(self, pathAndName: tuple[str, str]) -> None:
        self.midict.dictInt.ensureVisible()
        path, name = pathAndName
        self.initCardExporterIfNeeded()
        self.midict.addWindow.scrollArea.show()
        self.midict.addWindow.exportImage(path, name)

    def initCardExporterIfNeeded(self) -> None:
        if not self.midict.addWindow:
            self.midict.addWindow = CardExporter(self.midict.dictInt, self.midict)

    def bulkTextExport(self, cards: list[Any]) -> None:
        self.initCardExporterIfNeeded()
        self.midict.addWindow.bulkTextExport(cards)

    def bulkMediaExport(self, card: Any) -> None:
        self.initCardExporterIfNeeded()
        self.midict.addWindow.bulkMediaExport(card)

    def cancelBulkMediaExport(self) -> None:
        if self.midict.addWindow:
            self.midict.addWindow.bulkMediaExportCancelledByBrowserRefresh()

    def exportAudio(self, audioList: tuple[str, str, str]) -> None:
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
    ) -> str | bool:
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
            urls_list: list[str] = []
            img_separator = ""
            urls_data = json.loads(urls)
            auto_convert = self.midict.config.get("imageAutoConvert", True)
            media_dir = self.midict.dictInt.mw.col.media.dir()

            for imgurl in urls_data:
                try:
                    if os.path.exists(imgurl):
                        filename = os.path.basename(imgurl)
                        media_manager.copy_to_media(imgurl, filename, media_dir)
                        urls_list.append(f'<img src="{filename}">')
                    else:
                        ext = (
                            media_manager.image_ext_from_url(imgurl)
                            if not auto_convert
                            else "avif"
                        )
                        prefix = "base64" if imgurl.startswith("data:") else ""
                        filename = media_manager.unique_filename(prefix=prefix, ext=ext)
                        media_manager.download_image(
                            imgurl,
                            join(media_dir, filename),
                            max_w=self.midict.maxW,
                            max_h=self.midict.maxH,
                            auto_convert=auto_convert,
                        )
                        urls_list.append(f'<img src="{filename}">')
                except Exception as e:
                    logger.error(f"Failed to process image: {imgurl}: {e}")
                    continue
            if urls_list:
                self.sendToField("Images", img_separator.join(urls_list))
        else:
            logger.warning("no reviewer or editor")
            tooltip(
                "No active reviewer or editor found. Please open a card to send images to a field."
            )

    def addAudioToExportWindow(self, word: str, url: str) -> None:
        self.initCardExporterIfNeeded()
        try:
            filename = media_manager.unique_filename(ext="mp3")
            fullpath = join(self.midict.temp_dir, filename)
            if media_manager.download_file(url, fullpath):
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
            filename = media_manager.unique_filename(ext="mp3")
            fullpath = join(self.midict.dictInt.mw.col.media.dir(), filename)
            if media_manager.download_file(url, fullpath):
                tag = f"[sound:{filename}]"
                self.sendToField("Forvo", tag)
        except Exception as e:
            logger.error(f"Error sending Forvo audio to field: {e}")
            tooltip(f"Failed to send audio to field: {e}")

    def playAudio(self, url: str) -> None:
        try:
            filename = "temp_forvo_play.mp3"
            fullpath = join(self.midict.temp_dir, filename)
            if media_manager.download_file(url, fullpath):
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
