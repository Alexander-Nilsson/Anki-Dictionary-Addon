#

import re
from os.path import join

from anki import sound
from anki.notes import Note
from anki.utils import is_mac
from aqt import dialogs
from aqt.qt import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QComboBox,
    QFont,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QKeySequence,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSpinBox,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTextCharFormat,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import ensureWidgetInScreenBoundaries

from ..utils.common import miAsk, miInfo
from ..utils.config import get_addon_config
from ..utils.logger import get_logger
from . import note_creator
from .bulk_processor import BulkProcessor
from .html_cleaner import HtmlCleaner
from .media_transfer import MediaTransfer
from .note_assembler import NoteAssembler

logger = get_logger(__name__.split(".")[-1])


class MITextEdit(QTextEdit):
    def __init__(self, parent=None, dictInt=None):
        super().__init__(parent)
        self.dictInt = dictInt
        self.setAcceptRichText(False)

    def contextMenuEvent(self, event):  # ty:ignore[invalid-method-override]
        menu = super().createStandardContextMenu()
        search = QAction("Search")
        search.triggered.connect(self.searchSelected)
        menu.addAction(search)  # ty:ignore[unresolved-attribute]
        menu.exec_(event.globalPos())  # ty:ignore[unresolved-attribute]

    def keyPressEvent(self, event):  # ty:ignore[invalid-method-override]
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_B:
                cursor = self.textCursor()
                format = QTextCharFormat()
                format.setFontWeight(
                    QFont.Bold  # ty:ignore[unresolved-attribute]
                    if not cursor.charFormat().font().bold()
                    else QFont.Normal  # ty:ignore[unresolved-attribute]
                )
                cursor.mergeCharFormat(format)
                return
            elif event.key() == Qt.Key.Key_I:
                cursor = self.textCursor()
                format = QTextCharFormat()
                format.setFontItalic(
                    True if not cursor.charFormat().font().italic() else False
                )
                cursor.mergeCharFormat(format)
                return
            elif event.key() == Qt.Key.Key_U:
                cursor = self.textCursor()
                format = QTextCharFormat()
                format.setUnderlineStyle(
                    QTextCharFormat.SingleUnderline  # ty:ignore[unresolved-attribute]
                    if not cursor.charFormat().font().underline()
                    else QTextCharFormat.NoUnderline  # ty:ignore[unresolved-attribute]
                )
                cursor.mergeCharFormat(format)
                return
        QTextEdit.keyPressEvent(self, event)

    def searchSelected(self, in_browser):
        if in_browser:
            b = dialogs.open("Browser", self.dictInt.mw)  # ty:ignore[unresolved-attribute]
            b.form.searchEdit.lineEdit().setText(f"expression:*{self.selectedText()}*")
            b.onSearchActivated()
        else:
            self.dictInt.initSearch(self.selectedText())  # ty:ignore[unresolved-attribute]

    def selectedText(self):
        return self.textCursor().selectedText()


class MILineEdit(QLineEdit):
    def __init__(self, parent=None, dictInt=None):
        super().__init__(parent)
        self.dictInt = dictInt

    def contextMenuEvent(self, event):  # ty:ignore[invalid-method-override]
        menu = super().createStandardContextMenu()
        search = QAction("Search")
        search.triggered.connect(self.searchSelected)
        menu.addAction(search)  # ty:ignore[unresolved-attribute]
        menu.exec_(event.globalPos())  # ty:ignore[unresolved-attribute]

    def searchSelected(self, in_browser):
        if in_browser:
            b = dialogs.open("Browser", self.dictInt.mw)  # ty:ignore[unresolved-attribute]
            b.form.searchEdit.lineEdit().setText(f"Expression:*{self.selectedText()}*")
            b.onSearchActivated()
        else:
            self.dictInt.initSearch(self.selectedText())  # ty:ignore[unresolved-attribute]


