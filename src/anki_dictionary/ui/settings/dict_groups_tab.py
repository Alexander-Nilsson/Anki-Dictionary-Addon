# -*- coding: utf-8 -*-
#
#
from __future__ import annotations

from typing import Any, Callable, List

from aqt.qt import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from anki.utils import is_mac, is_lin, is_win
from .dict_groups import DictGroupEditor
from ...utils.common import miAsk
from ...utils.config import save_addon_config


class DictionaryGroupsTab:
    def __init__(
        self,
        mw: Any,
        parent: Any,
        get_config_callback: Callable[[], dict],
        get_dictionary_names_callback: Callable[[], List[str]],
    ) -> None:
        self.mw = mw
        self.parent = parent
        self.getConfig = get_config_callback
        self.getDictionaryNames = get_dictionary_names_callback
        self.add_button = QPushButton("Add Dictionary Group")
        self.table = self.getGroupTemplateTable()

    def getGroupTemplateTable(self) -> QTableWidget:
        macLin = bool(is_mac or is_lin)
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
        self.table.setRowCount(0)
        dictGroups = self.getConfig()["DictionaryGroups"]
        for groupName in dictGroups:
            rc = self.table.rowCount()
            self.table.setRowCount(rc + 1)
            self.table.setItem(rc, 0, QTableWidgetItem(groupName))
            editButton = QPushButton("Edit")
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editGroupRow(rc))
            self.table.setCellWidget(rc, 1, editButton)
            deleteButton = QPushButton("X")
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.clicked.connect(self.removeGroupRow(rc))
            self.table.setCellWidget(rc, 2, deleteButton)

    def removeGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.removeGroup(x)

    def editGroupRow(self, x: int) -> Callable[[], None]:
        return lambda: self.editGroup(x)

    def editGroup(self, row: int) -> None:
        groupName = self.table.item(row, 0).text()
        dictGroups = self.getConfig()["DictionaryGroups"]
        if groupName in dictGroups:
            group = dictGroups[groupName]
            dictEditor = DictGroupEditor(
                self.mw, self.parent, self.getDictionaryNames(), group, groupName
            )
            dictEditor.exec()

    def removeGroup(self, row: int) -> None:
        if miAsk(
            "Are you sure you would like to remove this dictionary group? This action will happen immediately and is not un-doable.",
            self.parent,
        ):
            newConfig = self.getConfig()
            dictGroups = newConfig["DictionaryGroups"]
            groupName = self.table.item(row, 0).text()
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
            "Add a new dictionary group.\nDictionary groups allow you to specify which dictionaries to search\nwithin. You can also set a specific font for that group."
        )
