import os
from enum import Enum
from aqt.qt import *
from anki.httpclient import HttpClient
import aqt
from ..utils.common import prefer_ipv4

from ..utils.paths import get_addon_root, get_icons_dir, get_db_dir
from . import config as webConfig


class FreqConjWebWindow(QDialog):

    class Mode(Enum):
        Freq = (0,)
        Conj = (1,)

    MIN_SIZE = (400, 400)

    def __init__(self, dst_lang, index_data, mode):
        super(FreqConjWebWindow, self).__init__()
        self.dst_lang = dst_lang
        self.mode = mode
        self.mode_str = "frequency" if self.mode == self.Mode.Freq else "conjugation"

        self.setWindowTitle("Anki Dictionary - Web Installer")
        self.setWindowIcon(QIcon(os.path.join(get_icons_dir(), "anki.svg")))

        lyt = QVBoxLayout()
        self.setLayout(lyt)

        lbl = QLabel(
            "Select the language you want to download %s data from" % self.mode_str
        )
        lbl.setWordWrap(True)
        lyt.addWidget(lbl)

        self.lst = QListWidget()
        lyt.addWidget(self.lst)

        for lang in index_data.get("languages", []):
            lists = []
            if self.mode == self.Mode.Freq:
                if lang.get("frequency_url"):
                    lists.append({"name": "Frequency", "url": lang["frequency_url"]})
                for fl in lang.get("frequency_lists", []):
                    lists.append(fl)
            else:
                if lang.get("conjugation_url"):
                    lists.append({"name": "Conjugation", "url": lang["conjugation_url"]})
                for cl in lang.get("conjugation_lists", []):
                    lists.append(cl)

            if not lists:
                continue

            lang_str = lang.get("name_en", "<Unnamed>")
            if "name_native" in lang:
                lang_str += " (" + lang["name_native"] + ")"
            
            for l_info in lists:
                url = l_info["url"]
                name = l_info["name"]

                if not url.startswith("http"):
                    url = webConfig.normalize_url(webConfig.DEFAULT_SERVER + url)
                
                display_str = f"{lang_str} - {name}"
                itm = QListWidgetItem(display_str)
                itm.setData(Qt.ItemDataRole.UserRole, url)
                itm.setData(Qt.ItemDataRole.UserRole + 1, name)
                self.lst.addItem(itm)

        btn = QPushButton("Download")
        btn.clicked.connect(self.download)
        lyt.addWidget(btn)

        self.setMinimumSize(*self.MIN_SIZE)

    def download(self):
        idx = self.lst.currentIndex()
        if not idx.isValid():
            QMessageBox.show(self, self.windowTitle(), "Please select a language.")
            return
        url = idx.data(Qt.ItemDataRole.UserRole)

        client = HttpClient()

        try:
            with prefer_ipv4():
                resp = client.session.get(url, timeout=15, stream=True)
        except Exception:
            resp = None

        # If it's a 404 and looks like a path with underscores,
        # try replacing underscores with spaces and URL-encoding the result.
        if (resp is None or resp.status_code == 404) and "_" in url:
            import urllib.parse

            new_url = url.replace("_", " ")
            parts = new_url.split("://")
            if len(parts) > 1:
                quoted_path = urllib.parse.quote(parts[1], safe="/")
                new_url = parts[0] + "://" + quoted_path
            else:
                new_url = urllib.parse.quote(new_url, safe="/")

            try:
                with prefer_ipv4():
                    resp = client.session.get(new_url, timeout=15, stream=True)
            except Exception:
                resp = None

        if resp is None or resp.status_code != 200:
            QMessageBox.information(
                self, self.windowTitle(), "Downloading %s data failed." % self.mode_str
            )
            return

        # Manually stream content to avoid hangs
        chunks = []
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                chunks.append(chunk)

        data = b"".join(chunks)

        dir_path = os.path.join(get_db_dir(), self.mode_str)
        os.makedirs(dir_path, exist_ok=True)

        list_name = idx.data(Qt.ItemDataRole.UserRole + 1)
        if self.mode == self.Mode.Freq and list_name != "Frequency":
            filename = "%s_%s.json" % (self.dst_lang, list_name)
        else:
            filename = "%s.json" % self.dst_lang

        dst_path = os.path.join(dir_path, filename)

        with open(dst_path, "wb") as f:
            f.write(data)

        # Clear database cache to reflect changes
        if hasattr(aqt.mw, "miDictDB"):
            aqt.mw.miDictDB._extra_data_cache.pop(self.dst_lang, None)

        if self.mode == self.Mode.Freq:
            msg = (
                'Imported data as "%s" for "%s".\n\nNote that some data is only applied to newly imported dictionaries.'
                % (filename, self.dst_lang)
            )
        else:
            msg = 'Imported conjugation data for "%s".' % self.dst_lang
        QMessageBox.information(self, self.windowTitle(), msg)

        self.accept()

    @classmethod
    def execute_modal(cls, dst_lang, mode):
        aqt.mw.progress.start()
        try:
            index_data = webConfig.download_index()
        finally:
            aqt.mw.progress.finish()
        if index_data is None:
            QMessageBox.information(
                None,
                "Anki Dictionary",
                "The dictionary server is not reachable at the moment.\n\n"
                "Please try again later.",
            )
            return QDialog.Rejected
        window = cls(dst_lang, index_data, mode)
        return window.exec()