class CardExporter:
    def __init__(
        self,
        dictInt,
        dictWeb,
        templates=None,
        sentence=False,
        word=False,
        definition=False,
    ):
        if templates is None:
            templates = []
        self.window = QWidget()
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.window)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setWidgetResizable(True)
        self.window.setAutoFillBackground(True)
        self.dictInt = dictInt
        self.mw = self.dictInt.mw
        self.config = self.getConfig()
        self.definitionSettings = self.config["autoDefinitionSettings"]
        self.dictWeb = dictWeb
        self.layout = QVBoxLayout()
        self.decks = self.getDecks()
        self.templates = self.config["ExportTemplates"]
        self.templateCB = self.getTemplateCB()
        self.deckCB = self.getDeckCB()
        self.sentenceLE = MITextEdit(dictInt=dictInt)
        self.secondaryLE = MITextEdit(dictInt=dictInt)
        self.notesLE = MITextEdit(dictInt=dictInt)
        self.wordLE = MILineEdit(dictInt=dictInt)
        self.tagsLE = MILineEdit(dictInt=dictInt)
        self.definitions = self.getDefinitions()
        self.autoAdd = QCheckBox("Add Extension Cards Automatically")
        self.autoAdd.setChecked(self.config["autoAddCards"])
        self.searchUnknowns = QSpinBox()
        self.searchUnknowns.setValue(self.config.get("unknownsToSearch", 3))
        self.searchUnknowns.setMinimum(0)
        self.searchUnknowns.setMaximum(10)
        self.addDefinitionsCheckbox = QCheckBox("Automatically Add Definitions")
        self.addDefinitionsCheckbox.setChecked(self.config["autoAddDefinitions"])
        self.definitionSettingsButton = QPushButton("Automatic Definition Settings")
        self.clearButton = QPushButton("Clear Current Card")
        self.cancelButton = QPushButton("Cancel")
        self.addButton = QPushButton("Add")
        self.exportJS = self.config["jReadingCards"]
        self.imgName = ""
        self.imgPath = ""
        self.audioTag = ""
        self.audioName = ""
        self.audioPath = ""
        self.audioPlayer = sound
        self.audioPlay = QPushButton("Play")
        self.html_cleaner = HtmlCleaner()
        self.note_assembler = NoteAssembler(self.mw, self.html_cleaner)
        self.audioPlay.clicked.connect(self.playAudio)
        self.audioPlay.hide()
        self.setupLayout()
        self.media_transfer = MediaTransfer(
            self.mw, self.imageMap, self.audioMap, self.audioPlay, sound
        )
        self.initHandlers()
        self.setColors()
        self.window.setLayout(self.layout)
        self.window.setMinimumSize(490, 650)
        self.scrollArea.setMinimumWidth(490)
        self.scrollArea.setMinimumHeight(400)
        self.scrollArea.resize(490, 654)
        self.scrollArea.setWindowIcon(
            QIcon(join(self.dictInt.addonPath, "assets", "icons", "anki.svg"))
        )
        self.scrollArea.setWindowTitle("Anki Card Exporter")
        self.definitionList = []
        self.word = ""
        self.sentence = ""
        self.initTooltips()
        self.restoreSizePos()
        self.scrollArea.closeEvent = self.closeEvent  # ty:ignore[invalid-assignment]
        self.scrollArea.hideEvent = self.hideEvent  # ty:ignore[invalid-assignment]
        self.setHotkeys()
        self.scrollArea.show()
        self.alwaysOnTop = self.config["dictAlwaysOnTop"]
        self.bulk_processor = BulkProcessor(self.mw, self.dictInt, self.alwaysOnTop)
        self.maybeSetToAlwaysOnTop()

    def maybeSetToAlwaysOnTop(self):
        if self.alwaysOnTop:
            self.scrollArea.setWindowFlags(
                self.scrollArea.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
            self.scrollArea.show()

    def initTooltips(self):
        if self.config["tooltips"]:
            self.templateCB.setToolTip("Select the export template.")
            self.deckCB.setToolTip("Select the deck to export to.")
            self.clearButton.setToolTip("Clear the card exporter.")

    def restoreSizePos(self):
        sizePos = self.config["exporterSizePos"]
        if sizePos:
            self.scrollArea.resize(sizePos[2], sizePos[3])
            self.scrollArea.move(sizePos[0], sizePos[1])
            ensureWidgetInScreenBoundaries(self.scrollArea)

    def setHotkeys(self):
        self.sentencehotkeyS = QShortcut(
            QKeySequence("Ctrl+S"), self.scrollArea, lambda: self.attemptSearch(False)
        )
        self.sentencehotkeyS = QShortcut(
            QKeySequence("Ctrl+F"), self.scrollArea, lambda: self.attemptSearch(True)
        )
        self.scrollArea.hotkeyEsc = QShortcut(QKeySequence("Esc"), self.scrollArea)  # ty:ignore[unresolved-attribute]
        self.scrollArea.hotkeyEsc.activated.connect(self.scrollArea.hide)  # ty:ignore[unresolved-attribute]

    def attemptSearch(self, in_browser):
        focused = self.scrollArea.focusWidget()
        if type(focused).__name__ in ["MILineEdit", "MITextEdit"]:
            focused.searchSelected(in_browser)  # ty:ignore[unresolved-attribute]

    def setColors(self):
        if is_mac:
            self.templateCB.setStyleSheet(self.dictInt.getMacComboStyle())
            self.deckCB.setStyleSheet(self.dictInt.getMacComboStyle())
            self.definitions.setStyleSheet(self.dictInt.getMacTableStyle())
        else:
            self.templateCB.setStyleSheet("")
            self.deckCB.setStyleSheet("")
            self.definitions.setStyleSheet("")

    def addNote(self, note, did):
        note.note_type()["did"] = int(did)
        ret = note.dupeOrEmpty()
        if ret == 1:
            if not miAsk(
                "Your note's sorting field will be empty with this configuration."
                " Would you like to continue?",
                self.scrollArea,
            ):
                return False
        if "{{cloze:" in note.note_type()["tmpls"][0]["qfmt"]:
            if not self.mw.col.models._availClozeOrds(
                note.model(), note.joinedFields(), False
            ):
                if not miAsk(
                    "You have a cloze deletion note type but have not made any"
                    " cloze deletions. Would you like to continue?",
                    self.scrollArea,
                ):
                    return False
        cards = self.mw.col.addNote(note)
        if not cards:
            miInfo(
                (
                    """\
The current input and template combination \
will lead to a blank card and therefore has not been added. \
Please review your template and notetype combination."""
                ),
                level="wrn",
            )
            return False
        self.mw.reset()
        return True

    def getDecks(self):
        return {name: did for did, name in note_creator.get_decks(self.mw.col)}

    def getDeckCB(self):
        cb = QComboBox()
        decks = list(self.decks.keys())
        decks.sort()
        cb.addItems(decks)
        current = self.config["currentDeck"]
        if current in decks:
            cb.setCurrentText(current)
        cb.currentIndexChanged.connect(
            lambda: self.dictInt.writeConfig("currentDeck", cb.currentText())
        )
        return cb

    def hideEvent(self, event):
        self.saveSizeAndPos()
        event.accept()

    def closeEvent(self, event):
        self.clearCurrent()
        self.saveSizeAndPos()
        event.accept()

    def saveSizeAndPos(self):
        pos = self.scrollArea.pos()
        x = pos.x()
        y = pos.y()
        size = self.scrollArea.size()
        width = size.width()
        height = size.height()
        posSize = [x, y, width, height]
        self.dictInt.writeConfig("exporterSizePos", posSize)
        self.dictInt.writeConfig("exporterLastTags", self.tagsLE.text())

    def initHandlers(self):
        self.definitionSettingsButton.clicked.connect(self.definitionSettingsWidget)
        self.clearButton.clicked.connect(self.clearCurrent)
        self.cancelButton.clicked.connect(self.scrollArea.close)
        self.addButton.clicked.connect(self.addCard)
        self.addDefinitionsCheckbox.clicked.connect(self.saveAddDefinitionChecked)
        self.searchUnknowns.valueChanged.connect(self.saveSearchUnknowns)
        self.autoAdd.clicked.connect(self.saveAutoAddChecked)

    def saveSearchUnknowns(self):
        config = self.getConfig()
        config["unknownsToSearch"] = self.searchUnknowns.value()
        self.config = config
        self.mw.refresh_anki_dict_config(config)
        from anki_dictionary.utils.config import save_addon_config

        save_addon_config(config)

    def saveAutoAddChecked(self):
        config = self.getConfig()
        config["autoAddCards"] = self.autoAdd.isChecked()
        self.config = config
        self.mw.refresh_anki_dict_config(config)
        from anki_dictionary.utils.config import save_addon_config

        save_addon_config(config)

    def saveAddDefinitionChecked(self):
        config = self.getConfig()
        config["autoAddDefinitions"] = self.addDefinitionsCheckbox.isChecked()
        self.config = config
        self.mw.refresh_anki_dict_config(config)
        from anki_dictionary.utils.config import save_addon_config

        save_addon_config(config)

    def addCard(self):
        templateName = self.templateCB.currentText()
        if templateName in self.templates:
            template = self.templates[templateName]
            noteType = template["noteType"]
            model = self.mw.col.models.byName(noteType)
            if model:
                note = Note(self.mw.col, model)
                modelFields = self.mw.col.models.field_names(note.model())  # ty:ignore[unresolved-attribute]
                fieldsValues, imgField, audioField, tagsField = self.getFieldsValues(
                    template
                )
                word = self.wordLE.text()
                if not fieldsValues:
                    miInfo(
                        "The currently selected template and values will lead"
                        " to an invalid card. Please try again.",
                        level="wrn",
                    )
                    return
                for field in fieldsValues:
                    if field in modelFields:
                        note[field] = template["separator"].join(fieldsValues[field])
                note.set_tags_from_str(tagsField)
                did = False
                deck = self.deckCB.currentText()
                if deck in self.decks:
                    did = self.decks[deck]
                if did:
                    if word and self.addDefinitionsCheckbox.isChecked():
                        note = self.automaticallyAddDefinitions(note, word, template)
                    if self.exportJS:
                        note = self.dictInt.jHandler.attemptGenerate(note)
                    if not self.addNote(note, did):
                        return
                if imgField and imgField in modelFields:
                    self.moveImageToMediaFolder()
                if audioField and audioField in modelFields:
                    self.moveAudioToMediaFolder()
                self.clearCurrent()
                return
            else:
                miInfo(
                    "The notetype for the currently selected template does not"
                    " exist in the currently loaded profile.",
                    level="err",
                )
                return
        miInfo(
            "A card could not be added with this current configuration."
            " Please ensure that your template is configured correctly"
            " for this collection.",
            level="err",
        )

    # --- Field mapping methods delegated to NoteAssembler ---

    def fieldValid(self, field):
        return self.note_assembler.field_valid(field)

    def emptyValueIfEmptyHtml(self, value):
        return self.note_assembler.empty_value_if_empty_html(value)

    def getDictionaryEntries(self, dictionary):
        return self.note_assembler.get_dictionary_entries(
            self.definitionList, dictionary
        )

    def getDictionaryNameToTableNameDictionary(self):
        return self.note_assembler.get_dictionary_name_to_table_name_dictionary()

    def getFieldsValues(self, t):
        return self.note_assembler.assemble_field_values(
            t,
            self.sentenceLE.toHtml(),
            self.secondaryLE.toHtml(),
            self.notesLE.toHtml(),
            self.wordLE.text(),
            self.tagsLE.text(),
            self.definitionList,
            self.imgName,
            self.audioTag,
            self.imageMap.text(),
            self.audioMap.text(),
        )

    def getFieldsValuesForTextCard(self, t, wordText, sentenceText):
        return self.note_assembler.assemble_for_text_card(
            t, wordText, sentenceText, self.tagsLE.text()
        )

    def getFieldsValuesForMediaCard(self, t, wordText, card):
        return self.note_assembler.assemble_for_media_card(
            t, wordText, card, self.tagsLE.text()
        )

    def automaticallyAddDefinitions(self, note, word, template):
        return self.note_assembler.auto_add_definitions(
            note, word, template, self.definitionSettings
        )

    def clearCurrent(self):
        self.definitions.setRowCount(0)
        self.sentenceLE.clear()
        self.secondaryLE.clear()
        self.notesLE.clear()
        self.wordLE.clear()
        self.definitionList = []
        self.audioMap.clear()
        self.audioMap.setText("No Audio Selected")
        self.audioPlay.hide()
        self.audioTag = ""
        self.audioName = ""
        self.audioPath = ""
        self.imageMap.clear()
        self.imageMap.setText("No Image Selected")
        self.imgPath = ""
        self.imgName = ""

    def getDefinitions(self):
        definitions = QTableWidget()
        definitions.setMinimumHeight(100)
        definitions.setColumnCount(3)
        tableHeader = definitions.horizontalHeader()
        vHeader = definitions.verticalHeader()
        vHeader.setDefaultSectionSize(50)  # ty:ignore[unresolved-attribute]
        vHeader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        definitions.setColumnWidth(1, 100)
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        definitions.setRowCount(0)
        definitions.setSortingEnabled(False)
        definitions.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        definitions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        definitions.setColumnWidth(2, 40)
        tableHeader.hide()  # ty:ignore[unresolved-attribute]
        return definitions

    def getConfig(self):
        return get_addon_config()

    def setupLayout(self):
        tempLayout = QHBoxLayout()
        tempLayout.addWidget(QLabel("Template: "))
        self.templateCB.setFixedSize(120, 30)
        tempLayout.addWidget(self.templateCB)
        tempLayout.addWidget(QLabel(" Deck: "))
        self.deckCB.setFixedSize(120, 30)
        tempLayout.addWidget(self.deckCB)
        tempLayout.addStretch()
        tempLayout.setSpacing(2)
        self.clearButton.setFixedSize(130, 30)
        tempLayout.addWidget(self.clearButton)
        self.layout.addLayout(tempLayout)
        sentenceL = QLabel("Sentence")
        self.layout.addWidget(sentenceL)
        self.layout.addWidget(self.sentenceLE)
        secondaryL = QLabel("Secondary")
        self.layout.addWidget(secondaryL)
        self.layout.addWidget(self.secondaryLE)
        wordL = QLabel("Word")
        self.layout.addWidget(wordL)
        self.layout.addWidget(self.wordLE)
        notesL = QLabel("User Notes")
        self.layout.addWidget(notesL)
        self.layout.addWidget(self.notesLE)

        self.sentenceLE.setMinimumHeight(60)
        self.secondaryLE.setMinimumHeight(60)
        self.notesLE.setMinimumHeight(90)
        self.sentenceLE.setMaximumHeight(120)
        self.secondaryLE.setMaximumHeight(120)
        f = self.sentenceLE.font()
        f.setPointSize(16)
        self.sentenceLE.setFont(f)
        self.secondaryLE.setFont(f)
        self.notesLE.setFont(f)
        f = self.wordLE.font()
        f.setPointSize(20)
        self.wordLE.setFont(f)

        self.wordLE.setFixedHeight(40)
        definitionsL = QLabel("Definitions")
        self.layout.addWidget(definitionsL)
        self.layout.addWidget(self.definitions)

        self.layout.addWidget(QLabel("Audio"))
        self.audioMap = QLabel("No Audio Selected")
        self.layout.addWidget(self.audioMap)
        self.layout.addWidget(self.audioPlay)
        self.layout.addWidget(QLabel("Image"))
        self.imageMap = QLabel("No Image Selected")
        self.layout.addWidget(self.imageMap)
        tagsL = QLabel("Tags")
        self.layout.addWidget(tagsL)
        lastTags = self.config.get("exporterLastTags", "")
        self.tagsLE.setText(lastTags)
        self.layout.addWidget(self.tagsLE)

        unknownLayout = QHBoxLayout()
        unknownLayout.addWidget(QLabel("Number of unknown words to search: "))
        unknownLayout.addStretch()
        unknownLayout.addWidget(self.searchUnknowns)
        self.layout.addLayout(unknownLayout)

        autoDefLayout = QHBoxLayout()
        autoDefLayout.addWidget(self.addDefinitionsCheckbox)
        autoDefLayout.addStretch()
        self.definitionSettingsButton.setFixedSize(202, 30)
        autoDefLayout.addWidget(self.definitionSettingsButton)
        self.layout.addLayout(autoDefLayout)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.autoAdd)
        buttonLayout.addStretch()
        self.cancelButton.setFixedSize(100, 30)
        self.addButton.setFixedSize(100, 30)
        buttonLayout.addWidget(self.cancelButton)
        buttonLayout.addWidget(self.addButton)
        self.layout.addLayout(buttonLayout)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)

    def getTemplateCB(self):
        cb = QComboBox()
        cb.addItems(self.templates)
        current = self.config["currentTemplate"]

        cb.currentIndexChanged.connect(
            lambda: self.dictInt.writeConfig("currentTemplate", cb.currentText())
        )
        if current in self.templates:
            cb.setCurrentText(current)
        return cb

    def focusWindow(self):
        self.scrollArea.show()
        if self.scrollArea.windowState() == Qt.WindowState.WindowMinimized:
            self.scrollArea.setWindowState(Qt.WindowState.WindowNoState)
        self.scrollArea.setFocus()
        self.scrollArea.activateWindow()

    def definitionSettingsWidget(self):
        settingsWidget = QWidget(self.scrollArea, Qt.WindowType.Window)
        layout = QVBoxLayout()
        dict1 = QComboBox()
        dict2 = QComboBox()
        dict3 = QComboBox()

        dictToTable = self.getDictionaryNameToTableNameDictionary()
        dictNames = dictToTable.keys()
        dict1.addItems(dictNames)
        dict2.addItems(dictNames)
        dict3.addItems(dictNames)

        dict1Lay = QHBoxLayout()
        dict1Lay.addWidget(QLabel("1st Dictionary:"))
        dict1Lay.addStretch()
        dict1Lay.addWidget(dict1)
        dict2Lay = QHBoxLayout()
        dict2Lay.addWidget(QLabel("2nd Dictionary:"))
        dict2Lay.addStretch()
        dict2Lay.addWidget(dict2)
        dict3Lay = QHBoxLayout()
        dict3Lay.addWidget(QLabel("3rd Dictionary:"))
        dict3Lay.addStretch()
        dict3Lay.addWidget(dict3)

        howMany1 = QSpinBox()
        howMany1.setValue(1)
        howMany1.setMinimum(1)
        howMany1.setMaximum(20)
        hmLay1 = QHBoxLayout()
        hmLay1.addWidget(QLabel("Max Definitions:"))
        hmLay1.addWidget(howMany1)

        howMany2 = QSpinBox()
        howMany2.setValue(1)
        howMany2.setMinimum(1)
        howMany2.setMaximum(20)
        hmLay2 = QHBoxLayout()
        hmLay2.addWidget(QLabel("Max Definitions:"))
        hmLay2.addWidget(howMany2)

        howMany3 = QSpinBox()
        howMany3.setValue(1)
        howMany3.setMinimum(1)
        howMany3.setMaximum(20)
        hmLay3 = QHBoxLayout()
        hmLay3.addWidget(QLabel("Max Definitions:"))
        hmLay3.addWidget(howMany3)

        layout.addLayout(dict1Lay)
        layout.addLayout(hmLay1)
        layout.addLayout(dict2Lay)
        layout.addLayout(hmLay2)
        layout.addLayout(dict3Lay)
        layout.addLayout(hmLay3)

        if self.definitionSettings:
            howManys = [howMany1, howMany2, howMany3]
            dicts = [dict1, dict2, dict3]
            for idx, setting in enumerate(self.definitionSettings):
                dictName = setting["name"]
                if dictName in dictToTable:
                    limit = setting["limit"]
                    dicts[idx].setCurrentText(dictName)
                    howManys[idx].setValue(limit)

        save = QPushButton("Save Settings")
        layout.addWidget(save)
        layout.setContentsMargins(4, 4, 4, 4)
        save.clicked.connect(
            lambda: self.saveDefinitionSettings(
                settingsWidget,
                dict1.currentText(),
                howMany1.value(),
                dict2.currentText(),
                howMany2.value(),
                dict3.currentText(),
                howMany3.value(),
            )
        )
        settingsWidget.setWindowTitle("Definition Settings")
        settingsWidget.setWindowIcon(
            QIcon(join(self.dictInt.addonPath, "assets", "icons", "anki.svg"))
        )
        settingsWidget.setLayout(layout)
        settingsWidget.show()

    def saveDefinitionSettings(
        self, settingsWidget, dict1, limit1, dict2, limit2, dict3, limit3
    ):
        definitionSettings = []
        definitionSettings.append({"name": dict1, "limit": limit1})
        definitionSettings.append({"name": dict2, "limit": limit2})
        definitionSettings.append({"name": dict3, "limit": limit3})
        config = self.getConfig()
        self.definitionSettings = definitionSettings
        config["autoDefinitionSettings"] = definitionSettings
        from anki_dictionary.utils.config import save_addon_config

        save_addon_config(config)
        settingsWidget.close()
        settingsWidget.deleteLater()

    # --- Media handler methods delegated to MediaTransfer ---

    def moveImageToMediaFolder(self):
        self.media_transfer.move_image_to_media_folder(self.imgPath, self.imgName)

    def moveAudioToMediaFolder(self):
        self.media_transfer.move_audio_to_media_folder(self.audioPath, self.audioName)

    def playAudio(self):
        if self.audioPath:
            self.media_transfer.play_audio(self.audioPath)

    def exportImage(self, path, name):
        self.imgName = name
        self.imgPath = path
        self.media_transfer.export_image(path, name)

    def exportAudio(self, path, tag, name):
        self.audioTag = tag
        self.audioName = name
        self.audioPath = path
        self.media_transfer.export_audio(path, tag, name)

    def addImgs(self, word, imgs, thumbs):
        self.focusWindow()
        defEntry = ["Images", False, imgs, imgs]
        if defEntry in self.definitionList:
            miInfo("A card cannot contain duplicate definitions.", level="not")
            return
        self.definitionList.append(defEntry)
        rc = self.definitions.rowCount()
        self.definitions.setRowCount(rc + 1)
        self.definitions.setItem(rc, 0, QTableWidgetItem("Images"))
        self.definitions.setCellWidget(rc, 1, thumbs)
        deleteButton = QPushButton("X")
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(lambda: self.removeImgs(imgs))
        self.definitions.setCellWidget(rc, 2, deleteButton)
        self.definitions.resizeRowsToContents()
        if self.wordLE.text() == "":
            self.wordLE.setText(word)

    def exportWord(self, word):
        self.wordLE.setText(word)

    def removeImgs(self, imgs):
        try:
            row = self.definitions.selectionModel().currentIndex().row()
            self.definitions.removeRow(row)
            self.removeImgFromDefinitionList(imgs)
        except Exception:
            return

    def removeImgFromDefinitionList(self, imgs):
        for idx, entry in enumerate(self.definitionList):
            if entry[0] == "Images" and entry[3] == imgs:
                self.definitionList.pop(idx)
                break

    def addDefinition(self, dictName, word, definition):
        self.focusWindow()
        if len(definition) > 40:
            shortDef = (
                re.sub(r"<br\s*/?>", " ", definition, flags=re.IGNORECASE)[:40] + "..."
            )
        else:
            shortDef = re.sub(r"<br\s*/?>", " ", definition, flags=re.IGNORECASE)
        defEntry = [dictName, shortDef, definition, False]
        if defEntry in self.definitionList:
            miInfo("A card can not contain duplicate definitions.", level="not")
            return
        self.definitionList.append(defEntry)
        rc = self.definitions.rowCount()
        self.definitions.setRowCount(rc + 1)
        self.definitions.setItem(rc, 0, QTableWidgetItem(dictName))
        self.definitions.setItem(rc, 1, QTableWidgetItem(shortDef))
        deleteButton = QPushButton("X")
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(self.removeDefinition)
        self.definitions.setCellWidget(rc, 2, deleteButton)
        self.definitions.resizeRowsToContents()
        if self.wordLE.text() == "":
            self.wordLE.setText(word)

    def exportSentence(self, sentence):
        self.focusWindow()
        self.sentenceLE.setHtml(sentence)

    def exportSecondary(self, secondary):
        self.secondaryLE.setHtml(secondary)

    def removeFromDefinitionList(self, dictName, shortDef):
        for idx, entry in enumerate(self.definitionList):
            if entry[0] == dictName and entry[1] == shortDef:
                self.definitionList.pop(idx)
                break

    def removeDefinition(self):
        try:
            row = self.definitions.selectionModel().currentIndex().row()
            dictName = self.definitions.item(row, 0).text()
            shortDef = self.definitions.item(row, 1).text()
            self.definitions.removeRow(row)
            self.removeFromDefinitionList(dictName, shortDef)
        except Exception:
            return

    # --- Batch processing methods ---

    def attemptAutoAdd(self, bulkExport):
        if self.autoAdd.isChecked() or bulkExport:
            self.addCard()

    def addTextCard(self, card):
        templateName = self.templateCB.currentText()
        sentence = card["primary"]
        word = ""
        unknowns = card["unknowns"]
        if len(unknowns) > 0:
            word = unknowns[0]

        if templateName in self.templates:
            template = self.templates[templateName]
            noteType = template["noteType"]
            model = self.mw.col.models.byName(noteType)
            if model:
                note = Note(self.mw.col, model)
                modelFields = self.mw.col.models.field_names(note.model())  # ty:ignore[unresolved-attribute]
                fieldsValues, tagsField = self.getFieldsValuesForTextCard(
                    template, word, sentence
                )
                if fieldsValues:
                    for field in fieldsValues:
                        if field in modelFields:
                            note[field] = template["separator"].join(
                                fieldsValues[field]
                            )
                    note.set_tags_from_str(tagsField)
                    did = False
                    deck = self.deckCB.currentText()
                    if deck in self.decks:
                        did = self.decks[deck]
                    if did:
                        if word and self.addDefinitionsCheckbox.isChecked():
                            note = self.automaticallyAddDefinitions(
                                note, word, template
                            )
                        if self.exportJS:
                            note = self.dictInt.jHandler.attemptGenerate(note)
                        note.model()["did"] = int(did)  # ty:ignore[unresolved-attribute]
                        self.mw.col.addNote(note)
                else:
                    logger.error("Invalid field values")

    def addMediaCard(self, card):
        templateName = self.templateCB.currentText()
        word = ""
        unknowns = card["unknownWords"]
        if len(unknowns) > 0:
            word = unknowns[0]
        if templateName in self.templates:
            template = self.templates[templateName]
            noteType = template["noteType"]
            model = self.mw.col.models.byName(noteType)
            if model:
                note = Note(self.mw.col, model)
                modelFields = self.mw.col.models.field_names(note.model())  # ty:ignore[unresolved-attribute]
                fieldsValues, tagsField = self.getFieldsValuesForMediaCard(
                    template, word, card
                )
                if fieldsValues:
                    for field in fieldsValues:
                        logger.debug(f"Fields values: {fieldsValues}")
                        logger.debug(f"Processing field: {field}")
                        if field in modelFields:
                            note[field] = template["separator"].join(
                                fieldsValues[field]
                            )
                    note.set_tags_from_str(tagsField)
                    did = False
                    deck = self.deckCB.currentText()
                    if deck in self.decks:
                        did = self.decks[deck]
                    if did:
                        if word and self.addDefinitionsCheckbox.isChecked():
                            note = self.automaticallyAddDefinitions(
                                note, word, template
                            )
                        if self.exportJS:
                            note = self.dictInt.jHandler.attemptGenerate(note)
                        note.model()["did"] = int(did)  # ty:ignore[unresolved-attribute]
                        self.mw.col.addNote(note)
                else:
                    logger.error("Invalid field values")

    def bulkTextExport(self, cards):
        self.bulk_processor.bulk_text_export(cards, self.addTextCard)

    def bulkMediaExport(self, card):
        self.bulk_processor.bulk_media_export(card, self.addMediaCard)

    def bulkMediaExportCancelledByBrowserRefresh(self):
        self.bulk_processor.cancel_media_export()

    def getProgressBar(self, title, initialText):
        return self.bulk_processor._get_progress_bar(title, initialText)

    def closeProgressBar(self, progressBar):
        self.bulk_processor._close_progress_bar(progressBar)
