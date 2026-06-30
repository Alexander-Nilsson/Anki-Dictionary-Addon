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
from .dict_groups import DictGroupEditor


class DictionaryGroupsTab:
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
        self.add_button = QPushButton("Add Dictionary Group")
        self.table = self.getGroupTemplateTable()

    def getGroupTemplateTable(self) -> QTableWidget:
        macLin = (is_mac() if callable(is_mac) else bool(is_mac)) or (
            is_lin() if callable(is_lin) else bool(is_lin)
        )
        groupTemplates = QTableWidget()
        groupTemplates.setColumnCount(3)
        tableHeader = groupTemplates.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
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
        tableHeader.hide()  # ty:ignore[unresolved-attribute]
        groupTemplates.verticalHeader().hide()  # ty:ignore[unresolved-attribute]
        return groupTemplates

    def loadGroupTable(self) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                widget = self.table.cellWidget(r, c)
                if widget:
                    widget.clicked.disconnect()  # ty:ignore[unresolved-attribute]
        self.table.setRowCount(0)
        dictGroups = self.getConfig()["DictionaryGroups"]
        for groupName in dictGroups:
            rc = self.table.rowCount()
            self.table.setRowCount(rc + 1)
            self.table.setItem(rc, 0, QTableWidgetItem(groupName))
            editButton = QPushButton("Edit")
            editButton.setMinimumWidth(0)
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editGroupRow(rc))
            self.table.setCellWidget(rc, 1, editButton)
            deleteButton = QPushButton("X")
            deleteButton.setMinimumWidth(0)
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.setToolTip("Remove this group")
            deleteButton.clicked.connect(self.removeGroupRow(rc))
            self.table.setCellWidget(rc, 2, deleteButton)

    def removeGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.removeGroup(x)

    def editGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.editGroup(x)

    def editGroup(self, row: int) -> None:
        groupName = self.table.item(row, 0).text()  # ty:ignore[unresolved-attribute]
        dictGroups = self.getConfig()["DictionaryGroups"]
        if groupName in dictGroups:
            group = dictGroups[groupName]
            dictEditor = DictGroupEditor(
                self.mw, self.parent, self.getDictionaryNames(), group, groupName
            )
            dictEditor.exec()

    def removeGroup(self, row: int) -> None:
        if miAsk(
            "Are you sure you would like to remove this dictionary group?"
            " This action will happen immediately and is not un-doable.",
            self.parent,
        ):
            newConfig = self.getConfig()
            dictGroups = newConfig["DictionaryGroups"]
            groupName = self.table.item(row, 0).text()  # ty:ignore[unresolved-attribute]
            del dictGroups[groupName]
            save_addon_config(newConfig)
            self.table.removeRow(row)
            self.loadGroupTable()

    def addGroup(self) -> None:
        dictEditor = DictGroupEditor(self.mw, self.parent, self.getDictionaryNames())
        dictEditor.clearGroupEditor(True)
        dictEditor.exec()

    def init_tooltips(self) -> None:
        self.add_button.setToolTip(
            "Add a new dictionary group.\nDictionary groups allow you to"
            " specify which dictionaries to search\nwithin. You can also set"
            " a specific font for that group."
        )
