from aqt.qt import (
    QCheckBox,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextCursor,
    QTextEdit,
    QThread,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    Qt,
    pyqtSignal,
)
from anki.httpclient import HttpClient
import json
import io
import os
import aqt
import zipfile


from ..ui.dialogs.wizard import MiWizard, MiWizardPage
from . import config as webConfig
from ..utils.common import prefer_ipv4

addon_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


class NoAutoSelectLineEdit(QLineEdit):

    def focusInEvent(self, e):
        super(NoAutoSelectLineEdit, self).focusInEvent(e)
        self.deselect()


class DictionaryWebInstallWizard(MiWizard):

    INITIAL_SIZE = (600, 400)

    def __init__(self, force_lang=None):
        super(DictionaryWebInstallWizard, self).__init__()

        self.dictionary_force_lang = force_lang

        self.setWindowTitle("Anki Dictionary - Web Installer")
        self.setWindowIcon(
            QIcon(os.path.join(addon_path, "assets", "icons", "anki.svg"))
        )

        server_add_page = self.add_page(ServerAskPage(self))
        dict_select_page = self.add_page(DictionarySelectPage(self), server_add_page)
        dict_confirm_page = self.add_page(DictionaryConfirmPage(self), dict_select_page)
        dict_install_page = self.add_page(
            DictionaryInstallPage(self), dict_confirm_page
        )

        self.resize(*self.INITIAL_SIZE)

    @classmethod
    def execute_modal(cls, force_lang=None):
        wizard = cls(force_lang)
        return wizard.exec()


class ServerAskPage(MiWizardPage):

    def __init__(self, wizard):
        super(ServerAskPage, self).__init__(wizard)
        self.wizard = wizard

        self.title = "Select Dictionary Server"

        lyt = QVBoxLayout()
        self.setLayout(lyt)

        lyt.addStretch()

        lbl = QLabel(
            "Our dictionary server contains several free, open source dictionaries.\n\n"
            "You can also select a custom server to install other 3rd party dictionaries.\n"
        )
        lbl.setWordWrap(True)
        lyt.addWidget(lbl)

        server_lyt = QHBoxLayout()
        lyt.addLayout(server_lyt)

        self.server_line = NoAutoSelectLineEdit()
        self.server_line.setPlaceholderText("Insert Dictionary Server Address")
        server_lyt.addWidget(self.server_line)

        self.server_reset_btn = QPushButton("Default")
        server_lyt.addWidget(self.server_reset_btn)

        lyt.addStretch()

        self.reset_server_line()

        self.server_reset_btn.clicked.connect(self.reset_server_line)

    def reset_server_line(self):
        self.server_line.setText(webConfig.DEFAULT_SERVER)

    def on_next(self):

        server_url_usr = self.server_line.text().strip()
        server_url = webConfig.normalize_url(server_url_usr)

        aqt.mw.progress.start()
        try:
            index_data = webConfig.download_index(server_url)
        finally:
            aqt.mw.progress.finish()

        if index_data is None:
            QMessageBox.information(
                self,
                "Anki Dictionary",
                'The server "%s" is not reachable.\n\n'
                "Make sure you are connected to the internet and the url you entered is valid."
                % server_url_usr,
            )
            return False

        self.wizard.dictionary_index = index_data
        self.wizard.Dictionary_server_root = server_url

        return True


