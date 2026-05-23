from __future__ import annotations

from aqt.qt import QTreeWidgetItem, Qt

from ...utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class TreeManager:
    def __init__(self, mw, parent):
        self.mw = mw
        self.parent = parent

    def reload_tree_widget(self):
        db = self.mw.miDictDB
        dict_tree = self.parent.dict_tree

        langs = db.getCurrentDbLangs()
        dicts_by_langs = {}

        for info in db.getAllDictsWithLang():
            lang = info["lang"]
            dict_list = dicts_by_langs.get(lang, [])
            dict_list.append(info["dict"])
            dicts_by_langs[lang] = dict_list

        dict_tree.clear()

        for lang in langs:
            lang_item = QTreeWidgetItem([lang])
            lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang)
            lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)

            dict_tree.addTopLevelItem(lang_item)

            for d in dicts_by_langs.get(lang, []):
                dict_name = db.cleanDictName(d)
                dict_name = dict_name.replace("_", " ")
                dict_item = QTreeWidgetItem([dict_name])
                dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang)
                dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, d)
                lang_item.addChild(dict_item)

            lang_item.setExpanded(True)

    def on_current_item_change(self, new_sel, old_sel):
        lang, dict_ = self.get_current_lang_dict()

        self.parent.lang_grp.setEnabled(lang is not None)
        self.parent.dict_grp.setEnabled(dict_ is not None)

    def get_current_lang_dict(self):
        curr_item = self.parent.dict_tree.currentItem()

        lang = None
        dict_ = None

        if curr_item:
            lang = curr_item.data(0, Qt.ItemDataRole.UserRole + 0)
            dict_ = curr_item.data(0, Qt.ItemDataRole.UserRole + 1)

        return lang, dict_

    def get_current_lang_item(self):
        curr_item = self.parent.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent:
                return curr_item_parent

        return curr_item

    def get_current_dict_item(self):
        curr_item = self.parent.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent is None:
                return None

        return curr_item
