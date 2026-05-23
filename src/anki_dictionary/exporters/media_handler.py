# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from os.path import join, exists
from shutil import copyfile

from aqt.qt import QPixmap, QPushButton, QTableWidgetItem, Qt

from ..utils.common import miInfo
from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class MediaHandler:
    def __init__(self, exporter):
        self.exporter = exporter

    def moveImageToMediaFolder(self):
        if self.exporter.imgPath and self.exporter.imgName:
            if exists(self.exporter.imgPath):
                path = join(self.exporter.mw.col.media.dir(), self.exporter.imgName)
                if not exists(path):
                    copyfile(self.exporter.imgPath, path)

    def moveAudioToMediaFolder(self):
        if self.exporter.audioPath and self.exporter.audioName:
            if exists(self.exporter.audioPath):
                path = join(self.exporter.mw.col.media.dir(), self.exporter.audioName)
                if not exists(path):
                    copyfile(self.exporter.audioPath, path)

    def playAudio(self):
        if self.exporter.audioPath:
            self.exporter.audioPlayer.play(self.exporter.audioPath)

    def exportImage(self, path, name):
        self.exporter.imgName = name
        self.exporter.imgPath = path
        if self.exporter.imageMap:
            self.exporter.imageMap.setText("")
            screenshot = QPixmap(path)
            screenshot = screenshot.scaled(
                200,
                200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.exporter.imageMap.setPixmap(screenshot)

    def exportAudio(self, path, tag, name):
        self.exporter.audioTag = tag
        self.exporter.audioName = name
        self.exporter.audioPath = path
        self.exporter.audioMap.setText(tag)
        self.exporter.audioPlay.show()

    def addImgs(self, word, imgs, thumbs):
        self.exporter.focusWindow()
        defEntry = ["Images", False, imgs, imgs]
        if defEntry in self.exporter.definitionList:
            miInfo("A card cannot contain duplicate definitions.", level="not")
            return
        self.exporter.definitionList.append(defEntry)
        rc = self.exporter.definitions.rowCount()
        self.exporter.definitions.setRowCount(rc + 1)
        self.exporter.definitions.setItem(rc, 0, QTableWidgetItem("Images"))
        self.exporter.definitions.setCellWidget(rc, 1, thumbs)
        deleteButton = QPushButton("X")
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(lambda: self.removeImgs(imgs))
        self.exporter.definitions.setCellWidget(rc, 2, deleteButton)
        self.exporter.definitions.resizeRowsToContents()
        if self.exporter.wordLE.text() == "":
            self.exporter.wordLE.setText(word)

    def exportWord(self, word):
        self.exporter.wordLE.setText(word)

    def removeImgs(self, imgs):
        try:
            row = self.exporter.definitions.selectionModel().currentIndex().row()
            self.exporter.definitions.removeRow(row)
            self.removeImgFromDefinitionList(imgs)
        except Exception:
            return

    def removeImgFromDefinitionList(self, imgs):
        for idx, entry in enumerate(self.exporter.definitionList):
            if entry[0] == "Images" and entry[3] == imgs:
                self.exporter.definitionList.pop(idx)
                break

    def addDefinition(self, dictName, word, definition):
        self.exporter.focusWindow()
        if len(definition) > 40:
            shortDef = (
                re.sub(r"<br\s*/?>", " ", definition, flags=re.IGNORECASE)[:40] + "..."
            )
        else:
            shortDef = re.sub(r"<br\s*/?>", " ", definition, flags=re.IGNORECASE)
        defEntry = [dictName, shortDef, definition, False]
        if defEntry in self.exporter.definitionList:
            miInfo("A card can not contain duplicate definitions.", level="not")
            return
        self.exporter.definitionList.append(defEntry)
        rc = self.exporter.definitions.rowCount()
        self.exporter.definitions.setRowCount(rc + 1)
        self.exporter.definitions.setItem(rc, 0, QTableWidgetItem(dictName))
        self.exporter.definitions.setItem(rc, 1, QTableWidgetItem(shortDef))
        deleteButton = QPushButton("X")
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(self.removeDefinition)
        self.exporter.definitions.setCellWidget(rc, 2, deleteButton)
        self.exporter.definitions.resizeRowsToContents()
        if self.exporter.wordLE.text() == "":
            self.exporter.wordLE.setText(word)

    def exportSentence(self, sentence):
        self.exporter.focusWindow()
        self.exporter.sentenceLE.setHtml(sentence)

    def exportSecondary(self, secondary):
        self.exporter.secondaryLE.setHtml(secondary)

    def removeFromDefinitionList(self, dictName, shortDef):
        for idx, entry in enumerate(self.exporter.definitionList):
            if entry[0] == dictName and entry[1] == shortDef:
                self.exporter.definitionList.pop(idx)
                break

    def removeDefinition(self):
        try:
            row = self.exporter.definitions.selectionModel().currentIndex().row()
            dictName = self.exporter.definitions.item(row, 0).text()
            shortDef = self.exporter.definitions.item(row, 1).text()
            self.exporter.definitions.removeRow(row)
            self.removeFromDefinitionList(dictName, shortDef)
        except Exception:
            return