class DictionarySelectPage(MiWizardPage):

    def __init__(self, wizard):
        super(DictionarySelectPage, self).__init__(wizard)
        self.wizard = wizard

        self.title = "Select the dictionaries you want to install"

        lyt = QVBoxLayout()
        self.setLayout(lyt)

        self.dict_tree = QTreeWidget()
        self.dict_tree.setHeaderHidden(True)
        lyt.addWidget(self.dict_tree)

        options_lyt = QHBoxLayout()
        lyt.addLayout(options_lyt)

        self.install_freq = QCheckBox("Install Frequency Data")
        self.install_freq.setChecked(True)
        options_lyt.addWidget(self.install_freq)

        self.install_conj = QCheckBox("Install Conjugation Data")
        self.install_conj.setChecked(True)
        options_lyt.addWidget(self.install_conj)

        self.install_hsk = QCheckBox("Install HSK Data")
        self.install_hsk.setChecked(True)
        options_lyt.addWidget(self.install_hsk)

        options_lyt.addStretch()

        self.dict_tree.itemChanged.connect(self.on_item_changed)
        self._updating_checks = False

    def on_item_changed(self, item, column):
        if self._updating_checks:
            return

        self._updating_checks = True
        try:
            state = item.checkState(0)

            def set_child_states(parent):
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    child.setCheckState(0, state)
                    set_child_states(child)

            set_child_states(item)
        finally:
            self._updating_checks = False

    def on_show(self, is_next, is_back):
        if is_next:
            self.setup_entries()

    def on_next(self):

        dictionaries_to_install = []

        dict_root = self.dict_tree.invisibleRootItem()

        for li in range(dict_root.childCount()):
            lang_item = dict_root.child(li)
            language = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)
            dictionaries = []

            def scan_tree(item):
                for di in range(item.childCount()):
                    dict_item = item.child(di)
                    dictionary = dict_item.data(0, Qt.ItemDataRole.UserRole + 1)
                    if dictionary:
                        try:
                            # Try the new way
                            if dict_item.checkState(0) == Qt.CheckState.Checked:
                                dictionaries.append(dictionary)
                        except AttributeError:
                            # Fallback for older versions
                            if dict_item.checkState(0) == Qt.Checked:
                                dictionaries.append(dictionary)
                    else:
                        scan_tree(dict_item)

            scan_tree(lang_item)

            if len(dictionaries) > 0:
                lang_w_enabled_dicts = language.copy()
                lang_w_enabled_dicts["dictionaries"] = dictionaries
                dictionaries_to_install.append(lang_w_enabled_dicts)

        self.wizard.dictionary_install_index = dictionaries_to_install
        self.wizard.dictionary_install_frequency = self.install_freq.isChecked()
        self.wizard.dictionary_install_conjugation = self.install_conj.isChecked()
        self.wizard.dictionary_install_hsk = self.install_hsk.isChecked()

        return True

    # TODO: Add whitelist functionality so only limited amount is displayed based on user target language, native language, etc
    def setup_entries(self):

        self.dict_tree.clear()

        dictionary_index = getattr(self.wizard, "dictionary_index", {})

        languages = dictionary_index.get("languages", [])

        self._updating_checks = True
        try:
            for language in languages:
                name_en = language.get("name_en")
                name_native = language.get("name_native")

                if not name_en:
                    continue

                text = name_en
                if name_native:
                    text += " (" + name_native + ")"

                lang_item = QTreeWidgetItem([text])
                lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, language)
                lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)
                try:
                    lang_item.setCheckState(0, Qt.CheckState.Unchecked)
                except AttributeError:
                    lang_item.setCheckState(0, Qt.Unchecked)

                self.dict_tree.addTopLevelItem(lang_item)

                def load_dict_list(dict_list, parent_item):
                    for dictionary in dict_list:
                        dictionary_name = dictionary.get("name")
                        if not dictionary_name:
                            continue
                        dictionary_text = dictionary_name

                        dictionary_description = dictionary.get("description")
                        if dictionary_description:
                            dictionary_text += " - " + dictionary_description

                        dict_item = QTreeWidgetItem([dictionary_text])
                        try:
                            # Try the new way
                            dict_item.setCheckState(0, Qt.CheckState.Unchecked)
                        except AttributeError:
                            # Fallback for older versions
                            dict_item.setCheckState(0, Qt.Unchecked)
                        dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, None)
                        dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, dictionary)

                        parent_item.addChild(dict_item)

                for to_language in language.get("to_languages", []):
                    to_name_en = to_language.get("name_en")
                    to_name_native = to_language.get("name_native")

                    if not to_name_en:
                        continue

                    text = to_name_en
                    if to_name_native:
                        text += " (" + to_name_native + ")"

                    to_lang_item = QTreeWidgetItem([text])
                    to_lang_item.setData(0, Qt.ItemDataRole.UserRole + 0, None)
                    to_lang_item.setData(0, Qt.ItemDataRole.UserRole + 1, None)
                    try:
                        to_lang_item.setCheckState(0, Qt.CheckState.Unchecked)
                    except AttributeError:
                        to_lang_item.setCheckState(0, Qt.Unchecked)

                    lang_item.addChild(to_lang_item)

                    dictionaries = to_language.get("dictionaries", [])
                    load_dict_list(dictionaries, to_lang_item)

                dictionaries = language.get("dictionaries", [])
                load_dict_list(dictionaries, lang_item)
        finally:
            self._updating_checks = False


