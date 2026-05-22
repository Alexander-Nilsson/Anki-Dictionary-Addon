import aqt
import json
import shutil
import os
from aqt.qt import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ...web.installer import DictionaryWebInstallWizard
from ...web.windows import FreqConjWebWindow
from ...utils.paths import get_addon_root, get_db_dir, get_icons_dir, get_hsk_dir, get_frequency_dir
from .dict_import import (
    importDict,
    organizeDictionaryByFrequency,
    getStarCount,
    getFrequencyList,
)


class DictionaryManagerWidget(QWidget):

    def __init__(self, mw, parent=None):
        super(DictionaryManagerWidget, self).__init__(parent)
        self.mw = mw
        lyt = QVBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        lyt.addWidget(splitter)

        left_side = QWidget()
        splitter.addWidget(left_side)
        left_lyt = QVBoxLayout()
        left_side.setLayout(left_lyt)

        self.dict_tree = QTreeWidget()
        self.dict_tree.setHeaderHidden(True)
        self.dict_tree.currentItemChanged.connect(self.on_current_item_change)
        left_lyt.addWidget(self.dict_tree)

        add_lang_btn = QPushButton("Add a Language")
        add_lang_btn.clicked.connect(self.add_lang)
        left_lyt.addWidget(add_lang_btn)

        web_installer_btn = QPushButton("Install Languages in Wizard")
        web_installer_btn.clicked.connect(self.web_installer)
        left_lyt.addWidget(web_installer_btn)

        right_side = QWidget()
        splitter.addWidget(right_side)
        right_lyt = QVBoxLayout()
        right_side.setLayout(right_lyt)

        self.lang_grp = QGroupBox("Language Options")
        right_lyt.addWidget(self.lang_grp)

        lang_lyt = QVBoxLayout()
        self.lang_grp.setLayout(lang_lyt)

        lang_lyt1 = QHBoxLayout()
        lang_lyt2 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt2)
        lang_lyt3 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt3)
        lang_lyt4 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt4)
        lang_lyt5 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt5)
        lang_lyt.addLayout(lang_lyt1)

        remove_lang_btn = QPushButton("Remove Language")
        remove_lang_btn.clicked.connect(self.remove_lang)
        lang_lyt1.addWidget(remove_lang_btn)

        web_installer_lang_btn = QPushButton("Install Dictionary in Wizard")
        web_installer_lang_btn.clicked.connect(self.web_installer_lang)
        lang_lyt2.addWidget(web_installer_lang_btn)

        import_dicts_btn = QPushButton("Install Dictionaries From Files")
        import_dicts_btn.clicked.connect(self.import_dicts)
        lang_lyt2.addWidget(import_dicts_btn)

        web_freq_data_btn = QPushButton("Install Frequency/Level Data in Wizard")
        web_freq_data_btn.clicked.connect(self.web_freq_data)
        lang_lyt3.addWidget(web_freq_data_btn)

        set_freq_data_btn = QPushButton("Install Frequency/Level Data From File")
        set_freq_data_btn.clicked.connect(self.set_freq_data)
        lang_lyt3.addWidget(set_freq_data_btn)

        web_conj_data_btn = QPushButton("Install Conjugation Data in Wizard")
        web_conj_data_btn.clicked.connect(self.web_conj_data)
        lang_lyt4.addWidget(web_conj_data_btn)

        set_conj_data_btn = QPushButton("Install Conjugation Data From File")
        set_conj_data_btn.clicked.connect(self.set_conj_data)
        lang_lyt4.addWidget(set_conj_data_btn)

        lang_lyt1.addStretch()
        lang_lyt2.addStretch()
        lang_lyt3.addStretch()
        lang_lyt4.addStretch()

        self.dict_grp = QGroupBox("Dictionary Options")
        right_lyt.addWidget(self.dict_grp)

        dict_lyt = QHBoxLayout()
        self.dict_grp.setLayout(dict_lyt)

        remove_dict_btn = QPushButton("Remove Dictionary")
        remove_dict_btn.clicked.connect(self.remove_dict)
        dict_lyt.addWidget(remove_dict_btn)

        set_term_headers_btn = QPushButton("Edit Definition Header")
        set_term_headers_btn.clicked.connect(self.set_term_header)
        dict_lyt.addWidget(set_term_headers_btn)

        dict_lyt.addStretch()

        right_lyt.addStretch()

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.reload_tree_widget()

        self.on_current_item_change(None, None)

    def info(self, text):
        dlg = QMessageBox(
            QMessageBox.Icon.Information,
            "Anki Dictionary",
            text,
            QMessageBox.StandardButton.Ok,
            self,
        )
        return dlg.exec()

    def get_string(self, text, default_text=""):
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Anki Dictionary")
        dlg.setLabelText(text + ":")
        dlg.setTextValue(default_text)
        dlg.resize(350, dlg.sizeHint().height())
        ok = dlg.exec()
        txt = dlg.textValue()
        return txt, ok

    def reload_tree_widget(self):
        db = self.mw.miDictDB

        langs = db.getCurrentDbLangs()
        dicts_by_langs = {}

        for info in db.getAllDictsWithLang():
            lang = info["lang"]

            dict_list = dicts_by_langs.get(lang, [])
            dict_list.append(info["dict"])
            dicts_by_langs[lang] = dict_list

        self.dict_tree.clear()

        for lang in langs:
            lang_item = QTreeWidgetItem([lang])
            lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang)
            lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)

            self.dict_tree.addTopLevelItem(lang_item)

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

        self.lang_grp.setEnabled(lang is not None)
        self.dict_grp.setEnabled(dict_ is not None)

    def get_current_lang_dict(self):

        curr_item = self.dict_tree.currentItem()

        lang = None
        dict_ = None

        if curr_item:
            lang = curr_item.data(0, Qt.ItemDataRole.UserRole + 0)
            dict_ = curr_item.data(0, Qt.ItemDataRole.UserRole + 1)

        return lang, dict_

    def get_current_lang_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent:
                return curr_item_parent

        return curr_item

    def get_current_dict_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent is None:
                return None

        return curr_item

    def web_installer(self):

        DictionaryWebInstallWizard.execute_modal()
        self.reload_tree_widget()
        # Refresh dictionary window to show new dictionaries in "All" group
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def add_lang(self):
        db = self.mw.miDictDB

        text, ok = self.get_string("Select name of new language")
        if not ok:
            return

        name = text.strip()
        if not name:
            self.info("Language names may not be empty.")
            return

        try:
            db.addLanguages([name])
        except Exception as e:
            self.info("Adding language failed.")
            return

        lang_item = QTreeWidgetItem([name])
        lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, name)
        lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)

        self.dict_tree.addTopLevelItem(lang_item)
        self.dict_tree.setCurrentItem(lang_item)

    def remove_lang(self):
        db = self.mw.miDictDB

        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Anki Dictionary",
            'Do you really want to remove the language "%s"?\n\nAll settings and dictionaries for it will be removed.'
            % lang_name,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        # Remove language from db
        db.deleteLanguage(lang_name)

        # Remove frequency data
        try:
            freq_dir = get_frequency_dir()
            if os.path.exists(freq_dir):
                for filename in os.listdir(freq_dir):
                    if filename.startswith(lang_name):
                        os.remove(os.path.join(freq_dir, filename))
        except OSError:
            pass

        # Remove conjugation data
        try:
            path = os.path.join(get_db_dir(), "conjugation", "%s.json" % lang_name)
            os.remove(path)
        except OSError:
            pass

        # Remove HSK data (legacy location)
        try:
            path = os.path.join(get_hsk_dir(), "%s.json" % lang_name)
            os.remove(path)
            # Also try language code variants if lang_name is long
            # (e.g. "Chinese Simplified" -> "zh")
            # But for now we just stick to what was likely installed
        except OSError:
            pass

        aqt.qt.sip.delete(lang_item)
        # Refresh dictionary window to remove language's dictionaries
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def set_freq_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(
            self,
            "Select the frequency or level data you want to import",
            os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*.*)",
        )[0]
        if not path:
            return

        # Ask if this is the main frequency list or an extra level list
        msg = QMessageBox(self)
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
            # Ask for a label
            label, ok = QInputDialog.getText(
                self, "Label", "Enter a label for this data (e.g. HSK, JLPT, CEFR):"
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
            self.info("Importing data failed.")
            return

        self.info(
            'Imported data as "%s" for "%s".\n\nNote that some data is only applied to newly imported dictionaries.'
            % (filename, lang_name)
        )

        # Clear database cache to reflect changes
        if hasattr(self.mw, "miDictDB"):
            self.mw.miDictDB._extra_data_cache.pop(lang_name, None)

    def web_freq_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Freq)

    def set_conj_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(
            self,
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
            self.info("Importing conjugation data failed.")
            return

        self.info('Imported conjugation data for "%s".' % lang_name)

    def web_conj_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Conj)

    def import_dict(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        path = QFileDialog.getOpenFileName(
            self,
            "Select the dictionary you want to import",
            os.path.expanduser("~"),
            "ZIP Files (*.zip);;All Files (*.*)",
        )[0]
        if not path:
            return

        dict_name = os.path.splitext(os.path.basename(path))[0]
        dict_name, ok = self.get_string("Set name of dictionary", dict_name)

        try:
            final_name = importDict(lang_name, path, dict_name, parent=self)
        except ValueError as e:
            self.info(str(e))
            return

        dict_item = QTreeWidgetItem([final_name.replace("_", " ")])
        dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang_name)
        dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, final_name)

        lang_item.addChild(dict_item)
        self.dict_tree.setCurrentItem(dict_item)

        # Refresh dictionary window to show new dictionaries in "All" group
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def import_dicts(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select the dictionaries you want to import",
            os.path.expanduser("~"),
            "ZIP Files (*.zip);;All Files (*.*)",
        )
        if not paths:
            return

        use_default_names = (
            QMessageBox.question(
                self,
                "Use Default Names?",
                "Do you want to use default names for the imported dictionaries?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

        progress = QProgressDialog(
            "Importing dictionaries...", "Cancel", 0, len(paths), self
        )
        progress.setWindowTitle("Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)

        batch_response = None  # To store YesToAll / NoToAll if we implement it

        for i, path in enumerate(paths):
            if progress.wasCanceled():
                break

            dict_name = os.path.splitext(os.path.basename(path))[0]

            if not use_default_names:
                dict_name, ok = self.get_string("Set name of dictionary", dict_name)
                if not ok:
                    continue

            try:
                # For batch import, we might want a slightly different duplicate handler
                # but for now we'll use the default which prompts for each.
                final_name = importDict(lang_name, path, dict_name, parent=self)
            except ValueError as e:
                # If the user clicked "No" on overwrite, it raises ValueError
                # We should probably catch "duplicate" specifically if we want to skip silently
                if "Creating dictionary failed" in str(e) and "duplicate" in str(e):
                    # User chose not to overwrite
                    progress.setValue(i + 1)
                    continue
                self.info(str(e))
                continue

            dict_item = QTreeWidgetItem([final_name.replace("_", " ")])
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang_name)
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, final_name)

            lang_item.addChild(dict_item)
            progress.setValue(i + 1)

        progress.close()

        if paths:
            self.dict_tree.setCurrentItem(lang_item.child(lang_item.childCount() - 1))
            # Refresh dictionary window to show new dictionaries in "All" group
            if hasattr(self.mw, "refreshAnkiDictConfig"):
                self.mw.refreshAnkiDictConfig(force=True)

    def web_installer_lang(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        DictionaryWebInstallWizard.execute_modal(lang_name)
        self.reload_tree_widget()
        # Refresh dictionary window to show new dictionaries in "All" group
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def remove_dict(self):
        db = self.mw.miDictDB

        dict_item = self.get_current_dict_item()
        if dict_item is None:
            return
        dict_name = dict_item.data(0, Qt.ItemDataRole.UserRole + 1)
        dict_display = dict_item.data(0, Qt.ItemDataRole.DisplayRole)

        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Anki Dictionary",
            'Do you really want to remove the dictionary "%s"?' % dict_display,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        db.deleteDict(dict_name)
        aqt.qt.sip.delete(dict_item)
        # Refresh dictionary window to remove dictionary from "All" group
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            self.mw.refreshAnkiDictConfig(force=True)

    def set_term_header(self):
        db = self.mw.miDictDB

        dict_name = self.get_current_lang_dict()[1]
        if dict_name is None:
            return

        dict_clean = db.cleanDictName(dict_name)

        term_txt = ", ".join(json.loads(db.getDictTermHeader(dict_clean)))

        term_txt, ok = self.get_string(
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
                self.info('The term header part "%s" is not valid.' % part_txt)
                return
            parts.append(part)

        db.setDictTermHeader(dict_clean, json.dumps(parts))
