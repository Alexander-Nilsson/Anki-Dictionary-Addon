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

try:
    from aqt.qt import QMenu
except ImportError:
    from PyQt6.QtWidgets import QMenu  # type:ignore[no-redef,unused-ignore]

from ...utils.common import miAsk
from ...utils.config import get_addon_config, save_addon_config
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
        groupTemplates.setColumnCount(4)
        tableHeader = groupTemplates.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # ty:ignore[unresolved-attribute]
        groupTemplates.setRowCount(0)
        groupTemplates.setSortingEnabled(False)
        groupTemplates.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        groupTemplates.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        if macLin:
            groupTemplates.setColumnWidth(2, 50)
            groupTemplates.setColumnWidth(3, 40)
        else:
            groupTemplates.setColumnWidth(2, 40)
            groupTemplates.setColumnWidth(3, 40)
        tableHeader.hide()  # ty:ignore[unresolved-attribute]
        groupTemplates.verticalHeader().hide()  # ty:ignore[unresolved-attribute]
        return groupTemplates

    def _get_langs_for_group(self, group_name: str) -> list[str]:
        config = self.getConfig()
        lang_defaults = config.get("language_defaults", {})
        return [lang for lang, gname in lang_defaults.items() if gname == group_name]

    def _install_langs(self) -> list[str]:
        try:
            if hasattr(self.mw, "miDictDB"):
                return self.mw.miDictDB.getCurrentDbLangs()
        except Exception:
            pass
        return []

    def _lang_button_label(self, langs: list[str]) -> str:
        if not langs:
            return "Lang"
        if len(langs) <= 2:
            return ", ".join(langs)
        return f"{len(langs)} langs"

    def _make_lang_button(self, group_name: str) -> QPushButton:
        current_langs = self._get_langs_for_group(group_name)
        label = self._lang_button_label(current_langs)
        btn = QPushButton(label)
        btn.setMinimumWidth(0)
        text_w = len(label) * 9 + 20
        btn.setFixedWidth(max(text_w, 60))
        btn.setFixedHeight(30)
        tip_langs = ", ".join(current_langs) if current_langs else "(none)"
        btn.setToolTip(
            f"Language defaults: {tip_langs}\n"
            "Click to set which languages this group is the default for.\n"
            "When Auto-Select is enabled, searching text in a language\n"
            "will automatically switch to this group."
        )

        def make_handler(gn: str) -> Callable[[], None]:
            def handler() -> None:
                self._show_lang_menu(btn, gn)

            return handler

        btn.clicked.connect(make_handler(group_name))
        return btn

    def _show_lang_menu(self, button: QPushButton, group_name: str) -> None:
        menu = QMenu(button)
        current_langs = self._get_langs_for_group(group_name)
        installed = self._install_langs()

        for lang in installed:
            action = menu.addAction(lang)
            action.setCheckable(True)  # ty:ignore[unresolved-attribute]
            if lang in current_langs:
                action.setChecked(True)  # ty:ignore[unresolved-attribute]
            action.triggered.connect(  # ty:ignore[unresolved-attribute]
                lambda checked, l=lang: self._toggle_lang_for_group(
                    group_name, l, checked
                )
            )
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))  # ty:ignore[invalid-argument-type]

    def _toggle_lang_for_group(self, group_name: str, lang: str, checked: bool) -> None:
        config = get_addon_config()
        lang_defaults = dict(config.get("language_defaults", {}))

        for k in list(lang_defaults.keys()):
            if lang_defaults[k] == group_name and k == lang:
                if not checked:
                    del lang_defaults[k]
                break
        else:
            if checked:
                lang_defaults[lang] = group_name

        config["language_defaults"] = lang_defaults
        save_addon_config(config)
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(config)
        self.loadGroupTable()

    def loadGroupTable(self) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                widget = self.table.cellWidget(r, c)
                if widget:
                    try:
                        widget.clicked.disconnect()  # ty:ignore[unresolved-attribute]
                    except TypeError:
                        pass
        self.table.setRowCount(0)
        dictGroups = self.getConfig()["DictionaryGroups"]
        for groupName in dictGroups:
            rc = self.table.rowCount()
            self.table.setRowCount(rc + 1)
            self.table.setItem(rc, 0, QTableWidgetItem(groupName))
            langButton = self._make_lang_button(groupName)
            self.table.setCellWidget(rc, 1, langButton)
            editButton = QPushButton("Edit")
            editButton.setMinimumWidth(0)
            if is_win:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editGroupRow(rc))
            self.table.setCellWidget(rc, 2, editButton)
            deleteButton = QPushButton("X")
            deleteButton.setMinimumWidth(0)
            if is_win:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.setToolTip("Remove this group")
            deleteButton.clicked.connect(self.removeGroupRow(rc))
            self.table.setCellWidget(rc, 3, deleteButton)

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

            lang_defaults = dict(newConfig.get("language_defaults", {}))
            for k in list(lang_defaults.keys()):
                if lang_defaults[k] == groupName:
                    del lang_defaults[k]
            newConfig["language_defaults"] = lang_defaults

            save_addon_config(newConfig)
            if hasattr(self.mw, "refreshAnkiDictConfig"):
                self.mw.refreshAnkiDictConfig(newConfig)
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
