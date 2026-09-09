"""
Card exporter — thin PyQt shell hosting the Svelte exporter web UI.

Every widget the old Qt window drew (template/deck combos, the sentence,
secondary, word and notes editors, the definitions table, the media rows, the
tags box and the automatic-definition pop-out) now lives in the Svelte app
built into ``exporter.html`` and hosted by :class:`ExporterBridge`. This module
keeps what a web page cannot do: window chrome, note assembly, media transfer
into Anki's collection and the bulk-export paths.

Python stays the source of truth for the card being built. The web UI mirrors
each edit back over ``exporter:setField`` as it is typed, and ships the whole
state with ``exporter:add`` so a card is never assembled from stale values.
"""

import re
from os.path import join

from anki import sound
from anki.notes import Note
from anki.utils import is_mac
from aqt import dialogs
from aqt.qt import (
    QIcon,
    QKeySequence,
    QShortcut,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import ensureWidgetInScreenBoundaries

from ..utils.common import miAsk, miInfo
from ..utils.config import get_addon_config, save_addon_config
from ..utils.logger import get_logger
from . import note_creator
from .bulk_processor import BulkProcessor
from .exporter_bridge import ExporterBridge
from .html_cleaner import HtmlCleaner
from .media_transfer import MediaTransfer
from .note_assembler import NoteAssembler

logger = get_logger(__name__.split(".")[-1])

NO_IMAGE = "No Image Selected"
NO_AUDIO = "No Audio Selected"


class ExporterWindow(QWidget):
    """Frameless-free Qt window whose only child is the exporter web view.

    ``CardExporter`` installs its own ``closeEvent``/``hideEvent`` handlers,
    matching how the previous QScrollArea-based window was wired.
    """


class CardExporter:
    def __init__(
        self,
        dictInt,
        dictWeb,
        _unused_templates=None,
        sentence=False,
        word=False,
        definition=False,
    ):
        self.dictInt = dictInt
        self.mw = self.dictInt.mw
        self.dictWeb = dictWeb
        self.config = self.getConfig()
        self.definitionSettings = self.config["autoDefinitionSettings"]
        self.templates = self.config["ExportTemplates"]
        self.decks = self.getDecks()
        self.exportJS = self.config["jReadingCards"]

        # ── card state (mirrored to/from the web UI) ──────────
        self.template = self._initial_template()
        self.deck = self._initial_deck()
        self.sentence_html = ""
        self.secondary_html = ""
        self.notes_html = ""
        self.word_text = ""
        self.tags_text = self.config.get("exporterLastTags", "")
        self.definitionList = []
        # Parallel to definitionList: `file://` thumbnails for image rows.
        self.definitionThumbs = []
        self.autoAdd = bool(self.config["autoAddCards"])
        self.autoAddDefinitions = bool(self.config["autoAddDefinitions"])
        self.unknownsToSearch = int(self.config.get("unknownsToSearch", 3))

        self.imgName = ""
        self.imgPath = ""
        self.imageLabel = NO_IMAGE
        self.audioTag = ""
        self.audioName = ""
        self.audioPath = ""
        self.audioLabel = NO_AUDIO
        self.audioPlayer = sound

        self.html_cleaner = HtmlCleaner()
        self.note_assembler = NoteAssembler(self.mw, self.html_cleaner)
        self.media_transfer = MediaTransfer(self.mw, sound)

        # ── window ────────────────────────────────────────────
        self.window = ExporterWindow()
        self.bridge = ExporterBridge(
            self, self.dictInt.addonPath, self.dictInt.theme_manager
        )
        layout = QVBoxLayout(self.window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.bridge)
        self.window.setMinimumSize(490, 400)
        self.window.resize(490, 654)
        self.window.setWindowTitle("Anki Card Exporter")
        self.window.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.setColors()
        self.restoreSizePos()
        self.window.closeEvent = self.closeEvent  # ty:ignore[invalid-assignment]
        self.window.hideEvent = self.hideEvent  # ty:ignore[invalid-assignment]
        self.setHotkeys()
        self.window.show()

        self.alwaysOnTop = self.config["dictAlwaysOnTop"]
        self.bulk_processor = BulkProcessor(self.mw, self.dictInt, self.alwaysOnTop)
        self.maybeSetToAlwaysOnTop()

    # ── compatibility shim ────────────────────────────────────

    @property
    def scrollArea(self):
        """The old window attribute — callers still say ``addWindow.scrollArea``."""
        return self.window

    # ── web state ─────────────────────────────────────────────

    def _initial_template(self):
        current = self.config["currentTemplate"]
        names = list(self.templates)
        if current in self.templates:
            return current
        return names[0] if names else ""

    def _initial_deck(self):
        current = self.config["currentDeck"]
        names = sorted(self.decks)
        if current in self.decks:
            return current
        return names[0] if names else ""

    def web_state(self):
        """The full state the Svelte page renders."""
        return {
            "templates": list(self.templates),
            "template": self.template,
            "decks": sorted(self.decks),
            "deck": self.deck,
            "sentence": self.sentence_html,
            "secondary": self.secondary_html,
            "word": self.word_text,
            "notes": self.notes_html,
            "tags": self.tags_text,
            "definitions": self._definition_rows(),
            "imageLabel": self.imageLabel,
            "audioLabel": self.audioLabel,
            "imagePreview": self._file_url(self.imgPath) if self.imgPath else "",
            "autoAdd": self.autoAdd,
            "autoAddDefinitions": self.autoAddDefinitions,
            "unknownsToSearch": self.unknownsToSearch,
            "tooltips": bool(self.config.get("tooltips", True)),
            "dictionaryNames": sorted(self.getDictionaryNameToTableNameDictionary()),
            "definitionSettings": self.definitionSettings or [],
        }

    def _definition_rows(self):
        rows = []
        for idx, entry in enumerate(self.definitionList):
            thumbs = (
                self.definitionThumbs[idx] if idx < len(self.definitionThumbs) else []
            )
            rows.append(
                {
                    "name": entry[0],
                    "short": entry[1] if isinstance(entry[1], str) else "",
                    "thumbs": [self._file_url(p) for p in thumbs],
                }
            )
        return rows

    @staticmethod
    def _file_url(path):
        from urllib.parse import quote
        from urllib.request import pathname2url

        return "file://" + quote(pathname2url(path))

    def pushState(self):
        """Re-render the web UI from Python's state."""
        self.bridge.push_state()

    # Fields the web UI is allowed to write, mapped to the attribute holding
    # them. Anything else in a `setField` payload is ignored.
    _WEB_FIELDS = {
        "template": "template",
        "deck": "deck",
        "sentence": "sentence_html",
        "secondary": "secondary_html",
        "word": "word_text",
        "notes": "notes_html",
        "tags": "tags_text",
        "autoAdd": "autoAdd",
        "autoAddDefinitions": "autoAddDefinitions",
        "unknownsToSearch": "unknownsToSearch",
    }

    def set_web_field(self, field, value):
        """Mirror one edit from the web UI, persisting the ones that are config."""
        attr = self._WEB_FIELDS.get(field)
        if attr is None:
            return
        if field == "unknownsToSearch":
            value = int(value or 0)
        elif field in ("autoAdd", "autoAddDefinitions"):
            value = bool(value)
        else:
            value = "" if value is None else str(value)
        setattr(self, attr, value)

        if field == "template":
            self.dictInt.writeConfig("currentTemplate", value)
        elif field == "deck":
            self.dictInt.writeConfig("currentDeck", value)
        elif field == "autoAdd":
            self._saveConfigValue("autoAddCards", value)
        elif field == "autoAddDefinitions":
            self._saveConfigValue("autoAddDefinitions", value)
        elif field == "unknownsToSearch":
            self._saveConfigValue("unknownsToSearch", value)

    def apply_web_state(self, state):
        """Adopt every field of a state snapshot sent with an add request."""
        if not isinstance(state, dict):
            return
        for field in self._WEB_FIELDS:
            if field in state:
                self.set_web_field(field, state[field])

    def _saveConfigValue(self, key, value):
        config = self.getConfig()
        config[key] = value
        self.config = config
        self.mw.refresh_anki_dict_config(config)
        save_addon_config(config)

    # ── window plumbing ───────────────────────────────────────

    def maybeSetToAlwaysOnTop(self):
        if self.alwaysOnTop:
            self.window.setWindowFlags(
                self.window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
            self.window.show()

    def restoreSizePos(self):
        sizePos = self.config["exporterSizePos"]
        if sizePos:
            self.window.resize(sizePos[2], sizePos[3])
            self.window.move(sizePos[0], sizePos[1])
            ensureWidgetInScreenBoundaries(self.window)

    def setHotkeys(self):
        # Esc is handled inside the page too; the Qt shortcut covers the case
        # where focus sits on the window chrome rather than the web view.
        self.window.hotkeyEsc = QShortcut(QKeySequence("Esc"), self.window)  # ty:ignore[unresolved-attribute]
        self.window.hotkeyEsc.activated.connect(self.window.hide)  # ty:ignore[unresolved-attribute]

    def searchSelected(self, text, in_browser):
        """Look up text selected in the web UI (Ctrl+S / Ctrl+F)."""
        text = (text or "").strip()
        if not text:
            return
        if in_browser:
            b = dialogs.open("Browser", self.dictInt.mw)
            b.form.searchEdit.lineEdit().setText(f"expression:*{text}*")
            b.onSearchActivated()
        else:
            self.dictInt.initSearch(text)

    def setColors(self):
        """Follow the active theme, like the main window and history browser."""
        self.window.setStyleSheet(
            self.dictInt.theme_manager.get_qt_styles(is_mac=is_mac)
        )
        icon = "nightanki.svg" if self.dictInt.theme_manager.is_dark else "anki.svg"
        self.window.setWindowIcon(
            QIcon(join(self.dictInt.addonPath, "assets", "icons", icon))
        )
        self.bridge.repaint_theme()
        self.window.update()

    def hideEvent(self, event):
        self.saveSizeAndPos()
        event.accept()

    def closeEvent(self, event):
        self.clearCurrent()
        self.saveSizeAndPos()
        event.accept()

    def saveSizeAndPos(self):
        pos = self.window.pos()
        size = self.window.size()
        posSize = [pos.x(), pos.y(), size.width(), size.height()]
        self.dictInt.writeConfig("exporterSizePos", posSize)
        self.dictInt.writeConfig("exporterLastTags", self.tags_text)

    def focusWindow(self):
        self.window.show()
        if self.window.windowState() == Qt.WindowState.WindowMinimized:
            self.window.setWindowState(Qt.WindowState.WindowNoState)
        self.window.setFocus()
        self.window.activateWindow()

    def getDecks(self):
        return {name: did for did, name in note_creator.get_decks(self.mw.col)}

    def getConfig(self):
        return get_addon_config()

    # ── note assembly ─────────────────────────────────────────

    def addNote(self, note, did):
        note.note_type()["did"] = int(did)
        ret = note.dupeOrEmpty()
        if ret == 1:
            if not miAsk(
                "Your note's sorting field will be empty with this configuration."
                " Would you like to continue?",
                self.window,
            ):
                return False
        if "{{cloze:" in note.note_type()["tmpls"][0]["qfmt"]:
            if not self.mw.col.models._availClozeOrds(
                note.model(), note.joinedFields(), False
            ):
                if not miAsk(
                    "You have a cloze deletion note type but have not made any"
                    " cloze deletions. Would you like to continue?",
                    self.window,
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

    def addCard(self):
        templateName = self.template
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
                word = self.word_text
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
                if self.deck in self.decks:
                    did = self.decks[self.deck]
                if did:
                    if word and self.autoAddDefinitions:
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
            self.sentence_html,
            self.secondary_html,
            self.notes_html,
            self.word_text,
            self.tags_text,
            self.definitionList,
            self.imgName,
            self.audioTag,
            self.imageLabel,
            self.audioLabel,
        )

    def getFieldsValuesForTextCard(self, t, wordText, sentenceText):
        return self.note_assembler.assemble_for_text_card(
            t, wordText, sentenceText, self.tags_text
        )

    def getFieldsValuesForMediaCard(self, t, wordText, card):
        return self.note_assembler.assemble_for_media_card(
            t, wordText, card, self.tags_text
        )

    def automaticallyAddDefinitions(self, note, word, template):
        return self.note_assembler.auto_add_definitions(
            note, word, template, self.definitionSettings
        )

    def clearCurrent(self):
        self.sentence_html = ""
        self.secondary_html = ""
        self.notes_html = ""
        self.word_text = ""
        self.definitionList = []
        self.definitionThumbs = []
        self.audioLabel = NO_AUDIO
        self.audioTag = ""
        self.audioName = ""
        self.audioPath = ""
        self.imageLabel = NO_IMAGE
        self.imgPath = ""
        self.imgName = ""
        self.pushState()

    # ── automatic definition settings ─────────────────────────

    def saveDefinitionSettings(self, rows):
        """Persist the modal's three dictionary/limit pairs."""
        settings = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            settings.append(
                {"name": str(row.get("name", "")), "limit": int(row.get("limit", 1))}
            )
        self.definitionSettings = settings
        config = self.getConfig()
        config["autoDefinitionSettings"] = settings
        self.config = config
        save_addon_config(config)
        self.pushState()

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
        self.imageLabel = name
        self.pushState()

    def exportAudio(self, path, tag, name):
        self.audioTag = tag
        self.audioName = name
        self.audioPath = path
        self.audioLabel = tag
        self.pushState()

    def exportWord(self, word):
        self.word_text = word
        self.pushState()

    def exportSentence(self, sentence):
        self.focusWindow()
        self.sentence_html = sentence
        self.pushState()

    def exportSecondary(self, secondary):
        self.secondary_html = secondary
        self.pushState()

    # ── definitions ───────────────────────────────────────────

    def addImgs(self, word, imgs, thumbs=None):
        """Attach an image definition. `thumbs` are local paths to preview."""
        self.focusWindow()
        defEntry = ["Images", False, imgs, imgs]
        if defEntry in self.definitionList:
            miInfo("A card cannot contain duplicate definitions.", level="not")
            return
        self.definitionList.append(defEntry)
        self.definitionThumbs.append(list(thumbs or []))
        if self.word_text == "":
            self.word_text = word
        self.pushState()

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
        self.definitionThumbs.append([])
        if self.word_text == "":
            self.word_text = word
        self.pushState()

    def removeDefinitionAt(self, index):
        """Drop the definition the web UI's row X button points at."""
        if 0 <= index < len(self.definitionList):
            self.definitionList.pop(index)
            if index < len(self.definitionThumbs):
                self.definitionThumbs.pop(index)
        self.pushState()

    # ── batch processing ──────────────────────────────────────

    def attemptAutoAdd(self, bulkExport):
        if self.autoAdd or bulkExport:
            self.addCard()

    def addTextCard(self, card):
        templateName = self.template
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
                    if self.deck in self.decks:
                        did = self.decks[self.deck]
                    if did:
                        if word and self.autoAddDefinitions:
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
        templateName = self.template
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
                    if self.deck in self.decks:
                        did = self.decks[self.deck]
                    if did:
                        if word and self.autoAddDefinitions:
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
