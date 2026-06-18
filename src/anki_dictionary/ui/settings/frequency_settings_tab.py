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

        self._list_checkboxes: Dict[str, QCheckBox] = {}

        self._build_ui()

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

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        infoLabel = QLabel(
            "Configure how frequency information and level labels are displayed."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        visGroup = QGroupBox("Visibility Options")
        visLayout = QVBoxLayout()
        visLayout.addWidget(self.showStars)
        visLayout.addWidget(self.showRank)

        # Dynamic word list checkboxes
        for key, provider in sorted(self._discover_providers().items()):
            label = f"{provider.lang}: {provider.name}"
            cb = QCheckBox(label)
            cb.setChecked(True)
            self._list_checkboxes[key] = cb
            visLayout.addWidget(cb)

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

        word_list_visibility: Dict[str, Dict[str, bool]] = config.get(
            "word_list_visibility", {}
        )
        for key, cb in self._list_checkboxes.items():
            lang, name = key.split("::", 1)
            visible = word_list_visibility.get(lang, {}).get(name, True)
            cb.setChecked(visible)

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

        word_list_visibility: Dict[str, Dict[str, bool]] = {}
        for key, cb in self._list_checkboxes.items():
            lang, name = key.split("::", 1)
            if lang not in word_list_visibility:
                word_list_visibility[lang] = {}
            word_list_visibility[lang][name] = cb.isChecked()
        config["word_list_visibility"] = word_list_visibility
