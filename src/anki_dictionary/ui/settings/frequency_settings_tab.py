from __future__ import annotations

import os
from typing import Any, Dict, List

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


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
        self.showHSK = QCheckBox("Display Level Labels (HSK, JLPT, etc.)")
        self.hskMode = QComboBox()
        self.hskMode.addItem("HSK 3.0", "hsk3")
        self.hskMode.addItem("HSK 2.0", "hsk2")
        self.hskMode.addItem("Both (HSK 2.0 & 3.0)", "both")

        self._build_ui()
        self._update_hsk_visibility()

    def _has_chinese_language(self) -> bool:
        try:
            langs = self.mw.miDictDB.getCurrentDbLangs()
            for lang in langs:
                if any(x in lang.lower() for x in ["zh", "chinese", "cn"]):
                    return True
        except Exception:
            pass
        return False

    def _has_hsk_data(self) -> bool:
        from ...utils.paths import get_hsk_dir

        hsk_dir = get_hsk_dir()
        if not os.path.exists(hsk_dir):
            return False
        for f in os.listdir(hsk_dir):
            if f.endswith(".json") and "hsk" in f.lower():
                return True
        return False

    def _update_hsk_visibility(self) -> None:
        visible = self._has_chinese_language() and self._has_hsk_data()
        self.showHSK.setVisible(visible)
        if hasattr(self, "_hsk_group") and self._hsk_group is not None:
            self._hsk_group.setVisible(visible)

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
        visLayout.addWidget(self.showHSK)
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

        self._hsk_group = QGroupBox("Chinese HSK Configuration")
        hskLayout = QFormLayout()
        hskLayout.addRow("HSK Version Preference:", self.hskMode)
        hskHint = QLabel(
            "For Chinese, choose HSK 3.0 (9 levels), HSK 2.0 (6 levels), or show both simultaneously."
        )
        hskHint.setStyleSheet("font-size: 10px; color: gray;")
        hskLayout.addRow("", hskHint)
        self._hsk_group.setLayout(hskLayout)
        layout.addWidget(self._hsk_group)

        layout.addStretch()

    def load_config(self, config: Dict[str, Any]) -> None:
        self.freqStarChar.setText(config.get("star_char", "★"))
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
        self.showHSK.setChecked(config.get("show_hsk", True))

        hsk_mode = config.get("hsk_mode", "hsk3")
        index = self.hskMode.findData(hsk_mode)
        if index != -1:
            self.hskMode.setCurrentIndex(index)

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
        config["show_hsk"] = self.showHSK.isChecked()
        config["hsk_mode"] = self.hskMode.currentData()