class DictionaryConfirmPage(MiWizardPage):

    def __init__(self, wizard, can_select_none=False):
        super(DictionaryConfirmPage, self).__init__(wizard)
        self.wizard = wizard
        self.can_select_none = can_select_none

        self.title = "Confirm selected dictionaries"
        self.back_enabled = True
        self.next_enabled = True
        self.next_text = "Confirm"

        lyt = QVBoxLayout()
        self.setLayout(lyt)

        self.box = QTextEdit()
        self.box.setReadOnly(True)
        lyt.addWidget(self.box)

    def on_show(self, is_next, is_prev):
        install_index = getattr(self.wizard, "dictionary_install_index", [])
        install_freq = getattr(self.wizard, "dictionary_install_frequency", False)
        install_conj = getattr(self.wizard, "dictionary_install_conjugation", False)
        install_hsk = getattr(self.wizard, "dictionary_install_hsk", False)

        has_selection = len(install_index) > 0
        has_multiple_langs = len(install_index) > 1
        force_lang = getattr(self.wizard, "dictionary_force_lang", None)

        can_continue = False

        if not has_selection:
            if self.can_select_none:
                self.box.setText(
                    "No dictionaries selected.<br><br>Are you sure that you want to continue?"
                )
                can_continue = True
            else:
                self.box.setText(
                    "No dictionaries selected.<br><br>Please go back to the previous page and select the dictionaries that you want to install."
                )
        elif has_multiple_langs and force_lang:
            self.box.setText(
                "You can only install dictionaries from a single language when adding dictionaries to an existing language.<br><br>"
                "Please go back to the previous page and make sure only dictionaries from a single language are selected."
            )
        else:
            txt = ""
            for language in install_index:
                txt += "<b>"
                txt += language["name_en"]
                if "name_native" in language:
                    txt += " (" + language["name_native"] + ")"
                if force_lang:
                    txt += " into " + force_lang
                txt += "</b><ul>"

                if install_freq:
                    has_freq = "frequency_url" in language
                    if not has_freq and "frequency_lists" in language:
                        has_freq = len(language["frequency_lists"]) > 0

                    if has_freq:
                        txt += "<li>Installing frequency data</li>"
                    else:
                        txt += "<li><b>No frequency data available</b></li>"
                if install_conj:
                    has_conj = "conjugation_url" in language
                    if not has_conj and "conjugation_lists" in language:
                        has_conj = len(language["conjugation_lists"]) > 0

                    if has_conj:
                        txt += "<li>Installing conjugation data</li>"
                    else:
                        txt += "<li><b>No conjugation data available</b></li>"
                if install_hsk:
                    has_hsk = "hsk_url" in language
                    if not has_hsk and "word_lists" in language:
                        has_hsk = any(
                            "hsk" in wl.get("name", "").lower()
                            for wl in language["word_lists"]
                        )

                    if has_hsk:
                        txt += "<li>Installing HSK data</li>"
                    else:
                        txt += "<li><b>No HSK data available</b></li>"

                for dictionary in language.get("dictionaries", []):
                    txt += "<li>"
                    txt += dictionary["name"]
                    txt += "</li>"

                txt += "</ul>"

            self.box.setText(txt)
            can_continue = True

        self.next_enabled = can_continue
        self.refresh_wizard_states()


