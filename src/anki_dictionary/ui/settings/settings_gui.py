"""
Settings window — thin PyQt shell hosting the Svelte settings web UI.

All settings UI (the five tabs plus the dictionary-group and export-template
editors) lives in the Svelte app built into ``settings.html`` and hosted by
:class:`SettingsBridge`. This widget provides the native Qt surface (window
chrome, escape-to-close, ``mw.dictSettings`` teardown) plus the native flows a
web page cannot drive itself: file dialogs, the dictionary/frequency web
installers, language removal, and font browsing.

Native commands start with ``settings:<name>``, arrive via the bridge's
``handleSettingsAction``, and are delegated here; config editing/saving is
handled entirely by the web UI + bridge.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from collections.abc import Callable
from os.path import join
from typing import Any

from anki.utils import is_win
from aqt.qt import (
    QEvent,
    QFileDialog,
    QIcon,
    QInputDialog,
    QKeySequence,
    QMessageBox,
    QProgressDialog,
    QShortcut,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ...utils.config import get_addon_config
from ...utils.logger import get_logger
from ...utils.paths import get_db_dir, get_word_lists_dir
from .settings_bridge import SettingsBridge

logger = get_logger(__name__.split(".")[-1])

verNumber = "0.1"


class SettingsGui(QWidget):
    """Qt window around the Svelte settings page + native settings flows."""

    def __init__(
        self, mw: Any, path: str, reboot: Callable[[], None] | None = None
    ) -> None:
        super().__init__()
        self.mw = mw
        self.reboot = reboot
        self.addonPath = path
        self.config = get_addon_config()

        self.setMinimumSize(500, 500)
        if is_win:
            self.resize(920, 650)
        else:
            self.resize(1034, 650)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setWindowTitle("Anki Dictionary Settings (Ver. " + verNumber + ")")
        self.setWindowIcon(QIcon(join(self.addonPath, "assets", "icons", "anki.svg")))

        self._bridge = SettingsBridge(self, mw, path)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._bridge)

        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.close)

        self.show()

    # ── teardown ─────────────────────────────────────────────

    def hideEvent(self, event: QEvent) -> None:  # ty:ignore[invalid-method-override]
        self.mw.dictSettings = None
        event.accept()

    def closeEvent(self, event: QEvent) -> None:  # ty:ignore[invalid-method-override]
        self.mw.dictSettings = None
        event.accept()

    def show_tab(self, tab_id: str) -> None:
        """Select one of the web UI's tabs (e.g. the theme gallery).

        Safe to call before the page has finished loading — the bridge holds
        the request until the Svelte app announces itself.
        """
        self._bridge.focus_tab(tab_id)

    # ── config lifecycle (called by the bridge) ───────────────

    def after_save(self) -> None:
        """Refresh web-side data after the config is persisted (bridge-driven).

        The bridge persists the staged config itself; here we re-push the
        derived data sets so editors (dictionary defaults in groups, per-dict
        field overrides, language list) reflect post-save state.
        """
        bridge = self._bridge
        bridge._push("setDictionaryNames", bridge._dictionary_names())
        bridge._push("setWordListData", bridge._word_list_data())
        bridge._push("setLanguagesDicts", bridge._languages_dicts())

    # ── language removal (no tree UI in the web page) ─────────

    def remove_language(self, lang: str) -> None:
        """Remove a language, its dictionaries, word lists and conjugation data."""
        db = self.mw.miDictDB
        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Anki Dictionary",
            f'Do you really want to remove the language "{lang}"?\n\n'
            "All settings and dictionaries for it will be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        if dlg.exec() != QMessageBox.StandardButton.Yes:
            return

        db.deleteLanguage(lang)

        try:
            wl_dir = get_word_lists_dir()
            if os.path.isdir(wl_dir):
                for filename in os.listdir(wl_dir):
                    if filename.lower().startswith(lang.lower().replace(" ", "_")):
                        os.remove(os.path.join(wl_dir, filename))
        except OSError:
            logger.debug("Could not clear word lists for %s", lang, exc_info=True)

        try:
            os.remove(os.path.join(get_db_dir(), "conjugation", f"{lang}.json"))
        except OSError:
            pass

        self._after_native_change()

    # ── native delegates (file dialogs / web installers) ─────

    def web_install_dicts(self) -> None:
        """Open the dictionary web-install wizard (creates languages itself)."""
        from ...web.installer import DictionaryWebInstallWizard

        DictionaryWebInstallWizard.execute_modal()
        self._after_native_change()

    def import_dicts(self) -> None:
        """Import dictionaries from ZIP files into a user-chosen language."""
        from ..dialogs.dict_import import importDict

        lang = self._select_language()
        if lang is None:
            return

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

        for i, path in enumerate(paths):
            if progress.wasCanceled():
                break

            dict_name = os.path.splitext(os.path.basename(path))[0]

            if not use_default_names:
                dict_name, ok = QInputDialog.getText(
                    self, "Anki Dictionary", "Set name of dictionary", text=dict_name
                )
                if not ok:
                    continue

            try:
                importDict(lang, path, dict_name, parent=self)
            except ValueError as e:
                if "Creating dictionary failed" in str(e) and "duplicate" in str(e):
                    progress.setValue(i + 1)
                    continue
                QMessageBox.information(self, "Anki Dictionary", str(e))
                continue

            progress.setValue(i + 1)

        progress.close()
        if paths:
            self._after_native_change()

    def web_install_freq(self) -> None:
        """Open the frequency-data web wizard for a user-chosen language."""
        from ...web.windows import FreqConjWebWindow

        lang = self._select_language()
        if lang is None:
            return

        FreqConjWebWindow.execute_modal(lang, FreqConjWebWindow.Mode.Freq)
        self._after_native_change()

    def import_freq(self) -> None:
        """Import a frequency/level JSON (or ZIP) file for a user-chosen language."""
        lang = self._select_language()
        if lang is None:
            return

        path = QFileDialog.getOpenFileName(
            self,
            "Select the frequency or level data you want to import",
            os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*.*)",
        )[0]
        if not path:
            return

        filename = os.path.basename(path)
        wl_dir = get_word_lists_dir()
        os.makedirs(wl_dir, exist_ok=True)

        dst_path = os.path.join(wl_dir, filename)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            QMessageBox.information(self, "Anki Dictionary", "Importing data failed.")
            return

        # Extract ZIP word lists (Anki-dictionary format)
        try:
            with zipfile.ZipFile(dst_path) as zf:
                data_files = [
                    f
                    for f in zf.namelist()
                    if f.startswith("term_meta_bank_") or f.startswith("term_bank_")
                ]
                if data_files:
                    with zf.open(data_files[0]) as df:
                        real_data = json.load(df)
                    with open(dst_path, "w", encoding="utf-8") as f:
                        json.dump(real_data, f, ensure_ascii=False)
        except (zipfile.BadZipFile, Exception):  # noqa: BLE001 - plain JSON, skip
            pass

        self._after_native_change()
        QMessageBox.information(
            self, "Anki Dictionary", f'Imported data as "{filename}" for "{lang}".'
        )

    def browse_font_file(self) -> None:
        """Open a native font picker and send the path back to the web page."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Font File",
            os.path.expanduser("~"),
            "Font Files (*.ttf *.otf *.ttc);;All Files (*.*)",
        )
        if path:
            self._bridge._push("setFontFile", path)

    # ── helpers ───────────────────────────────────────────────

    def _select_language(self) -> str | None:
        """Ask which language to install into; None if the user cancels."""
        langs: list[str] = []
        try:
            langs = list(self.mw.miDictDB.getCurrentDbLangs())
        except Exception:  # noqa: BLE001
            logger.debug("Could not list languages", exc_info=True)

        if langs:
            choice, ok = QInputDialog.getItem(
                self, "Anki Dictionary", "Select language:", langs, 0, False
            )
            return choice if ok else None

        text, ok = QInputDialog.getText(self, "Anki Dictionary", "Language name:")
        return text.strip() or None if ok else None

    def _after_native_change(self) -> None:
        """Refresh the addon + re-push web-side data after a native flow."""
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            try:
                self.mw.refreshAnkiDictConfig(force=True)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Could not refresh config after native change", exc_info=True
                )
        self.after_save()
