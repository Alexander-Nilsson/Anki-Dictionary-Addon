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
from ...utils.constants import COUNTRY_LIST

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
        self.setMinimumSize(850, 550)
        if not is_win:
            self.resize(1034, 550)
        else:
            self.resize(920, 550)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setWindowTitle("Anki Dictionary Settings (Ver. " + verNumber + ")")
        self.addonPath = path
        self.setWindowIcon(
            QIcon(join(self.addonPath, "assets", "icons", "dictionary.png"))
        )
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
        self.condensedAudioDirectoryLabel = QLabel("Condensed Audio Save Location:")
        self.chooseAudioDirectory = QPushButton("Choose Directory")
        self.disableCondensedMessages = QCheckBox()
        self.dictOnTop = QCheckBox()
        self.showTarget = QCheckBox()
        self.totalDefs = QSpinBox()
        self.totalDefs.setRange(0, 1000)
        self.dictDefs = QSpinBox()
        self.dictDefs.setRange(0, 100)
        self.frontBracket = QLineEdit()
        self.backBracket = QLineEdit()
        self.highlightTarget = QCheckBox()
        self.highlightSentence = QCheckBox()
        self.openOnStart = QCheckBox()
        self.globalHotkeys = QCheckBox()
        self.globalOpen = QCheckBox()

        # LLM Settings
        self.llmEnabled = QCheckBox()
        self.llmApiKey = QLineEdit()
        self.llmApiKey.setEchoMode(QLineEdit.EchoMode.Password)
        self.llmBaseUrl = QLineEdit()
        self.llmModel = QLineEdit()
        self.llmPrompt = QTextEdit()
        self.llmPrompt.setAcceptRichText(False)
        self.llmPrompt.setFixedHeight(100)
        self.testLLMButton = QPushButton("Test API Connection")
        self.testLLMButton.clicked.connect(self.testLLM)
        self.llmStatusLabel = QLabel("")
        self.llmStatusLabel.setWordWrap(True)
        self.llmStatusLabel.setStyleSheet("font-weight: bold;")

        self.restoreButton = QPushButton("Restore Defaults")
        self.cancelButton = QPushButton("Cancel")
        self.applyButton = QPushButton("Apply")
        self.layout = QVBoxLayout()
        self.settingsTab = QWidget(self)
        self.llmTab = self.getLLMTab()
        # self.userGuideTab = self.getUserGuideTab()
        self.setupLayout()
        self.addTab(self.settingsTab, "Settings")
        self.addTab(self.llmTab, "LLM API")
        self.addTab(DictionaryManagerWidget(), "Dictionaries")
        # self.addTab(self.userGuideTab, "User Guide")
        # self.addTab(self.getAboutTab(), "About")
        self.loadTemplateTable()
        self.loadGroupTable()
        self.initHandlers()
        self.loadConfig()
        self.initTooltips()
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.close)

        self.show()

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
        self.genJSEdit.setToolTip(
            "If this is enabled and you have Anki Japanese With Pitch Accent installed in Anki,\nthen when a definition is sent to a field, readings and accent information will automatically be generated for all\nactive fields. This generation is based on your Anki Japanese With Pitch Accent Sentence Button (文) settings."
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
        self.highlightSentence.setToolTip(
            "The dictionary will highlight example sentences in\nthe search results. This feature is experimental and currently only\nfunctions on Japanese monolingual dictionaries."
        )
        self.openOnStart.setToolTip(
            "Enable/Disable launching the Anki Dictionary on profile load."
        )
        linNote = ""
        self.globalHotkeys.setToolTip("Enable/Disable global hotkeys." + linNote)
        self.globalOpen.setToolTip(
            "If enabled the dictionary will be opened on a global search."
        )
        self.disableCondensedMessages.setToolTip(
            "Disable messages shown when condensed audio files are successfully created."
        )

    def getConfig(self):
        return get_addon_config()

    def loadConfig(self):
        config = self.getConfig()
        self.openOnStart.setChecked(config["dictOnStart"])
        self.highlightSentence.setChecked(config["highlightSentences"])
        self.highlightTarget.setChecked(config["highlightTarget"])
        self.totalDefs.setValue(config["maxSearch"])
        self.dictDefs.setValue(config["dictSearch"])
        self.imageSearchCountry.setCurrentText(config["imageSearchRegion"])
        self.maxImgWidth.setValue(config["maxWidth"])
        self.maxImgHeight.setValue(config["maxHeight"])
        self.frontBracket.setText(config["frontBracket"])
        self.backBracket.setText(config["backBracket"])
        self.showTarget.setChecked(config["showTarget"])
        self.tooltipCB.setChecked(config["tooltips"])
        self.globalHotkeys.setChecked(config["globalHotkeys"])
        self.globalOpen.setChecked(config["openOnGlobal"])
        self.disableCondensedMessages.setChecked(config["disableCondensed"])
        self.dictOnTop.setChecked(config["dictAlwaysOnTop"])

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

        if config.get("condensedAudioDirectory", False) is not False:
            self.chooseAudioDirectory.setText(config["condensedAudioDirectory"])
        else:
            self.chooseAudioDirectory.setText("Choose Directory")

    def saveConfig(self):
        nc = self.getConfig()
        nc["dictOnStart"] = self.openOnStart.isChecked()
        nc["highlightSentences"] = self.highlightSentence.isChecked()
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
        nc["globalHotkeys"] = self.globalHotkeys.isChecked()
        nc["openOnGlobal"] = self.globalOpen.isChecked()
        nc["disableCondensed"] = self.disableCondensedMessages.isChecked()
        nc["dictAlwaysOnTop"] = self.dictOnTop.isChecked()

        # Save LLM settings
        nc["llm_enabled"] = self.llmEnabled.isChecked()
        nc["llm_api_key"] = self.llmApiKey.text()
        nc["llm_base_url"] = self.llmBaseUrl.text()
        nc["llm_model"] = self.llmModel.text()
        nc["llm_prompt"] = self.llmPrompt.toPlainText()

        if self.chooseAudioDirectory.text() != "Choose Directory":
            nc["condensedAudioDirectory"] = self.chooseAudioDirectory.text()
        else:
            nc["condensedAudioDirectory"] = False
        save_addon_config(nc)
        self.hide()

        # Refresh dictionary window with new settings
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(nc)
        if nc["mp3Convert"]:
            self.ffmpegInstaller.installFFMPEG()

    def updateAudioDirectory(self):
        directory = str(
            QFileDialog.getExistingDirectory(None, "Select Condensed Audio Directory")
        )
        if directory:
            self.chooseAudioDirectory.setText(directory)
        else:
            self.chooseAudioDirectory.setText("Choose Directory")

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
            dictName = self.cleanDictName(dictionary["dict"])
            if dictName not in dictionaryList:
                dictionaryList.append(dictName)

        # Add special entries
        if "Images" not in dictionaryList:
            dictionaryList.append("Images")

        # Check current UI state for LLM enabled
        if self.llmEnabled.isChecked() and "LLM API" not in dictionaryList:
            dictionaryList.append("LLM API")

        dictionaryList = sorted(dictionaryList, key=str.casefold)
        return dictionaryList

    def initHandlers(self):
        self.addDictGroup.clicked.connect(self.addGroup)
        self.addExportTemplate.clicked.connect(self.addTemplate)
        self.restoreButton.clicked.connect(self.restoreDefaults)
        self.cancelButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.saveConfig)
        self.chooseAudioDirectory.clicked.connect(self.updateAudioDirectory)

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
        groupLayout = QHBoxLayout()
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

        optionsBox = QGroupBox("Options")
        optionsLayout = QHBoxLayout()
        optLay1 = QVBoxLayout()
        optLay2 = QVBoxLayout()
        optLay3 = QVBoxLayout()

        startupLay = QHBoxLayout()
        startupLay.addWidget(self.miQLabel("Open on Startup:", 182))
        startupLay.addWidget(self.openOnStart)
        optLay1.addLayout(startupLay)

        highSentLay = QHBoxLayout()
        highSentLay.addWidget(self.miQLabel("Highlight Examples Sentences:", 182))
        highSentLay.addWidget(self.highlightSentence)
        optLay1.addLayout(highSentLay)

        highWordLay = QHBoxLayout()
        highWordLay.addWidget(self.miQLabel("Highlight Searched Term:", 182))
        highWordLay.addWidget(self.highlightTarget)
        optLay1.addLayout(highWordLay)

        expTargetLay = QHBoxLayout()
        expTargetLay.addWidget(self.miQLabel("Show Export Target:", 182))
        expTargetLay.addWidget(self.showTarget)
        optLay1.addLayout(expTargetLay)

        toolTipLay = QHBoxLayout()
        toolTipLay.addWidget(self.miQLabel("Dictionary Tooltips:", 182))
        toolTipLay.addWidget(self.tooltipCB)
        optLay1.addLayout(toolTipLay)

        gHLay = QHBoxLayout()
        gHLay.addWidget(self.miQLabel("Global Hotkeys:", 182))
        gHLay.addWidget(self.globalHotkeys)
        optLay1.addLayout(gHLay)

        disableCondensedLay = QHBoxLayout()
        disableCondensedLay.addWidget(
            self.miQLabel("Disable Condensed Audio Messages:", 182)
        )
        disableCondensedLay.addWidget(self.disableCondensedMessages)
        optLay1.addLayout(disableCondensedLay)

        globalOpenLay = QHBoxLayout()
        globalOpenLay.addWidget(self.miQLabel("Open on Global Search:", 323))
        globalOpenLay.addWidget(self.globalOpen)
        optLay2.addLayout(globalOpenLay)

        totResLay = QHBoxLayout()
        totResLay.addWidget(self.miQLabel("Max Total Search Results:", 180))
        totResLay.addWidget(self.totalDefs)
        self.totalDefs.setFixedWidth(160)
        optLay2.addLayout(totResLay)

        dictResLay = QHBoxLayout()
        dictResLay.addWidget(self.miQLabel("Max Dictionary Search Results:", 180))
        dictResLay.addWidget(self.dictDefs)
        self.dictDefs.setFixedWidth(160)
        optLay2.addLayout(dictResLay)

        countryLay = QHBoxLayout()
        countryLay.addWidget(self.miQLabel("Image Search Region:", 180))
        countryLay.addWidget(self.imageSearchCountry)
        self.imageSearchCountry.setFixedWidth(160)
        optLay2.addLayout(countryLay)

        optLay2.addStretch()

        maxWidLay = QHBoxLayout()
        maxWidLay.addWidget(self.miQLabel("Maximum Image Width:", 140))
        maxWidLay.addWidget(self.maxImgWidth)
        optLay3.addLayout(maxWidLay)

        maxHeiLay = QHBoxLayout()
        maxHeiLay.addWidget(self.miQLabel("Maximum Image Height:", 140))
        maxHeiLay.addWidget(self.maxImgHeight)
        optLay3.addLayout(maxHeiLay)

        frontBracketLay = QHBoxLayout()
        frontBracketLay.addWidget(self.miQLabel("Surround Term (Front):", 140))
        frontBracketLay.addWidget(self.frontBracket)
        optLay3.addLayout(frontBracketLay)

        backBracketLay = QHBoxLayout()
        backBracketLay.addWidget(self.miQLabel("Surround Term (Back):", 140))
        backBracketLay.addWidget(self.backBracket)
        optLay3.addLayout(backBracketLay)

        dictOnTopLay = QHBoxLayout()
        dictOnTopLay.addWidget(self.miQLabel("Always on Top:", 323))
        dictOnTopLay.addWidget(self.dictOnTop)
        optLay3.addLayout(dictOnTopLay)

        extensionAudioLay = QHBoxLayout()
        extensionAudioLay.addWidget(self.condensedAudioDirectoryLabel)
        self.chooseAudioDirectory.setFixedWidth(100)
        extensionAudioLay.addWidget(self.chooseAudioDirectory)
        optLay3.addLayout(extensionAudioLay)

        optLay3.addStretch()

        optionsLayout.addLayout(optLay1)
        optionsLayout.addStretch()
        optionsLayout.addWidget(self.getLineSeparator())
        optionsLayout.addStretch()
        optionsLayout.addLayout(optLay2)
        optionsLayout.addStretch()
        optionsLayout.addWidget(self.getLineSeparator())
        optionsLayout.addStretch()
        optionsLayout.addLayout(optLay3)

        optionsBox.setLayout(optionsLayout)
        self.layout.addWidget(optionsBox)
        self.layout.addStretch()

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
            "Configure an OpenAI-compatible LLM API to get AI-generated definitions."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        formGroup = QGroupBox("LLM Configuration")
        formLayout = QFormLayout()

        formLayout.addRow("Enable LLM Dictionary:", self.llmEnabled)
        formLayout.addRow("API Key:", self.llmApiKey)
        formLayout.addRow("Base URL:", self.llmBaseUrl)
        formLayout.addRow("Model:", self.llmModel)
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

    def testLLM(self):
        """Test the LLM API configuration."""
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
