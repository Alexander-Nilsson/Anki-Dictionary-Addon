from __future__ import annotations

from aqt.qt import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from ...utils.logger import get_logger
from .dict_importer_widget import DictImporter
from .language_manager_widget import LanguageManager
from .tree_manager_widget import TreeManager

logger = get_logger(__name__.split(".")[-1])


class DictionaryManagerWidget(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        self.tree_manager = TreeManager(mw, self)
        self.dict_importer = DictImporter(mw, self)
        self.language_manager = LanguageManager(mw, self)

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

        install_btn = QPushButton("Install from Web")
        install_btn.clicked.connect(self.web_installer)
        left_lyt.addWidget(install_btn)

        right_side = QWidget()
        splitter.addWidget(right_side)
        right_lyt = QVBoxLayout()
        right_side.setLayout(right_lyt)

        self.lang_grp = QGroupBox("Language Options")
        right_lyt.addWidget(self.lang_grp)

        lang_lyt = QVBoxLayout()
        self.lang_grp.setLayout(lang_lyt)

        lang_lyt_row1 = QHBoxLayout()
        lang_lyt_row2 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt_row1)
        lang_lyt.addLayout(lang_lyt_row2)

        install_dict_btn = QPushButton("Install Dictionaries")
        install_menu = QMenu()
        install_menu.addAction("From Web Wizard", self.web_installer_lang)
        install_menu.addAction("From Files", self.import_dicts)
        install_dict_btn.setMenu(install_menu)
        lang_lyt_row1.addWidget(install_dict_btn)

        install_freq_btn = QPushButton("Install Frequency Data")
        freq_menu = QMenu()
        freq_menu.addAction("From Web Wizard", self.web_freq_data)
        freq_menu.addAction("From Files", self.set_freq_data)
        install_freq_btn.setMenu(freq_menu)
        lang_lyt_row1.addWidget(install_freq_btn)

        remove_lang_btn = QPushButton("Remove Language")
        remove_lang_btn.clicked.connect(self.remove_lang)
        lang_lyt_row2.addWidget(remove_lang_btn)

        lang_lyt_row1.addStretch()
        lang_lyt_row2.addStretch()

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

    # --- TreeManager delegation ---

    def reload_tree_widget(self):
        self.tree_manager.reload_tree_widget()

    def on_current_item_change(self, new_sel, old_sel):
        self.tree_manager.on_current_item_change(new_sel, old_sel)

    def get_current_lang_dict(self):
        return self.tree_manager.get_current_lang_dict()

    def get_current_lang_item(self):
        return self.tree_manager.get_current_lang_item()

    def get_current_dict_item(self):
        return self.tree_manager.get_current_dict_item()

    # --- DictImporter delegation ---

    def web_installer(self):
        self.dict_importer.web_installer()

    def web_installer_lang(self):
        self.dict_importer.web_installer_lang()

    def import_dicts(self):
        self.dict_importer.import_dicts()

    def import_dict(self):
        self.dict_importer.import_dict()

    def set_freq_data(self):
        self.dict_importer.set_freq_data()

    def web_freq_data(self):
        self.dict_importer.web_freq_data()

    def set_conj_data(self):
        self.dict_importer.set_conj_data()

    def web_conj_data(self):
        self.dict_importer.web_conj_data()

    def set_term_header(self):
        self.dict_importer.set_term_header()

    # --- LanguageManager delegation ---

    def add_lang(self):
        self.language_manager.add_lang()

    def remove_lang(self):
        self.language_manager.remove_lang()

    def remove_dict(self):
        self.language_manager.remove_dict()