class DictionaryInstallPage(MiWizardPage):

    class InstallThread(QThread):

        progress_update = pyqtSignal(int)
        log_update = pyqtSignal(str)

        def __init__(
            self,
            wizard,
            server_root,
            install_index,
            install_freq,
            install_conj,
            install_hsk,
            force_lang=None,
        ):
            QThread.__init__(self)
            self.wizard = wizard
            self.server_root = server_root
            self.install_index = install_index
            self.install_freq = install_freq
            self.install_conj = install_conj
            self.install_hsk = install_hsk
            self.force_lang = force_lang
            self.cancel_requested = False

        def construct_url(self, url):
            if not url.startswith("http"):
                return self.server_root + url
            return url

        def fetch_data(self, client, url):
            """Fetch data from URL with standard quoting."""
            import urllib.parse

            # Simple quoting to handle spaces in URLs
            parts = url.split("://")
            if len(parts) > 1:
                quoted_url = parts[0] + "://" + urllib.parse.quote(parts[1], safe="/")
            else:
                quoted_url = urllib.parse.quote(url, safe="/")

            with prefer_ipv4():
                return client.session.get(quoted_url, timeout=60, stream=True)

        def run(self):
            from ..ui.dialogs.dictionary_manager import importDict

            client = HttpClient()

            num_dicts = 0
            num_installed = 0

            def update_dict_progress(amt):
                progress = 0
                if num_dicts > 0:
                    progress = num_installed / num_dicts
                    progress += amt / num_dicts
                progress_percent = round(progress * 100)
                self.progress_update.emit(progress_percent)

            for l in self.install_index:
                num_dicts += len(l.get("dictionaries", []))

            self.log_update.emit("Installing %d dictionaries..." % num_dicts)

            freq_path = os.path.join(addon_path, "user_files", "db", "frequency")
            os.makedirs(freq_path, exist_ok=True)

            conj_path = os.path.join(addon_path, "user_files", "db", "conjugation")
            os.makedirs(conj_path, exist_ok=True)

            hsk_path = os.path.join(addon_path, "user_files", "db", "hsk")
            os.makedirs(hsk_path, exist_ok=True)

            for l in self.install_index:
                if self.cancel_requested:
                    return

                lname = self.force_lang
                if not lname:
                    lname = l.get("name_en")
                if not lname:
                    continue

                # Create Language
                try:
                    aqt.mw.miDictDB.addLanguages([lname])
                except Exception as e:
                    # Lanugage already exists
                    pass

                # Install frequency data
                if self.install_freq:
                    furls = []
                    if l.get("frequency_url"):
                        furls.append({"name": "Frequency", "url": l["frequency_url"]})
                    for fl in l.get("frequency_lists", []):
                        furls.append(fl)

                    for f_info in furls:
                        fname = f_info["name"]
                        furl = self.construct_url(f_info["url"])
                        self.log_update.emit(
                            "Installing %s %s data..." % (lname, fname)
                        )
                        dl_resp = self.fetch_data(client, furl)
                        if dl_resp.status_code == 200:
                            # Handle ZIP if necessary
                            chunks = []
                            for chunk in dl_resp.iter_content(chunk_size=16384):
                                if chunk:
                                    chunks.append(chunk)
                            data = b"".join(chunks)

                            if furl.lower().endswith(".zip"):
                                try:
                                    z = zipfile.ZipFile(io.BytesIO(data))
                                    # Find first json file
                                    json_files = [
                                        n for n in z.namelist() if n.endswith(".json")
                                    ]
                                    if json_files:
                                        data = z.read(json_files[0])
                                except Exception as e:
                                    self.log_update.emit(
                                        " ERROR: Failed to unzip: %s" % str(e)
                                    )

                            dst_path = os.path.join(freq_path, "%s.json" % lname)
                            with open(dst_path, "wb") as f:
                                f.write(data)
                            # Only install one frequency list for now to avoid overwriting
                            break
                        else:
                            self.log_update.emit(
                                " ERROR: Download failed (%d)." % dl_resp.status_code
                            )

                # Install conjugation data
                if self.install_conj:
                    curls = []
                    if l.get("conjugation_url"):
                        curls.append(
                            {"name": "Conjugation", "url": l["conjugation_url"]}
                        )
                    for cl in l.get("conjugation_lists", []):
                        curls.append(cl)

                    for c_info in curls:
                        cname = c_info["name"]
                        curl = self.construct_url(c_info["url"])
                        self.log_update.emit(
                            "Installing %s %s data..." % (lname, cname)
                        )
                        dl_resp = self.fetch_data(client, curl)
                        if dl_resp.status_code == 200:
                            chunks = []
                            for chunk in dl_resp.iter_content(chunk_size=16384):
                                if chunk:
                                    chunks.append(chunk)
                            data = b"".join(chunks)

                            dst_path = os.path.join(conj_path, "%s.json" % lname)
                            with open(dst_path, "wb") as f:
                                f.write(data)
                            # Only install one conjugation list
                            break
                        else:
                            self.log_update.emit(
                                " ERROR: Download failed (%d)." % dl_resp.status_code
                            )

                # Install HSK data
                if self.install_hsk:
                    hurls = []
                    if l.get("hsk_url"):
                        hurls.append({"name": "HSK", "url": l["hsk_url"]})

                    # Also check word_lists for items containing 'HSK'
                    for wl in l.get("word_lists", []):
                        if "hsk" in wl.get("name", "").lower():
                            hurls.append(wl)

                    for h in hurls:
                        hname = h["name"]
                        hurl = self.construct_url(h["url"])
                        self.log_update.emit(
                            "Installing %s %s data..." % (lname, hname)
                        )

                        dl_resp = self.fetch_data(client, hurl)
                        if dl_resp.status_code == 200:
                            # Map names to expected filenames for database.py
                            suffix = ""
                            if "2.0" in hname:
                                suffix = "_hsk2"
                            elif "3.0" in hname:
                                suffix = "_hsk3"

                            dst_path = os.path.join(
                                hsk_path, "%s%s.json" % (lname, suffix)
                            )
                            with open(dst_path, "wb") as f:
                                for chunk in dl_resp.iter_content(chunk_size=16384):
                                    if chunk:
                                        f.write(chunk)
                        else:
                            self.log_update.emit(
                                " ERROR: Download failed (%d)." % dl_resp.status_code
                            )

                # Install dictionaries
                for d in l.get("dictionaries", []):
                    if self.cancel_requested:
                        return

                    dname = d.get("name")

                    # Check if already exists
                    if aqt.mw.miDictDB.dictExists(dname, lname):
                        self.log_update.emit("Skipping %s (already installed)." % dname)
                        update_dict_progress(1.0)
                        num_installed += 1
                        continue

                    durl = self.construct_url(d.get("url"))

                    self.log_update.emit("Installing %s..." % dname)

                    self.log_update.emit(" Downloading %s..." % durl)
                    dl_resp = self.fetch_data(client, durl)

                    if dl_resp.status_code == 200:
                        update_dict_progress(0.5)
                        self.log_update.emit(" Importing...")
                        # Manually stream content to avoid hangs
                        chunks = []
                        for chunk in dl_resp.iter_content(chunk_size=16384):
                            if chunk:
                                chunks.append(chunk)

                        ddata = b"".join(chunks)

                        try:
                            # Pass wizard as parent to allow message boxes if needed
                            # Note: calling GUI from thread is usually bad, but QMessageBox.exec()
                            # might work if it's handled properly by the bridge or if we use signals.
                            # However, importDict uses QMessageBox.
                            # In Anki context, this might need to be handled via signals if it causes crashes.
                            # But let's try passing the parent first.
                            importDict(
                                lname, io.BytesIO(ddata), dname, parent=self.wizard
                            )
                        except ValueError as e:
                            self.log_update.emit(" ERROR: %s" % str(e))
                    else:
                        self.log_update.emit(
                            " ERROR: Download failed (%d)." % dl_resp.status_code
                        )

                    update_dict_progress(1.0)
                    num_installed += 1

                # Only once language can be installed when language is forced
                if self.force_lang:
                    # Should never happen
                    break

            self.progress_update.emit(100)
            self.log_update.emit("All done.")

    def __init__(self, wizard, is_last_page=True):
        super(DictionaryInstallPage, self).__init__(wizard)
        self.wizard = wizard
        self.is_last_page = is_last_page

        self.title = "Installing selected dictionaries..."
        self.back_enabled = False
        self.next_enabled = False

        if self.is_last_page:
            self.next_text = "Finish"

        lyt = QVBoxLayout()
        self.setLayout(lyt)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        lyt.addWidget(self.progress_bar)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        lyt.addWidget(self.log_box)

        self.is_complete = False
        self.install_thread = None

    def on_show(self, is_next, is_back):
        if is_next:
            self.is_complete = False
            self.install_thread = None
            self.progress_bar.setValue(0)
            self.log_box.clear()
            self.start_thread()

    def on_cancel(self):
        if self.install_thread and self.install_thread.isRunning():
            dlg = QMessageBox(
                QMessageBox.Icon.Question,
                "Anki Dictionary",
                "Do you really want to cancel the import process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self,
            )
            r = dlg.exec()

            if r != QMessageBox.StandardButton.Yes:
                return False

            self.install_thread.cancel_requested = True
            self.install_thread.wait()

        return True

    def add_log(self, txt):
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        if not self.log_box.document().isEmpty():
            self.log_box.insertPlainText("\n")
        self.log_box.insertPlainText(txt)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def start_thread(self):
        if self.install_thread:
            return

        server_root = getattr(self.wizard, "Dictionary_server_root", "")
        install_index = getattr(self.wizard, "dictionary_install_index", [])
        install_freq = getattr(self.wizard, "dictionary_install_frequency", False)
        install_conj = getattr(self.wizard, "dictionary_install_conjugation", False)
        install_hsk = getattr(self.wizard, "dictionary_install_hsk", False)
        force_lang = getattr(self.wizard, "dictionary_force_lang", None)

        self.install_thread = self.InstallThread(
            self.wizard,
            server_root,
            install_index,
            install_freq,
            install_conj,
            install_hsk,
            force_lang,
        )
        self.install_thread.finished.connect(self.on_thread_finish)
        self.install_thread.progress_update.connect(self.update_progress)
        self.install_thread.log_update.connect(self.add_log)
        self.install_thread.start()

    def on_thread_finish(self):
        self.progress_bar.setValue(100)
        self.next_enabled = True

        if self.is_last_page:
            self.cancel_enabled = False

        self.refresh_wizard_states()
