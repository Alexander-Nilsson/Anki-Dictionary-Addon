# -*- coding: utf-8 -*-
#
#
import json
import sys
import math
from anki.hooks import addHook, wrap
from aqt.qt import *
from aqt.utils import openLink, tooltip, showInfo, askUser
from anki.utils import is_mac, is_win, is_lin
from anki.lang import _
from aqt.webview import AnkiWebView
import re
import os
from os.path import dirname, join
import platform
from .dict_groups import DictGroupEditor
from .templates import TemplateEditor
from ...utils.common import miInfo, miAsk
from ..dialogs.dictionary_manager import DictionaryManagerWidget
from ...utils.config import get_addon_config, save_addon_config
from ...utils.constants import COUNTRY_LIST, FORVO_LANGUAGES

try:
    from PyQt5.QtSvg import QSvgWidget
except ModuleNotFoundError:
    from PyQt6.QtSvgWidgets import QSvgWidget


verNumber = "0.1"


def attemptOpenLink(cmd):
    if cmd.startswith("openLink:"):
        openLink(cmd[9:])


class AnkiSVG(QSvgWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QSvgWidget.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()


class DictLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()


class SettingsGui(QTabWidget):
    def __init__(self, mw, path, reboot):
        super(SettingsGui, self).__init__()
        self.mw = mw
        self.reboot = reboot
        self.imageSearchCountries = COUNTRY_LIST
        self.setMinimumSize(500, 500)
        if not is_win:
            self.resize(1034, 650)
        else:
            self.resize(920, 650)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setWindowTitle("Anki Dictionary Settings (Ver. " + verNumber + ")")
        self.addonPath = path
        self.setWindowIcon(QIcon(join(self.addonPath, "assets", "icons", "anki.svg")))
        self.addDictGroup = QPushButton("Add Dictionary Group")
        self.addExportTemplate = QPushButton("Add Export Template")
        self.dictGroups = self.getGroupTemplateTable()
        self.exportTemplates = self.getGroupTemplateTable()
        self.tooltipCB = QCheckBox()
        self.tooltipCB.setFixedHeight(30)
        self.maxImgWidth = QSpinBox()
        self.maxImgWidth.setRange(0, 9999)
        self.maxImgHeight = QSpinBox()
        self.maxImgHeight.setRange(0, 9999)
        self.imageSearchCountry = QComboBox()
        self.imageSearchCountry.addItems(self.imageSearchCountries)
        self.dictOnTop = QCheckBox()
        self.showTarget = QCheckBox()
        self.totalDefs = QSpinBox()
        self.totalDefs.setRange(0, 1000)
        self.dictDefs = QSpinBox()
        self.dictDefs.setRange(0, 100)
        self.frontBracket = QLineEdit()
        self.backBracket = QLineEdit()
        self.highlightTarget = QCheckBox()
        self.genJSExport = QCheckBox()

        # LLM Settings
        self.llmEnabled = QCheckBox()
        self.llmApiKey = QLineEdit()
        self.llmApiKey.setEchoMode(QLineEdit.EchoMode.Password)
        self.llmBaseUrl = QLineEdit()
        self.llmModel = QLineEdit()
        self.llmPrompt = QTextEdit()
        self.llmPrompt.setAcceptRichText(False)
        self.llmPrompt.setFixedHeight(100)

        # New LLM Parameters
        self.llmTemperature = QDoubleSpinBox()
        self.llmTemperature.setRange(0.0, 2.0)
        self.llmTemperature.setSingleStep(0.1)
        self.llmTemperature.setDecimals(1)

        self.llmKeepAlive = QLineEdit()
        self.llmKeepAlive.setPlaceholderText("e.g., 30m, 1h, 0")

        self.llmThink = QCheckBox()
        self.llmStream = QCheckBox()

        self.testLLMButton = QPushButton("Test API Connection")
        self.testLLMButton.clicked.connect(self.testLLM)
        self.llmStatusLabel = QLabel("")
        self.llmStatusLabel.setWordWrap(True)
        self.llmStatusLabel.setStyleSheet("font-weight: bold;")

        # Forvo Settings
        self.forvoEnabled = QCheckBox()
        self.forvoLanguage = QComboBox()
        self.forvoLanguage.setEditable(True)
        for lang in FORVO_LANGUAGES:
            self.forvoLanguage.addItem(lang["English name"], lang["Code"])

        # Frequency Lists Settings
        self.freqStarChar = QLineEdit()
        self.freqStarChar.setMaxLength(2)
        self.freqThreshold1 = QSpinBox()
        self.freqThreshold1.setRange(1, 1000000)
        self.freqThreshold2 = QSpinBox()
        self.freqThreshold2.setRange(1, 1000000)
        self.freqThreshold3 = QSpinBox()
        self.freqThreshold3.setRange(1, 1000000)
        self.freqThreshold4 = QSpinBox()
        self.freqThreshold4.setRange(1, 1000000)
        self.freqThreshold5 = QSpinBox()
        self.freqThreshold5.setRange(1, 1000000)

        self.showStars = QCheckBox("Display Stars")
        self.showRank = QCheckBox("Display Frequency Rank")
        self.showHSK = QCheckBox("Display Level Labels (HSK, JLPT, etc.)")

        self.hskMode = QComboBox()
        self.hskMode.addItem("HSK 3.0", "hsk3")
        self.hskMode.addItem("HSK 2.0", "hsk2")
        self.hskMode.addItem("Both (HSK 2.0 & 3.0)", "both")

        self.restoreButton = QPushButton("Restore Defaults")
        self.cancelButton = QPushButton("Cancel")
        self.applyButton = QPushButton("Apply")
        self.layout = QVBoxLayout()
        self.settingsTab = QWidget()
        self.llmTab = self.getLLMTab()
        self.forvoTab = self.getForvoTab()
        self.frequencyTab = self.getFrequencyTab()

        self.setupLayout()

        self.addTab(self.wrapInScrollArea(self.settingsTab), "Settings")
        self.addTab(self.wrapInScrollArea(self.llmTab), "LLM")
        self.addTab(self.wrapInScrollArea(self.forvoTab), "Forvo")
        self.addTab(self.wrapInScrollArea(self.frequencyTab), "Frequency Lists")
        self.addTab(
            self.wrapInScrollArea(DictionaryManagerWidget(self.mw)), "Dictionaries"
        )

        self.loadTemplateTable()
        self.loadGroupTable()
        self.initHandlers()
        self.loadConfig()
        self.initTooltips()
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.close)

        self.show()

    def wrapInScrollArea(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    def hideEvent(self, event):
        self.mw.dictSettings = None
        # self.userGuideTab.close()
        # self.userGuideTab.deleteLater()
        event.accept()

    def closeEvent(self, event):
        self.mw.dictSettings = None
        # self.userGuideTab.close()
        # self.userGuideTab.deleteLater()
        event.accept()

    def initTooltips(self):
        self.addDictGroup.setToolTip(
            "Add a new dictionary group.\nDictionary groups allow you to specify which dictionaries to search\nwithin. You can also set a specific font for that group."
        )
        self.addExportTemplate.setToolTip(
            "Add a new export template.\nExport templates allow you to specify a note type, and fields where\ntarget sentences, target words, definitions, and images will be sent to\n when using the Card Exporter to create cards."
        )
        self.tooltipCB.setToolTip(
            "Enable/disable tooltips within the dictionary and its sub-windows."
        )
        self.maxImgWidth.setToolTip("Images will be scaled according to this width.")
        self.maxImgHeight.setToolTip("Images will be scaled according to this height.")
        self.imageSearchCountry.setToolTip(
            "Select the country or region for image search, the search region\ngreatly impacts search results so choose a location where your target language is spoken."
        )
        self.showTarget.setToolTip(
            "Show/Hide the Target Identifier from the dictionary window. The Target Identifier\nlets you know which window is currently selected and will be used when sending\ndefinitions to a target field."
        )
        self.totalDefs.setToolTip(
            "This is the total maximum number of definitions which the dictionary will output."
        )
        self.dictDefs.setToolTip(
            "This is the maximum number of definitions which the dictionary will output for any given dictionary."
        )
        self.genJSExport.setToolTip(
            "If this is enabled and you have Anki Japanese With Pitch Accent installed in Anki,\nthen when a card is exported, readings and accent information will automatically be generated for all\nactive fields. This generation is based on your Anki Japanese With Pitch Accent Sentence Button (文) settings."
        )
        self.frontBracket.setToolTip(
            "This is the text that will be placed in front of each term\n in the dictionary."
        )
        self.backBracket.setToolTip(
            "This is the text that will be placed after each term\nin the dictionary."
        )
        self.highlightTarget.setToolTip(
            "The dictionary will highlight the searched term in\nthe search results."
        )

        # LLM Tooltips
        self.llmTemperature.setToolTip(
            "Controls randomness: Lower is more focused/deterministic, higher is more creative."
        )
        self.llmKeepAlive.setToolTip(
            "How long the model stays loaded in memory after the request (e.g., '30m', '1h'). Set to '0' to unload immediately."
        )
        self.llmThink.setToolTip(
            "If enabled, internal reasoning/thinking tags (like <think>) will be visible in the results. Currently supported by models like DeepSeek."
        )
        self.llmStream.setToolTip(
            "Enable streaming response. Note: The addon currently waits for the full response before displaying, but this can affect API behavior."
        )

    def getConfig(self):
        return get_addon_config()

    def loadConfig(self):
        config = self.getConfig()
        self.highlightTarget.setChecked(config.get("highlightTarget", True))
        self.totalDefs.setValue(config.get("maxSearch", 1000))
        self.dictDefs.setValue(config.get("dictSearch", 50))
        self.imageSearchCountry.setCurrentText(
            config.get("imageSearchRegion", "United States")
        )
        self.maxImgWidth.setValue(config.get("maxWidth", 1500))
        self.maxImgHeight.setValue(config.get("maxHeight", 400))
        self.frontBracket.setText(config.get("frontBracket", "【"))
        self.backBracket.setText(config.get("backBracket", "】"))
        self.showTarget.setChecked(config.get("showTarget", False))
        self.tooltipCB.setChecked(config.get("tooltips", True))
        self.dictOnTop.setChecked(config.get("dictAlwaysOnTop", False))
        self.genJSExport.setChecked(config.get("jReadingCards", False))

        # Load LLM settings
        self.llmEnabled.setChecked(config.get("llm_enabled", False))
        self.llmApiKey.setText(config.get("llm_api_key", ""))
        self.llmBaseUrl.setText(
            config.get("llm_base_url", "https://api.openai.com/v1/chat/completions")
        )
        self.llmModel.setText(config.get("llm_model", "gpt-3.5-turbo"))
        self.llmPrompt.setPlainText(
            config.get(
                "llm_prompt",
                "Provide a concise dictionary definition for the word: {term}",
            )
        )
        self.llmTemperature.setValue(config.get("llm_temperature", 0.3))
        self.llmKeepAlive.setText(config.get("llm_keep_alive", "30m"))
        self.llmThink.setChecked(config.get("llm_think", False))
        self.llmStream.setChecked(config.get("llm_stream", False))

        # Load Forvo settings

        self.forvoEnabled.setChecked(config.get("forvo_enabled", True))
        forvo_lang = config.get("forvo_language", "ja")
        index = self.forvoLanguage.findData(forvo_lang)
        if index != -1:
            self.forvoLanguage.setCurrentIndex(index)

        # Load Frequency/HSK settings
        self.freqStarChar.setText(config.get("star_char", "★"))
        thresholds = config.get("star_thresholds", [1501, 5001, 15001, 30001, 60001])
        self.freqThreshold1.setValue(thresholds[0])
        self.freqThreshold2.setValue(thresholds[1])
        self.freqThreshold3.setValue(thresholds[2])
        self.freqThreshold4.setValue(thresholds[3])
        self.freqThreshold5.setValue(thresholds[4])

        self.showStars.setChecked(config.get("show_stars", True))
        self.showRank.setChecked(config.get("show_rank", False))
        self.showHSK.setChecked(config.get("show_hsk", True))

        hsk_mode = config.get("hsk_mode", "hsk3")
        index = self.hskMode.findData(hsk_mode)
        if index != -1:
            self.hskMode.setCurrentIndex(index)

    def saveConfig(self):
        nc = self.getConfig()
        nc["highlightTarget"] = self.highlightTarget.isChecked()
        nc["maxSearch"] = self.totalDefs.value()
        nc["dictSearch"] = self.dictDefs.value()
        nc["imageSearchRegion"] = self.imageSearchCountry.currentText()
        nc["maxWidth"] = self.maxImgWidth.value()
        nc["maxHeight"] = self.maxImgHeight.value()
        nc["frontBracket"] = self.frontBracket.text()
        nc["backBracket"] = self.backBracket.text()
        nc["showTarget"] = self.showTarget.isChecked()
        nc["tooltips"] = self.tooltipCB.isChecked()
        nc["dictAlwaysOnTop"] = self.dictOnTop.isChecked()
        nc["jReadingCards"] = self.genJSExport.isChecked()

        # Save LLM settings
        nc["llm_enabled"] = self.llmEnabled.isChecked()
        nc["llm_api_key"] = self.llmApiKey.text()
        nc["llm_base_url"] = self.llmBaseUrl.text()
        nc["llm_model"] = self.llmModel.text()
        nc["llm_prompt"] = self.llmPrompt.toPlainText()
        nc["llm_temperature"] = self.llmTemperature.value()
        nc["llm_keep_alive"] = self.llmKeepAlive.text()
        nc["llm_think"] = self.llmThink.isChecked()
        nc["llm_stream"] = self.llmStream.isChecked()

        # Save Forvo settings

        nc["forvo_enabled"] = self.forvoEnabled.isChecked()
        nc["forvo_language"] = self.forvoLanguage.currentData()

        # Save Frequency/HSK settings
        nc["star_char"] = self.freqStarChar.text()
        nc["star_thresholds"] = [
            self.freqThreshold1.value(),
            self.freqThreshold2.value(),
            self.freqThreshold3.value(),
            self.freqThreshold4.value(),
            self.freqThreshold5.value(),
        ]
        nc["show_stars"] = self.showStars.isChecked()
        nc["show_rank"] = self.showRank.isChecked()
        nc["show_hsk"] = self.showHSK.isChecked()
        nc["hsk_mode"] = self.hskMode.currentData()

        save_addon_config(nc)
        self.hide()

        # Refresh dictionary window with new settings
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(nc)

    def getGroupTemplateTable(self):
        macLin = False
        if is_mac or is_lin:
            macLin = True
        groupTemplates = QTableWidget()
        groupTemplates.setColumnCount(3)
        tableHeader = groupTemplates.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        tableHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        groupTemplates.setRowCount(0)
        groupTemplates.setSortingEnabled(False)
        groupTemplates.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        groupTemplates.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        if macLin:
            groupTemplates.setColumnWidth(1, 50)
            groupTemplates.setColumnWidth(2, 40)
        else:
            groupTemplates.setColumnWidth(1, 40)
            groupTemplates.setColumnWidth(2, 40)
        tableHeader.hide()
        return groupTemplates

    def loadGroupTable(self):
        self.dictGroups.setRowCount(0)
        dictGroups = self.getConfig()["DictionaryGroups"]
        for groupName in dictGroups:
            rc = self.dictGroups.rowCount()
            self.dictGroups.setRowCount(rc + 1)
            self.dictGroups.setItem(rc, 0, QTableWidgetItem(groupName))
            editButton = QPushButton("Edit")
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editGroupRow(rc))
            self.dictGroups.setCellWidget(rc, 1, editButton)
            deleteButton = QPushButton("X")
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.clicked.connect(self.removeGroupRow(rc))
            self.dictGroups.setCellWidget(rc, 2, deleteButton)

    def removeGroupRow(self, x):
        return lambda: self.removeGroup(x)

    def editGroupRow(self, x):
        return lambda: self.editGroup(x)

    def editGroup(self, row):
        groupName = self.dictGroups.item(row, 0).text()
        dictGroups = self.getConfig()["DictionaryGroups"]
        if groupName in dictGroups:
            group = dictGroups[groupName]
            dictEditor = DictGroupEditor(
                self.mw, self, self.getDictionaryNames(), group, groupName
            )
            dictEditor.exec()

            # dictEditor.exec()

    def removeGroup(self, row):
        if miAsk(
            "Are you sure you would like to remove this dictionary group? This action will happen immediately and is not un-doable.",
            self,
        ):
            newConfig = self.getConfig()
            dictGroups = newConfig["DictionaryGroups"]
            groupName = self.dictGroups.item(row, 0).text()
            del dictGroups[groupName]
            save_addon_config(newConfig)
            self.dictGroups.removeRow(row)
            self.loadGroupTable()

    def loadTemplateTable(self):
        self.exportTemplates.setRowCount(0)
        exportTemplates = self.getConfig()["ExportTemplates"]
        for template in exportTemplates:
            rc = self.exportTemplates.rowCount()
            self.exportTemplates.setRowCount(rc + 1)
            self.exportTemplates.setItem(rc, 0, QTableWidgetItem(template))
            editButton = QPushButton("Edit")
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editTempRow(rc))
            self.exportTemplates.setCellWidget(rc, 1, editButton)
            deleteButton = QPushButton("X")
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.clicked.connect(self.removeTempRow(rc))
            self.exportTemplates.setCellWidget(rc, 2, deleteButton)

    def removeTemplate(self, row):
        if miAsk(
            "Are you sure you would like to remove this template? This action will happen immediately and is not un-doable.",
            self,
        ):
            newConfig = self.getConfig()
            exportTemplates = newConfig["ExportTemplates"]
            templateName = self.exportTemplates.item(row, 0).text()
            del exportTemplates[templateName]
            save_addon_config(newConfig)
            self.exportTemplates.removeRow(row)
            self.loadTemplateTable()

    def removeTempRow(self, x):
        return lambda: self.removeTemplate(x)

    def editTempRow(self, x):
        return lambda: self.editTemplate(x)

    def editTemplate(self, row):
        templateName = self.exportTemplates.item(row, 0).text()
        exportTemplates = self.getConfig()["ExportTemplates"]
        if templateName in exportTemplates:
            template = exportTemplates[templateName]
            templateEditor = TemplateEditor(
                self.mw, self, self.getDictionaryNames(), template, templateName
            )
            templateEditor.loadTemplateEditor(template, templateName)
            templateEditor.exec()

    def getDictionaryNames(self):
        dictList = self.mw.miDictDB.getAllDictsWithLang()
        dictionaryList = []
        for dictionary in dictList:
            dictName = self.cleanDictName(dictionary["dict"]).replace("_", " ")
            if dictName not in dictionaryList:
                dictionaryList.append(dictName)

        # Add special entries
        if "Images" not in dictionaryList:
            dictionaryList.append("Images")

        # Check current UI state for LLM enabled
        if self.llmEnabled.isChecked() and "LLM" not in dictionaryList:
            dictionaryList.append("LLM")

        # Check current UI state for Forvo enabled
        if self.forvoEnabled.isChecked() and "Forvo" not in dictionaryList:
            dictionaryList.append("Forvo")

        dictionaryList = sorted(dictionaryList, key=str.casefold)
        return dictionaryList

    def initHandlers(self):
        self.addDictGroup.clicked.connect(self.addGroup)
        self.addExportTemplate.clicked.connect(self.addTemplate)
        self.restoreButton.clicked.connect(self.restoreDefaults)
        self.cancelButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.saveConfig)

    def restoreDefaults(self):
        if miAsk(
            "This will remove any export templates and dictionary groups you have created, and is not undoable. Are you sure you would like to restore the default settings?"
        ):
            conf = self.mw.addonManager.addonConfigDefaults(dirname(__file__))
            save_addon_config(conf)
            # self.userGuideTab.close()
            # self.userGuideTab.deleteLater()
            self.close()
            self.reboot()

    def addGroup(self):
        dictEditor = DictGroupEditor(self.mw, self, self.getDictionaryNames())
        dictEditor.clearGroupEditor(True)
        dictEditor.exec()

    def addTemplate(self):
        templateEditor = TemplateEditor(self.mw, self, self.getDictionaryNames())
        templateEditor.exec()

    def miQLabel(self, text, width):
        label = QLabel(text)
        label.setFixedHeight(30)
        label.setFixedWidth(width)
        return label

    def getLineSeparator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet('QFrame[frameShape="5"]{color: #D5DFE5;}')
        return line

    def setupLayout(self):
        # 1. Dictionary Groups & Export Templates
        groupLayout = QVBoxLayout()
        dictsLayout = QVBoxLayout()
        exportsLayout = QVBoxLayout()

        dictsLayout.addWidget(QLabel("Dictionary Groups"))
        dictsLayout.addWidget(self.addDictGroup)
        dictsLayout.addWidget(self.dictGroups)

        exportsLayout.addWidget(QLabel("Export Templates"))
        exportsLayout.addWidget(self.addExportTemplate)
        exportsLayout.addWidget(self.exportTemplates)

        groupLayout.addLayout(dictsLayout)
        groupLayout.addLayout(exportsLayout)
        self.layout.addLayout(groupLayout)

        # 2. Options in categorized groups
        optionsLayout = QVBoxLayout()

        # --- Search & Behavior Group ---
        searchGroup = QGroupBox("Search & Behavior")
        searchForm = QFormLayout()
        searchForm.addRow("Max Total Results:", self.totalDefs)
        searchForm.addRow("Max per Dictionary:", self.dictDefs)
        searchForm.addRow("Image Search Region:", self.imageSearchCountry)

        bracketLayout = QHBoxLayout()
        bracketLayout.addWidget(self.frontBracket)
        bracketLayout.addWidget(QLabel("Term"))
        bracketLayout.addWidget(self.backBracket)
        searchForm.addRow("Surround Term:", bracketLayout)

        searchGroup.setLayout(searchForm)
        optionsLayout.addWidget(searchGroup)

        # --- Display & UI Group ---
        displayGroup = QGroupBox("Display & UI")
        displayLayout = QVBoxLayout()

        self.highlightTarget.setText("Highlight Searched Term")
        displayLayout.addWidget(self.highlightTarget)

        self.showTarget.setText("Show Export Target Identifier")
        displayLayout.addWidget(self.showTarget)

        self.tooltipCB.setText("Enable Tooltips")
        displayLayout.addWidget(self.tooltipCB)

        self.dictOnTop.setText("Keep Dictionary Always on Top")
        displayLayout.addWidget(self.dictOnTop)

        displayGroup.setLayout(displayLayout)
        optionsLayout.addWidget(displayGroup)

        # --- Media & Integration Group ---
        mediaGroup = QGroupBox("Media & Integration")
        mediaForm = QFormLayout()
        mediaForm.addRow("Max Image Width:", self.maxImgWidth)
        mediaForm.addRow("Max Image Height:", self.maxImgHeight)

        self.genJSExport.setText("Generate Japanese Readings (Export)")
        mediaForm.addRow(self.genJSExport)

        mediaGroup.setLayout(mediaForm)
        optionsLayout.addWidget(mediaGroup)

        self.layout.addLayout(optionsLayout)
        self.layout.addStretch()

        # 3. Bottom Buttons
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.restoreButton)
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.cancelButton)
        buttonsLayout.addWidget(self.applyButton)

        self.layout.addLayout(buttonsLayout)
        self.settingsTab.setLayout(self.layout)

    def cleanDictName(self, name):
        return re.sub(r"l\d+name", "", name)

    def getSVGWidget(self, name):
        widget = AnkiSVG(join(self.addonPath, "icons", name))
        widget.setFixedSize(27, 27)
        return widget

    def getLLMTab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        infoLabel = QLabel(
            "Configure an OpenAI-compatible LLM to get AI-generated definitions."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        formGroup = QGroupBox("LLM Configuration")
        formLayout = QFormLayout()

        formLayout.addRow("Enable LLM Dictionary:", self.llmEnabled)
        formLayout.addRow("API Key:", self.llmApiKey)
        formLayout.addRow("Base URL:", self.llmBaseUrl)

        baseUrlHint = QLabel(
            "Supports Ollama (e.g., http://localhost:11434/api/chat) or OpenAI-style endpoints."
        )
        baseUrlHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", baseUrlHint)

        formLayout.addRow("Model:", self.llmModel)
        formLayout.addRow("Temperature:", self.llmTemperature)
        formLayout.addRow("Keep Alive:", self.llmKeepAlive)
        formLayout.addRow("Enable Thinking", self.llmThink)
        formLayout.addRow("Enable Streaming:", self.llmStream)
        formLayout.addRow("Prompt Template:", self.llmPrompt)

        promptHint = QLabel("Use {term} as a placeholder for the word being searched.")
        promptHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", promptHint)

        formGroup.setLayout(formLayout)
        layout.addWidget(formGroup)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.testLLMButton)
        buttonLayout.addWidget(self.llmStatusLabel)
        buttonLayout.addStretch()
        layout.addLayout(buttonLayout)

        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def getForvoTab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        infoLabel = QLabel(
            "Enable Forvo to fetch native pronunciations for your search terms."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        formGroup = QGroupBox("Forvo Configuration")
        formLayout = QFormLayout()

        formLayout.addRow("Enable Forvo Dictionary:", self.forvoEnabled)
        formLayout.addRow("Forvo Language:", self.forvoLanguage)

        langHint = QLabel("Select the language for Forvo pronunciation searches.")
        langHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", langHint)

        formGroup.setLayout(formLayout)
        layout.addWidget(formGroup)

        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def getFrequencyTab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        infoLabel = QLabel(
            "Configure how frequency information and level labels are displayed."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        # Visibility Group
        visGroup = QGroupBox("Visibility Options")
        visLayout = QVBoxLayout()
        visLayout.addWidget(self.showStars)
        visLayout.addWidget(self.showRank)
        visLayout.addWidget(self.showHSK)
        visGroup.setLayout(visLayout)
        layout.addWidget(visGroup)

        # Stars Configuration
        starGroup = QGroupBox("Star Configuration")
        starLayout = QFormLayout()
        starLayout.addRow("Star Character:", self.freqStarChar)

        threshLayout = QHBoxLayout()
        threshLayout.addWidget(self.freqThreshold1)
        threshLayout.addWidget(self.freqThreshold2)
        threshLayout.addWidget(self.freqThreshold3)
        threshLayout.addWidget(self.freqThreshold4)
        threshLayout.addWidget(self.freqThreshold5)

        starLayout.addRow("Rank Thresholds:", threshLayout)
        starHint = QLabel("Rank thresholds for 5, 4, 3, 2, and 1 star(s) respectively.")
        starHint.setStyleSheet("font-size: 10px; color: gray;")
        starLayout.addRow("", starHint)

        starGroup.setLayout(starLayout)
        layout.addWidget(starGroup)

        # HSK Configuration
        hskGroup = QGroupBox("Chinese HSK Configuration")
        hskLayout = QFormLayout()
        hskLayout.addRow("HSK Version Preference:", self.hskMode)
        hskHint = QLabel(
            "For Chinese, choose HSK 3.0 (9 levels), HSK 2.0 (6 levels), or show both simultaneously."
        )
        hskHint.setStyleSheet("font-size: 10px; color: gray;")
        hskLayout.addRow("", hskHint)
        hskGroup.setLayout(hskLayout)
        layout.addWidget(hskGroup)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def testLLM(self):
        """Test the LLM configuration."""
        self.testLLMButton.setEnabled(False)
        self.testLLMButton.setText("Testing...")
        self.llmStatusLabel.setText("Testing...")
        self.llmStatusLabel.setStyleSheet("color: blue; font-weight: bold;")

        # Get current settings from UI
        config = {
            "llm_api_key": self.llmApiKey.text().strip(),
            "llm_base_url": self.llmBaseUrl.text().strip(),
            "llm_model": self.llmModel.text().strip(),
        }

        from ...integrations.llm import test_llm_config

        # Define a wrapper for taskman that includes the callback
        def run_test():
            result_data = {"success": False, "message": ""}

            def test_callback(success, message):
                result_data["success"] = success
                result_data["message"] = message

            test_llm_config(config, test_callback)
            return result_data

        # Use Anki's task manager for background operations
        self.mw.taskman.run_in_background(run_test, self.on_test_finished)

    def on_test_finished(self, future):
        """Handle the completion of the background test."""
        self.testLLMButton.setEnabled(True)
        self.testLLMButton.setText("Test API Connection")

        try:
            result = future.result()
            success = result["success"]
            message = result["message"]

            if success:
                self.llmStatusLabel.setText("Success!")
                self.llmStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                showInfo(message, self)
            else:
                self.llmStatusLabel.setText("Failed!")
                self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
                miInfo(message, self)
        except Exception as e:
            self.llmStatusLabel.setText("Error!")
            self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
            miInfo(f"Test crashed with error: {str(e)}", self)

    def getHTML(self):

        htmlPath = join(self.addonPath, "guide.html")
        url = QUrl.fromLocalFile(htmlPath)
        with open(htmlPath, "r", encoding="utf-8") as fh:
            html = fh.read()
        return html, url
