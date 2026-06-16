# -*- coding: utf-8 -*-
#
#
from __future__ import annotations

import re
from os.path import dirname, join
from typing import Any, Callable, Dict, List, Optional

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QEvent,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QIcon,
    QKeySequence,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSpinBox,
    QTabWidget,
    QUrl,
    QVBoxLayout,
    QWidget,
    Qt,
)
from anki.utils import is_mac, is_win, is_lin
from .llm_settings_tab import LLMSettingsTab
from .forvo_settings_tab import ForvoSettingsTab
from .frequency_settings_tab import FrequencySettingsTab
from .dict_groups_tab import DictionaryGroupsTab
from .export_templates_tab import ExportTemplatesTab
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

        self.dictGroupsTab = DictionaryGroupsTab(
            mw, self, self.getConfig, self.getDictionaryNames
        )
        self.exportTemplatesTab = ExportTemplatesTab(
            mw, self, self.getConfig, self.getDictionaryNames
        )
        self.addDictGroup = self.dictGroupsTab.add_button
        self.addExportTemplate = self.exportTemplatesTab.add_button
        self.dictGroups = self.dictGroupsTab.table
        self.exportTemplates = self.exportTemplatesTab.table
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
        self.layout = QVBoxLayout()  # ty:ignore[invalid-assignment]
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

    def hideEvent(self, event: QEvent) -> None:  # ty:ignore[invalid-method-override]
        self.mw.dictSettings = None
        event.accept()

    def closeEvent(self, event: QEvent) -> None:  # ty:ignore[invalid-method-override]
        self.mw.dictSettings = None
        event.accept()

    def initTooltips(self) -> None:
        self.dictGroupsTab.init_tooltips()
        self.exportTemplatesTab.init_tooltips()
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

    def loadGroupTable(self) -> None:
        self.dictGroupsTab.loadGroupTable()

    def loadTemplateTable(self) -> None:
        self.exportTemplatesTab.loadTemplateTable()

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
        self.addDictGroup.clicked.connect(self.dictGroupsTab.addGroup)
        self.addExportTemplate.clicked.connect(self.exportTemplatesTab.addTemplate)
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
        self.layout.addLayout(groupLayout)  # ty:ignore[unresolved-attribute]

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

        self.layout.addLayout(optionsLayout)  # ty:ignore[unresolved-attribute]
        self.layout.addStretch()  # ty:ignore[unresolved-attribute]

        # 3. Bottom Buttons
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.restoreButton)
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.cancelButton)
        buttonsLayout.addWidget(self.applyButton)

        self.layout.addLayout(buttonsLayout)  # ty:ignore[unresolved-attribute]
        self.settingsTab.setLayout(self.layout)  # ty:ignore[invalid-argument-type]

    def cleanDictName(self, name: str) -> str:
        return re.sub(r"l\d+name", "", name)

    def getHTML(self) -> tuple:
        htmlPath = join(self.addonPath, "guide.html")
        url = QUrl.fromLocalFile(htmlPath)
        with open(htmlPath, "r", encoding="utf-8") as fh:
            html = fh.read()
        return html, url
