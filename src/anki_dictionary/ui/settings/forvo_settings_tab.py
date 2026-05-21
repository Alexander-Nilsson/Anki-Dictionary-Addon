from __future__ import annotations

from typing import Any, Dict

from aqt.qt import *

from ...utils.constants import FORVO_LANGUAGES


class ForvoSettingsTab(QWidget):
    def __init__(self, mw: Any, addon_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mw = mw
        self.addon_path = addon_path

        self.forvoEnabled = QCheckBox()
        self.forvoLanguage = QComboBox()
        self.forvoLanguage.setEditable(True)
        for lang in FORVO_LANGUAGES:
            self.forvoLanguage.addItem(str(lang["English name"]), str(lang["Code"]))

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        infoLabel = QLabel(
            "Enable Forvo to fetch native pronunciations for your search terms."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        formGroup = QGroupBox("Forvo Configuration")
        formLayout = QFormLayout()

        formLayout.addRow("Enable Forvo Dictionary:", self.forvoEnabled)
        formLayout.addRow("Forvo Language:", self.forvoLanguage)

        langHint = QLabel("Select the language for Forvo pronunciation searches.")
        langHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", langHint)

        formGroup.setLayout(formLayout)
        layout.addWidget(formGroup)

        layout.addStretch()

    def load_config(self, config: Dict[str, Any]) -> None:
        self.forvoEnabled.setChecked(config.get("forvo_enabled", True))
        forvo_lang = config.get("forvo_language", "ja")
        index = self.forvoLanguage.findData(str(forvo_lang))
        if index != -1:
            self.forvoLanguage.setCurrentIndex(index)

    def save_config(self, config: Dict[str, Any]) -> None:
        config["forvo_enabled"] = self.forvoEnabled.isChecked()
        config["forvo_language"] = self.forvoLanguage.currentData()

    def is_enabled(self) -> bool:
        return self.forvoEnabled.isChecked()
