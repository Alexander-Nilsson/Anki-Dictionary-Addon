from __future__ import annotations

import json
import os
import shutil

from aqt.qt import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QProgressDialog,
    QTreeWidgetItem,
    Qt,
)

from ...utils.logger import get_logger
from ...utils.paths import get_db_dir, get_frequency_dir
from ...web.installer import DictionaryWebInstallWizard
from ...web.windows import FreqConjWebWindow
from .dict_import import importDict

logger = get_logger(__name__.split(".")[-1])


class DictImporter:
    def __init__(self, mw, parent):
        self.mw = mw
        self.parent = parent

    def web_installer(self):
        DictionaryWebInstallWizard.execute_modal()
        self.parent.tree_manager.reload_tree_widget()
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def web_installer_lang(self):
        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        DictionaryWebInstallWizard.execute_modal(lang_name)
        self.parent.tree_manager.reload_tree_widget()
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def import_dicts(self):
        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        paths, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Select the dictionaries you want to import",
            os.path.expanduser("~"),
            "ZIP Files (*.zip);;All Files (*.*)",
        )
        if not paths:
            return

        use_default_names = (
            QMessageBox.question(
                self.parent,
                "Use Default Names?",
                "Do you want to use default names for the imported dictionaries?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

        progress = QProgressDialog(
            "Importing dictionaries...", "Cancel", 0, len(paths), self.parent
        )
        progress.setWindowTitle("Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)

        for i, path in enumerate(paths):
            if progress.wasCanceled():
                break

            dict_name = os.path.splitext(os.path.basename(path))[0]

            if not use_default_names:
                dict_name, ok = self.parent.get_string(
                    "Set name of dictionary", dict_name
                )
                if not ok:
                    continue

            try:
                final_name = importDict(lang_name, path, dict_name, parent=self.parent)
            except ValueError as e:
                if "Creating dictionary failed" in str(e) and "duplicate" in str(e):
                    progress.setValue(i + 1)
                    continue
                self.parent.info(str(e))
                continue

            dict_item = QTreeWidgetItem([final_name.replace("_", " ")])
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang_name)
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, final_name)

            lang_item.addChild(dict_item)
            progress.setValue(i + 1)

        progress.close()

        if paths:
            self.parent.dict_tree.setCurrentItem(
                lang_item.child(lang_item.childCount() - 1)
            )
            if hasattr(self.mw, "refreshAnkiDictConfig"):
                self.mw.refreshAnkiDictConfig(force=True)

    def set_freq_data(self):
        lang_name = self.parent.tree_manager.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(
            self.parent,
            "Select the frequency or level data you want to import",
            os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*.*)",
        )[0]
        if not path:
            return

        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Data Type")
        msg.setText("What type of data are you importing?")
        btn_main = msg.addButton(
            "Main Frequency List", QMessageBox.ButtonRole.ActionRole
        )
        btn_extra = msg.addButton(
            "Extra Level/HSK List", QMessageBox.ButtonRole.ActionRole
        )
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_main:
            filename = "%s.json" % lang_name
        elif clicked == btn_extra:
            label, ok = QInputDialog.getText(
                self.parent,
                "Label",
                "Enter a label for this data (e.g. HSK, JLPT, CEFR):",
            )
            if not ok or not label:
                return
            filename = "%s_%s.json" % (lang_name, label)
        else:
            return

        freq_path = get_frequency_dir()
        os.makedirs(freq_path, exist_ok=True)

        dst_path = os.path.join(freq_path, filename)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.parent.info("Importing data failed.")
            return

        self.parent.info(
            'Imported data as "%s" for "%s".\n\nNote that some data is only applied to newly imported dictionaries.'
            % (filename, lang_name)
        )

        if hasattr(self.mw, "miDictDB"):
            self.mw.miDictDB._extra_data_cache.pop(lang_name, None)

    def web_freq_data(self):
        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Freq)

    def set_conj_data(self):
        lang_name = self.parent.tree_manager.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(
            self.parent,
            "Select the conjugation data you want to import",
            os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*.*)",
        )[0]
        if not path:
            return

        conj_path = os.path.join(get_db_dir(), "conjugation")
        os.makedirs(conj_path, exist_ok=True)

        dst_path = os.path.join(conj_path, "%s.json" % lang_name)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.parent.info("Importing conjugation data failed.")
            return

        self.parent.info('Imported conjugation data for "%s".' % lang_name)

    def web_conj_data(self):
        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Conj)

    def import_dict(self):
        lang_item = self.parent.tree_manager.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        path = QFileDialog.getOpenFileName(
            self.parent,
            "Select the dictionary you want to import",
            os.path.expanduser("~"),
            "ZIP Files (*.zip);;All Files (*.*)",
        )[0]
        if not path:
            return

        dict_name = os.path.splitext(os.path.basename(path))[0]
        dict_name, ok = self.parent.get_string("Set name of dictionary", dict_name)

        try:
            final_name = importDict(lang_name, path, dict_name, parent=self.parent)
        except ValueError as e:
            self.parent.info(str(e))
            return

        dict_item = QTreeWidgetItem([final_name.replace("_", " ")])
        dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang_name)
        dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, final_name)

        lang_item.addChild(dict_item)
        self.parent.dict_tree.setCurrentItem(dict_item)

        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def set_term_header(self):
        db = self.mw.miDictDB

        dict_name = self.parent.tree_manager.get_current_lang_dict()[1]
        if dict_name is None:
            return

        dict_clean = db.cleanDictName(dict_name)

        term_txt = ", ".join(json.loads(db.getDictTermHeader(dict_clean)))

        term_txt, ok = self.parent.get_string(
            'Set term header for dictionary "%s"' % dict_clean.replace("_", " "),
            term_txt,
        )

        if not ok:
            return

        parts_txt = term_txt.split(",")
        parts = []
        valid_parts = ["term", "altterm", "pronunciation"]

        for part_txt in parts_txt:
            part = part_txt.strip().lower()
            if part not in valid_parts:
                self.parent.info('The term header part "%s" is not valid.' % part_txt)
                return
            parts.append(part)

        db.setDictTermHeader(dict_clean, json.dumps(parts))
