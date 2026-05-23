# -*- coding: utf-8 -*-
from __future__ import annotations

from os.path import join

from aqt.qt import (
    QApplication,
    QIcon,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    Qt,
)
from anki.notes import Note

from ..utils.common import miInfo
from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class BatchProcessor:
    def __init__(self, exporter):
        self.exporter = exporter
        self.bulkTextImporting = False
        self.bulkMediaExportProgressWindow = False

    def attemptAutoAdd(self, bulkExport):
        if self.exporter.autoAdd.isChecked() or bulkExport:
            self.exporter.addCard()

    def addTextCard(self, card):
        templateName = self.exporter.templateCB.currentText()
        sentence = card["primary"]
        word = ""
        unknowns = card["unknowns"]
        if len(unknowns) > 0:
            word = unknowns[0]

        if templateName in self.exporter.templates:
            template = self.exporter.templates[templateName]
            noteType = template["noteType"]
            model = self.exporter.mw.col.models.byName(noteType)
            if model:
                note = Note(self.exporter.mw.col, model)
                modelFields = self.exporter.mw.col.models.field_names(note.model())
                fieldsValues, tagsField = (
                    self.exporter.field_mapper.getFieldsValuesForTextCard(
                        template, word, sentence
                    )
                )
                if fieldsValues:
                    for field in fieldsValues:
                        if field in modelFields:
                            note[field] = template["separator"].join(
                                fieldsValues[field]
                            )
                    note.set_tags_from_str(tagsField)
                    did = False
                    deck = self.exporter.deckCB.currentText()
                    if deck in self.exporter.decks:
                        did = self.exporter.decks[deck]
                    if did:
                        if word and self.exporter.addDefinitionsCheckbox.isChecked():
                            note = self.exporter.automaticallyAddDefinitions(
                                note, word, template
                            )
                        if self.exporter.exportJS:
                            note = self.exporter.dictInt.jHandler.attemptGenerate(note)
                        note.model()["did"] = int(did)
                        self.exporter.mw.col.addNote(note)
                else:
                    logger.error("Invalid field values")

    def addMediaCard(self, card):
        templateName = self.exporter.templateCB.currentText()
        word = ""
        unknowns = card["unknownWords"]
        if len(unknowns) > 0:
            word = unknowns[0]
        if templateName in self.exporter.templates:
            template = self.exporter.templates[templateName]
            noteType = template["noteType"]
            model = self.exporter.mw.col.models.byName(noteType)
            if model:
                note = Note(self.exporter.mw.col, model)
                modelFields = self.exporter.mw.col.models.field_names(note.model())
                fieldsValues, tagsField = (
                    self.exporter.field_mapper.getFieldsValuesForMediaCard(
                        template, word, card
                    )
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
                    deck = self.exporter.deckCB.currentText()
                    if deck in self.exporter.decks:
                        did = self.exporter.decks[deck]
                    if did:
                        if word and self.exporter.addDefinitionsCheckbox.isChecked():
                            note = self.exporter.automaticallyAddDefinitions(
                                note, word, template
                            )
                        if self.exporter.exportJS:
                            note = self.exporter.dictInt.jHandler.attemptGenerate(note)
                        note.model()["did"] = int(did)
                        self.exporter.mw.col.addNote(note)
                else:
                    logger.error("Invalid field values")

    def bulkTextExport(self, cards):
        self.bulkTextImporting = True
        total = len(cards)
        importingMessage = "Importing {} of " + str(total) + " cards."
        progressWidget, bar, textDisplay = self.getProgressBar(
            "Anki Dictionary - Importing Text Cards",
            importingMessage.format(0),
        )
        bar.setMaximum(total)
        for idx, card in enumerate(cards):
            if not self.bulkTextImporting:
                miInfo(
                    "Importing cards from the extension has been cancelled.\n\n{} of {} were added.".format(
                        idx, total
                    )
                )
                return
            self.addTextCard(card)
            bar.setValue(idx + 1)
            textDisplay.setText(importingMessage.format(idx + 1))
            self.exporter.mw.app.processEvents()
        self.bulkTextImporting = False
        self.closeProgressBar(progressWidget)

    def bulkMediaExport(self, card):
        if self.exporter.mw.DictBulkMediaExportWasCancelled:
            return
        if not self.bulkMediaExportProgressWindow:
            total = card["total"]
            importingMessage = "Importing {} of " + str(total) + " cards."
            (
                self.bulkMediaExportProgressWindow,
                self.bulkMediaExportProgressWindow.bar,
                self.bulkMediaExportProgressWindow.textDisplay,
            ) = self.getProgressBar(
                "Anki Dictionary - Importing Media Cards",
                importingMessage.format(0),
            )
            self.bulkMediaExportProgressWindow.bar.setMaximum(total)
            self.bulkMediaExportProgressWindow.currentValue = 0
            self.bulkMediaExportProgressWindow.total = total
        else:
            importingMessage = (
                "Importing {} of "
                + str(self.bulkMediaExportProgressWindow.total)
                + " cards."
            )
        self.addMediaCard(card)
        try:
            if (
                self.exporter.mw.DictBulkMediaExportWasCancelled
                or not self.bulkMediaExportProgressWindow
            ):
                if self.bulkMediaExportProgressWindow:
                    self.closeProgressBar(self.bulkMediaExportProgressWindow)
                return
            self.bulkMediaExportProgressWindow.currentValue += 1
            self.bulkMediaExportProgressWindow.bar.setValue(
                self.bulkMediaExportProgressWindow.currentValue
            )
            self.bulkMediaExportProgressWindow.textDisplay.setText(
                importingMessage.format(self.bulkMediaExportProgressWindow.currentValue)
            )
            self.exporter.mw.app.processEvents()
            if (
                self.bulkMediaExportProgressWindow.currentValue
                == self.bulkMediaExportProgressWindow.total
            ):
                total = self.bulkMediaExportProgressWindow.total
                if total == 1:
                    miInfo("{} card has been imported.".format(total))
                else:
                    miInfo("{} cards have been imported.".format(total))
                self.closeProgressBar(self.bulkMediaExportProgressWindow)
                self.bulkMediaExportProgressWindow = False
        except Exception:
            pass

    def bulkMediaExportCancelledByBrowserRefresh(self):
        if self.bulkMediaExportProgressWindow:
            currentValue = self.bulkMediaExportProgressWindow.currentValue
            miInfo(
                "Importing cards from the extension has been cancelled from within the browser.\n\n {} cards were imported.".format(
                    currentValue
                )
            )
            self.closeProgressBar(self.bulkMediaExportProgressWindow)
            self.bulkMediaExportProgressWindow = False
            self.exporter.mw.DictBulkMediaExportWasCancelled = False

    def getProgressBar(self, title, initialText):
        progressWidget = QWidget()
        progressWidget.closedBecauseFinishedImporting = False

        def closedProgressBar(event):
            if self.bulkTextImporting:
                self.bulkTextImporting = False
            event.accept()
            progressWidget.deleteLater()
            if self.bulkMediaExportProgressWindow:
                currentValue = self.bulkMediaExportProgressWindow.currentValue
                self.bulkMediaExportProgressWindow = False
                if not progressWidget.closedBecauseFinishedImporting:
                    self.exporter.mw.DictBulkMediaExportWasCancelled = True
                    miInfo(
                        "Importing cancelled.\n\n{} cards were imported.".format(
                            currentValue
                        )
                    )

        progressWidget.exporter = self.exporter
        textDisplay = QLabel()
        progressWidget.setWindowIcon(
            QIcon(
                join(
                    self.exporter.dictInt.addonPath,
                    "assets",
                    "icons",
                    "anki.svg",
                )
            )
        )
        progressWidget.setWindowTitle(title)
        textDisplay.setText(initialText)

        bar = QProgressBar(progressWidget)
        layout = QVBoxLayout()
        layout.addWidget(textDisplay)
        layout.addWidget(bar)
        progressWidget.setLayout(layout)
        bar.move(10, 10)
        per = QLabel(bar)
        per.setAlignment(Qt.AlignmentFlag.alignCenter)
        progressWidget.setFixedSize(500, 100)
        progressWidget.setWindowModality(Qt.WindowModality.ApplicationModal)
        if self.exporter.alwaysOnTop:
            progressWidget.setWindowFlags(
                progressWidget.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
        screenGeometry = QApplication.desktop().screenGeometry()
        x = (screenGeometry.width() - progressWidget.width()) / 2
        y = (screenGeometry.height() - progressWidget.height()) / 2
        progressWidget.move(x, y)
        progressWidget.show()
        progressWidget.setFocus()
        progressWidget.closeEvent = closedProgressBar
        self.exporter.mw.app.processEvents()
        return progressWidget, bar, textDisplay

    def closeProgressBar(self, progressBar):
        if progressBar:
            progressBar.closedBecauseFinishedImporting = True
            progressBar.close()
            progressBar.deleteLater()
