# -*- coding: utf-8 -*-
from __future__ import annotations

import collections
import re

from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class FieldMapper:
    def __init__(self, exporter):
        self.exporter = exporter

    def fieldValid(self, field):
        return field != "Don't Export"

    def emptyValueIfEmptyHtml(self, value):
        pattern = r"(?:<[^<]+?>)"
        if re.sub(pattern, "", value) == "":
            return ""
        return value

    def getDictionaryEntries(self, dictionary):
        finList = []
        idxs = []
        for idx, defList in enumerate(self.exporter.definitionList):
            if defList[0] == dictionary:
                finList.append(defList[2])
                idxs.append(idx)
        idxs.reverse()
        for idx in idxs:
            self.exporter.definitionList.pop(idx)
        return finList

    def getDictionaryNameToTableNameDictionary(self):
        dictToTable = collections.OrderedDict()
        dictToTable["None"] = "None"
        dictToTable["Images"] = "Images"
        for dictTableName in sorted(self.exporter.mw.miDictDB.getAllDicts()):
            dictName = self.exporter.mw.miDictDB.cleanDictName(dictTableName)
            dictToTable[dictName] = dictTableName
        return dictToTable

    def getFieldsValues(self, t):
        imgField = False
        audioField = False
        tagsField = ""
        fields = {}
        sentenceText = self.exporter.html_cleaner.cleanHTML(
            self.exporter.sentenceLE.toHtml()
        )
        sentenceText = self.emptyValueIfEmptyHtml(sentenceText)
        if sentenceText != "":
            sentenceField = t["sentence"]
            if sentenceField != "Don't Export":
                if self.fieldValid(sentenceField):
                    fields[sentenceField] = [sentenceText]
        secondaryText = self.exporter.html_cleaner.cleanHTML(
            self.exporter.secondaryLE.toHtml()
        )
        secondaryText = self.emptyValueIfEmptyHtml(secondaryText)
        if secondaryText != "" and "secondary" in t:
            secondaryField = t["secondary"]
            if secondaryField != "Don't Export":
                if self.fieldValid(secondaryField):
                    fields[secondaryField] = [secondaryText]
        notesText = self.exporter.html_cleaner.cleanHTML(self.exporter.notesLE.toHtml())
        notesText = self.emptyValueIfEmptyHtml(notesText)
        if notesText != "" and "notes" in t:
            notesField = t["notes"]
            if notesField != "Don't Export":
                if self.fieldValid(notesField):
                    fields[notesField] = [notesText]
        wordText = self.exporter.wordLE.text()
        if wordText != "":
            wordField = t["word"]
            if wordField != "Don't Export":
                if self.fieldValid(wordField):
                    if wordField not in fields:
                        fields[wordField] = [wordText]
                    else:
                        fields[wordField].append(wordText)
        tagsText = self.exporter.tagsLE.text()
        if tagsText != "":
            tagsField = tagsText
        imgText = self.exporter.imageMap.text()
        if imgText != "No Image Selected":
            imgField = t["image"]
            if imgField != "Don't Export":
                imgTag = '<img ankiDict="' + self.exporter.imgName + '">'
                if self.fieldValid(imgField):
                    if imgField not in fields:
                        fields[imgField] = [imgTag]
                    else:
                        fields[imgField].append(imgTag)
        audioText = self.exporter.imageMap.text()
        if (
            audioText != "No Audio Selected"
            and "audio" in t
            and self.exporter.audioTag is not False
        ):
            audioField = t["audio"]
            if audioField != "Don't Export":
                if self.fieldValid(audioField):
                    if audioField not in fields:
                        fields[audioField] = [self.exporter.audioTag]
                    else:
                        fields[audioField].append(self.exporter.audioTag)
        specific = t["specific"]
        for field in specific:
            for dictionary in specific[field]:
                if field not in fields:
                    fields[field] = self.getDictionaryEntries(dictionary)
                else:
                    fields[field] += self.getDictionaryEntries(dictionary)
        unspecified = t["unspecified"]
        for idx, defList in enumerate(self.exporter.definitionList):
            if unspecified not in fields:
                fields[unspecified] = [defList[2]]
            else:
                fields[unspecified].append(defList[2])
        return fields, imgField, audioField, tagsField

    def getFieldsValuesForTextCard(self, t, wordText, sentenceText):
        tagsField = ""
        fields = {}
        if sentenceText != "":
            sentenceField = t["sentence"]
            if sentenceField != "Don't Export":
                if self.fieldValid(sentenceField):
                    fields[sentenceField] = [sentenceText]
        if wordText != "":
            wordField = t["word"]
            if wordField != "Don't Export":
                if self.fieldValid(wordField):
                    if wordField not in fields:
                        fields[wordField] = [wordText]
                    else:
                        fields[wordField].append(wordText)
        tagsText = self.exporter.tagsLE.text()
        if tagsText != "":
            tagsField = tagsText
        return fields, tagsField

    def getFieldsValuesForMediaCard(self, t, wordText, card):
        sentenceText = card["primary"]
        secondaryText = card["secondary"]
        imageFile = card["image"]
        audioFile = card["audio"]
        audio = False
        image = False
        if audioFile:
            audio = "[sound:" + audioFile + "]"
        if imageFile:
            image = imageFile
        imgField = False
        audioField = False
        tagsField = ""
        fields = {}
        if sentenceText != "":
            sentenceField = t["sentence"]
            if sentenceField != "Don't Export":
                if self.fieldValid(sentenceField):
                    fields[sentenceField] = [sentenceText]
        if secondaryText != "" and "secondary" in t:
            secondaryField = t["secondary"]
            if secondaryField != "Don't Export":
                if self.fieldValid(secondaryField):
                    fields[secondaryField] = [secondaryText]
        if wordText != "":
            wordField = t["word"]
            if wordField != "Don't Export":
                if self.fieldValid(wordField):
                    if wordField not in fields:
                        fields[wordField] = [wordText]
                    else:
                        fields[wordField].append(wordText)
        tagsText = self.exporter.tagsLE.text()
        if tagsText != "":
            tagsField = tagsText
        if image:
            imgField = t["image"]
            imgTag = '<img ankiDict="' + image + '">'
            if self.fieldValid(imgField):
                if imgField not in fields:
                    fields[imgField] = [imgTag]
                else:
                    fields[imgField].append(imgTag)
        if audio:
            audioField = t["audio"]
            if self.fieldValid(audioField):
                if audioField not in fields:
                    fields[audioField] = [audio]
                else:
                    fields[audioField].append(audio)
        return fields, tagsField
