from __future__ import annotations

from typing import Any, Dict, List

from aqt.qt import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
        self.showLevelLabels = QCheckBox("Display Level Labels")
        self.showLevelLabels.setChecked(True)

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

    def _on_reapply(self) -> None:
        """Reapply frequency data to all existing dictionary entries."""
        from ...utils.config import get_addon_config, save_addon_config

        config = get_addon_config()
        langs = self.mw.miDictDB.getCurrentDbLangs()
        total = 0
        for lang in langs:
            try:
                self.mw.progress.start(label=f"Reapplying frequency data for {lang}...")
                count = self.mw.miDictDB.reapply_frequency_for_language(lang, config)
                total += count
            except Exception as e:
                from ...utils.logger import get_logger

                get_logger("frequency_settings").error(
                    "Error reapplying for %s: %s", lang, e
                )
            finally:
                self.mw.progress.finish()

        from aqt.utils import tooltip

        tooltip(
            f"Frequency data reapplied to {total} entries across {len(langs)} language(s)."
        )

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
        visLayout.addWidget(self.showLevelLabels)

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

        actionGroup = QGroupBox("Actions")
        actionLayout = QVBoxLayout()

        self.reapplyBtn = QPushButton("Reapply Frequency Data to All Existing Entries")
        self.reapplyBtn.clicked.connect(self._on_reapply)
        actionLayout.addWidget(self.reapplyBtn)

        reapplyHint = QLabel(
            "Recompute frequency ranks and star counts for all existing "
            "dictionary entries using currently downloaded word lists."
        )
        reapplyHint.setStyleSheet("font-size: 10px; color: gray;")
        reapplyHint.setWordWrap(True)
        actionLayout.addWidget(reapplyHint)

        actionGroup.setLayout(actionLayout)
        layout.addWidget(actionGroup)

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
        config["show_level_labels"] = self.showLevelLabels.isChecked()

        word_list_visibility: Dict[str, Dict[str, bool]] = {}
        for key, cb in self._list_checkboxes.items():
            lang, name = key.split("::", 1)
            if lang not in word_list_visibility:
                word_list_visibility[lang] = {}
            word_list_visibility[lang][name] = cb.isChecked()
        config["word_list_visibility"] = word_list_visibility
