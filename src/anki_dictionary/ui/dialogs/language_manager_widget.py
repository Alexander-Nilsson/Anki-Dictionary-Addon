from __future__ import annotations

import os

import aqt
from aqt.qt import QMessageBox, Qt, QTreeWidgetItem

from ...utils.logger import get_logger
from ...utils.paths import get_db_dir, get_word_lists_dir

logger = get_logger(__name__.split(".")[-1])


class LanguageManager:
    def __init__(self, mw, parent):
        self.mw = mw
        self.parent = parent

    def add_lang(self):
        db = self.mw.miDictDB

        text, ok = self.parent.get_string("Select name of new language")
        if not ok:
            return

        name = text.strip()
        if not name:
            self.parent.info("Language names may not be empty.")
            return

        try:
            db.addLanguages([name])
        except Exception:
            self.parent.info("Adding language failed.")
            return

        lang_item = QTreeWidgetItem([name])
        lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, name)
        lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)

        self.parent.dict_tree.addTopLevelItem(lang_item)
        self.parent.dict_tree.setCurrentItem(lang_item)

    def remove_lang(self):
        db = self.mw.miDictDB

        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Anki Dictionary",
            f'Do you really want to remove the language "{lang_name}"?\n\nAll settings and dictionaries for it will be removed.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self.parent,
        )
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        db.deleteLanguage(lang_name)

        try:
            wl_dir = get_word_lists_dir()
            if os.path.exists(wl_dir):
                for filename in os.listdir(wl_dir):
                    if filename.lower().startswith(lang_name.lower().replace(" ", "_")):
                        os.remove(os.path.join(wl_dir, filename))
        except OSError:
            pass

        try:
            path = os.path.join(get_db_dir(), "conjugation", f"{lang_name}.json")
            os.remove(path)
        except OSError:
            pass

        aqt.qt.sip.delete(lang_item)
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def remove_dict(self):
        db = self.mw.miDictDB

        dict_item = self.parent.tree_manager.get_current_dict_item()
        if dict_item is None:
            return
        dict_name = dict_item.data(0, Qt.ItemDataRole.UserRole + 1)
        dict_display = dict_item.data(0, Qt.ItemDataRole.DisplayRole)

        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Anki Dictionary",
            f'Do you really want to remove the dictionary "{dict_display}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self.parent,
        )
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        db.deleteDict(dict_name)
        aqt.qt.sip.delete(dict_item)
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)
