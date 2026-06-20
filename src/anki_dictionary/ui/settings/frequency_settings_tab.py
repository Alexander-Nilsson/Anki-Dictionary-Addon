from __future__ import annotations

from typing import Any, Dict, List

from aqt.qt import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.word_list_registry import WordListProvider

_DEFAULT_DISPLAY_NAMES = {"hsk": "HSK³", "jlpt": "JLPT", "cefr": "CEFR"}


class FrequencySettingsTab(QWidget):
    def __init__(self, mw: Any, addon_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mw = mw
        self.addon_path = addon_path

        self.freqStarChar = QLineEdit()
        self.freqStarChar.setMaxLength(2)
        self.freqThreshold1 = QSpinBox()
        self.freqThreshold1.setRange(1, 1000000)
        self.freqThreshold2 = QSpinBox()
        self.freqThreshold2.setRange(1, 1000000)
        self.freqThreshold3 = QSpinBox()
        self.freqThreshold3.setRange(1, 1000000)
        self.freqThreshold4 = QSpinBox()
        self.freqThreshold4.setRange(1, 1000000)
        self.freqThreshold5 = QSpinBox()
        self.freqThreshold5.setRange(1, 1000000)
        self.showStars = QCheckBox("Display Stars")
        self.showRank = QCheckBox("Display Frequency Rank")
        self.showLevelLabels = QCheckBox("Display Level Labels")
        self.showLevelLabels.setChecked(True)

        self._list_checkboxes: Dict[str, QCheckBox] = {}
        self._display_name_inputs: Dict[str, QLineEdit] = {}

        self._build_ui()

    @staticmethod
    def _get_default_display_name(name: str) -> str:
        name_lower = name.lower()
        for key, val in _DEFAULT_DISPLAY_NAMES.items():
            if key in name_lower:
                return val
        return name

    def _discover_providers(self) -> Dict[str, WordListProvider]:
        providers: Dict[str, WordListProvider] = {}
        try:
            langs = self.mw.miDictDB.getCurrentDbLangs()
            registry = self.mw.miDictDB._registry
            if registry is None:
                return providers
            for lang in langs:
                for p in registry.get_providers(lang):
                    key = f"{lang}::{p.name}"
                    providers[key] = p
        except Exception:
            pass
        return providers

    def _on_settings_changed(self) -> None:
        if hasattr(self.mw, "ankiDictionary") and self.mw.ankiDictionary:
            try:
                self.mw.ankiDictionary.refresh_application_theme()
            except Exception:
                pass

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        infoLabel = QLabel(
            "Configure how frequency information and level labels are displayed."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        visGroup = QGroupBox("Word List Visibility & Labels")
        visLayout = QVBoxLayout()
        visLayout.addWidget(self.showStars)
        visLayout.addWidget(self.showRank)
        visLayout.addWidget(self.showLevelLabels)

        visLayout.addWidget(QLabel(""))
        header_lay = QHBoxLayout()
        header_lay.addWidget(QLabel("Enabled"))
        header_lay.addWidget(QLabel("List"))
        header_lay.addStretch()
        header_lay.addWidget(QLabel("Display Name"))
        visLayout.addLayout(header_lay)

        for key, provider in sorted(self._discover_providers().items()):
            row = QHBoxLayout()
            cb = QCheckBox()
            cb.setChecked(True)
            self._list_checkboxes[key] = cb
            row.addWidget(cb)

            row.addWidget(QLabel(f"{provider.lang}: {provider.name}"))
            row.addStretch()

            display_input = QLineEdit()
            display_input.setPlaceholderText(
                self._get_default_display_name(provider.name)
            )
            display_input.setMaxLength(30)
            display_input.setFixedWidth(150)
            self._display_name_inputs[key] = display_input
            row.addWidget(display_input)

            visLayout.addLayout(row)

        visGroup.setLayout(visLayout)
        layout.addWidget(visGroup)

        starGroup = QGroupBox("Star Configuration")
        starLayout = QFormLayout()
        starLayout.addRow("Star Character:", self.freqStarChar)

        threshLayout = QHBoxLayout()
        threshLayout.addWidget(self.freqThreshold1)
        threshLayout.addWidget(self.freqThreshold2)
        threshLayout.addWidget(self.freqThreshold3)
        threshLayout.addWidget(self.freqThreshold4)
        threshLayout.addWidget(self.freqThreshold5)

        starLayout.addRow("Rank Thresholds:", threshLayout)
        starHint = QLabel("Rank thresholds for 5, 4, 3, 2, and 1 star(s) respectively.")
        starHint.setStyleSheet("font-size: 10px; color: gray;")
        starLayout.addRow("", starHint)

        starGroup.setLayout(starLayout)
        layout.addWidget(starGroup)

        layout.addStretch()

    def load_config(self, config: Dict[str, Any]) -> None:
        self.freqStarChar.setText(config.get("star_char", "\u2605"))
        thresholds: List[int] = config.get(
            "star_thresholds", [1501, 5001, 15001, 30001, 60001]
        )
        self.freqThreshold1.setValue(thresholds[0])
        self.freqThreshold2.setValue(thresholds[1])
        self.freqThreshold3.setValue(thresholds[2])
        self.freqThreshold4.setValue(thresholds[3])
        self.freqThreshold5.setValue(thresholds[4])

        self.showStars.setChecked(config.get("show_stars", True))
        self.showRank.setChecked(config.get("show_rank", False))
        self.showLevelLabels.setChecked(config.get("show_level_labels", True))

        word_list_visibility: Dict[str, Dict[str, bool]] = config.get(
            "word_list_visibility", {}
        )
        word_list_display_names: Dict[str, Dict[str, str]] = config.get(
            "word_list_display_names", {}
        )
        for key, cb in self._list_checkboxes.items():
            lang, name = key.split("::", 1)
            visible = word_list_visibility.get(lang, {}).get(name, True)
            cb.setChecked(visible)
            display_name = word_list_display_names.get(lang, {}).get(name, "")
            if display_name:
                self._display_name_inputs[key].setText(display_name)

    def save_config(self, config: Dict[str, Any]) -> None:
        config["star_char"] = self.freqStarChar.text()
        config["star_thresholds"] = [
            self.freqThreshold1.value(),
            self.freqThreshold2.value(),
            self.freqThreshold3.value(),
            self.freqThreshold4.value(),
            self.freqThreshold5.value(),
        ]
        config["show_stars"] = self.showStars.isChecked()
        config["show_rank"] = self.showRank.isChecked()
        config["show_level_labels"] = self.showLevelLabels.isChecked()

        word_list_visibility: Dict[str, Dict[str, bool]] = {}
        for key, cb in self._list_checkboxes.items():
            lang, name = key.split("::", 1)
            if lang not in word_list_visibility:
                word_list_visibility[lang] = {}
            word_list_visibility[lang][name] = cb.isChecked()
        config["word_list_visibility"] = word_list_visibility

        word_list_display_names: Dict[str, Dict[str, str]] = {}
        for key, inp in self._display_name_inputs.items():
            lang, name = key.split("::", 1)
            text = inp.text().strip()
            default = self._get_default_display_name(name)
            if text and text != default:
                if lang not in word_list_display_names:
                    word_list_display_names[lang] = {}
                word_list_display_names[lang][name] = text
        config["word_list_display_names"] = word_list_display_names

        self._on_settings_changed()
