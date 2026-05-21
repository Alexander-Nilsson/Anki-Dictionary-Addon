# -*- coding: utf-8 -*-
#
#
from __future__ import annotations

import re
import os
from os.path import dirname, join
from typing import Any, Callable, Dict, List, Optional

from aqt.qt import *
from anki.utils import is_mac, is_win, is_lin
from .dict_groups import DictGroupEditor
from .templates import TemplateEditor
from .llm_settings_tab import LLMSettingsTab
from .forvo_settings_tab import ForvoSettingsTab
from .frequency_settings_tab import FrequencySettingsTab
from ...utils.common import miInfo, miAsk
from ..dialogs.dictionary_manager import DictionaryManagerWidget
from ...utils.config import get_addon_config, save_addon_config
from ...utils.constants import COUNTRY_LIST

verNumber = "0.1"


class SettingsGui(QTabWidget):
    def __init__(self, mw: Any, path: str, reboot: Callable[[], None]) -> None:
        super(SettingsGui, self).__init__()
        self.mw = mw
        self.reboot = reboot
        self.addonPath = path
        self.imageSearchCountries = COUNTRY_LIST
        self.setMinimumSize(500, 500)
        if not is_win:
            self.resize(1034, 650)
        else:
            self.resize(920, 650)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setWindowTitle("Anki Dictionary Settings (Ver. " + verNumber + ")")
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

        self.restoreButton = QPushButton("Restore Defaults")
        self.cancelButton = QPushButton("Cancel")
        self.applyButton = QPushButton("Apply")
        self.layout = QVBoxLayout()
        self.settingsTab = QWidget()
        self.llmTab = LLMSettingsTab(mw, path, self)
        self.forvoTab = ForvoSettingsTab(mw, path, self)
        self.frequencyTab = FrequencySettingsTab(mw, path, self)

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

    def wrapInScrollArea(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    def hideEvent(self, event: QEvent) -> None:
        self.mw.dictSettings = None
        event.accept()

    def closeEvent(self, event: QEvent) -> None:
        self.mw.dictSettings = None
        event.accept()

    def initTooltips(self) -> None:
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

        self.llmTab.init_tooltips()

    def getConfig(self) -> Dict[str, Any]:
        return get_addon_config()

    def loadConfig(self) -> None:
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

        self.llmTab.load_config(config)
        self.forvoTab.load_config(config)
        self.frequencyTab.load_config(config)

    def saveConfig(self) -> None:
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

        self.llmTab.save_config(nc)
        self.forvoTab.save_config(nc)
        self.frequencyTab.save_config(nc)

        save_addon_config(nc)
        self.hide()

        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(nc)

    def getGroupTemplateTable(self) -> QTableWidget:
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

    def loadGroupTable(self) -> None:
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

    def removeGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.removeGroup(x)

    def editGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.editGroup(x)

    def editGroup(self, row: int) -> None:
        groupName = self.dictGroups.item(row, 0).text()
        dictGroups = self.getConfig()["DictionaryGroups"]
        if groupName in dictGroups:
            group = dictGroups[groupName]
            dictEditor = DictGroupEditor(
                self.mw, self, self.getDictionaryNames(), group, groupName
            )
            dictEditor.exec()

            # dictEditor.exec()

    def removeGroup(self, row: int) -> None:
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

    def loadTemplateTable(self) -> None:
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

    def removeTemplate(self, row: int) -> None:
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

    def removeTempRow(self, x: int) -> Callable[[], None]:
        return lambda: self.removeTemplate(x)

    def editTempRow(self, x: int) -> Callable[[], None]:
        return lambda: self.editTemplate(x)

    def editTemplate(self, row: int) -> None:
        templateName = self.exportTemplates.item(row, 0).text()
        exportTemplates = self.getConfig()["ExportTemplates"]
        if templateName in exportTemplates:
            template = exportTemplates[templateName]
            templateEditor = TemplateEditor(
                self.mw, self, self.getDictionaryNames(), template, templateName
            )
            templateEditor.loadTemplateEditor(template, templateName)
            templateEditor.exec()

    def getDictionaryNames(self) -> List[str]:
        dictList = self.mw.miDictDB.getAllDictsWithLang()
        dictionaryList = []
        for dictionary in dictList:
            dictName = self.cleanDictName(dictionary["dict"]).replace("_", " ")
            if dictName not in dictionaryList:
                dictionaryList.append(dictName)

        if "Images" not in dictionaryList:
            dictionaryList.append("Images")

        if self.llmTab.llmEnabled.isChecked() and "LLM" not in dictionaryList:
            dictionaryList.append("LLM")

        if self.forvoTab.is_enabled() and "Forvo" not in dictionaryList:
            dictionaryList.append("Forvo")

        dictionaryList = sorted(dictionaryList, key=str.casefold)
        return dictionaryList

    def initHandlers(self) -> None:
        self.addDictGroup.clicked.connect(self.addGroup)
        self.addExportTemplate.clicked.connect(self.addTemplate)
        self.restoreButton.clicked.connect(self.restoreDefaults)
        self.cancelButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.saveConfig)

    def restoreDefaults(self) -> None:
        if miAsk(
            "This will remove any export templates and dictionary groups you have created, and is not undoable. Are you sure you would like to restore the default settings?"
        ):
            conf = self.mw.addonManager.addonConfigDefaults(dirname(__file__))
            save_addon_config(conf)
            # self.userGuideTab.close()
            # self.userGuideTab.deleteLater()
            self.close()
            self.reboot()

    def addGroup(self) -> None:
        dictEditor = DictGroupEditor(self.mw, self, self.getDictionaryNames())
        dictEditor.clearGroupEditor(True)
        dictEditor.exec()

    def addTemplate(self) -> None:
        templateEditor = TemplateEditor(self.mw, self, self.getDictionaryNames())
        templateEditor.exec()

    def miQLabel(self, text: str, width: int) -> QLabel:
        label = QLabel(text)
        label.setFixedHeight(30)
        label.setFixedWidth(width)
        return label

    def getLineSeparator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet('QFrame[frameShape="5"]{color: #D5DFE5;}')
        return line

    def setupLayout(self) -> None:
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

    def cleanDictName(self, name: str) -> str:
        return re.sub(r"l\d+name", "", name)

    def getHTML(self) -> tuple:
        htmlPath = join(self.addonPath, "guide.html")
        url = QUrl.fromLocalFile(htmlPath)
        with open(htmlPath, "r", encoding="utf-8") as fh:
            html = fh.read()
        return html, url
