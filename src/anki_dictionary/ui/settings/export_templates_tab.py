#
#
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from anki.utils import is_lin, is_mac, is_win
from aqt.qt import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from ...utils.common import miAsk
from ...utils.config import save_addon_config
from .templates import TemplateEditor


class ExportTemplatesTab:
    def __init__(
        self,
        mw: Any,
        parent: Any,
        get_config_callback: Callable[[], dict],
        get_dictionary_names_callback: Callable[[], list[str]],
    ) -> None:
        self.mw = mw
        self.parent = parent
        self.getConfig = get_config_callback
        self.getDictionaryNames = get_dictionary_names_callback
        self.add_button = QPushButton("Add Export Template")
        self.table = self._create_table()

    def _create_table(self) -> QTableWidget:
        macLin = (is_mac() if callable(is_mac) else bool(is_mac)) or (
            is_lin() if callable(is_lin) else bool(is_lin)
        )
        table = QTableWidget()
        table.setColumnCount(3)
        tableHeader = table.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        table.setRowCount(0)
        table.setSortingEnabled(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        if macLin:
            table.setColumnWidth(1, 50)
            table.setColumnWidth(2, 40)
        else:
            table.setColumnWidth(1, 40)
            table.setColumnWidth(2, 40)
        tableHeader.hide()  # ty:ignore[unresolved-attribute]
        table.verticalHeader().hide()  # ty:ignore[unresolved-attribute]
        return table

    def loadTemplateTable(self) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                widget = self.table.cellWidget(r, c)
                if widget:
                    widget.clicked.disconnect()  # ty:ignore[unresolved-attribute]
        self.table.setRowCount(0)
        exportTemplates = self.getConfig()["ExportTemplates"]
        for template in exportTemplates:
            rc = self.table.rowCount()
            self.table.setRowCount(rc + 1)
            self.table.setItem(rc, 0, QTableWidgetItem(template))
            editButton = QPushButton("Edit")
            editButton.setMinimumWidth(0)
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editTempRow(rc))
            self.table.setCellWidget(rc, 1, editButton)
            deleteButton = QPushButton("X")
            deleteButton.setMinimumWidth(0)
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.setToolTip("Remove this template")
            deleteButton.clicked.connect(self.removeTempRow(rc))
            self.table.setCellWidget(rc, 2, deleteButton)

    def removeTempRow(self, x: int) -> Callable[[], None]:
        return lambda: self.removeTemplate(x)

    def editTempRow(self, x: int) -> Callable[[], None]:
        return lambda: self.editTemplate(x)

    def editTemplate(self, row: int) -> None:
        templateName = self.table.item(row, 0).text()  # ty:ignore[unresolved-attribute]
        exportTemplates = self.getConfig()["ExportTemplates"]
        if templateName in exportTemplates:
            template = exportTemplates[templateName]
            templateEditor = TemplateEditor(
                self.mw, self.parent, self.getDictionaryNames(), template, templateName
            )
            templateEditor.loadTemplateEditor(template, templateName)
            templateEditor.exec()

    def removeTemplate(self, row: int) -> None:
        if miAsk(
            "Are you sure you would like to remove this template?"
            " This action will happen immediately and is not un-doable.",
            self.parent,
        ):
            newConfig = self.getConfig()
            exportTemplates = newConfig["ExportTemplates"]
            templateName = self.table.item(row, 0).text()  # ty:ignore[unresolved-attribute]
            del exportTemplates[templateName]
            save_addon_config(newConfig)
            self.table.removeRow(row)
            self.loadTemplateTable()

    def addTemplate(self) -> None:
        templateEditor = TemplateEditor(self.mw, self.parent, self.getDictionaryNames())
        templateEditor.exec()

    def init_tooltips(self) -> None:
        self.add_button.setToolTip(
            "Add a new export template.\nExport templates allow you to"
            " specify a note type, and fields where\ntarget sentences, target"
            " words, definitions, and images will be sent to\nwhen using the"
            " Card Exporter to create cards."
        )
