from __future__ import annotations

import json
import os
from typing import Any

from aqt.qt import (
    QCheckBox,
    QComboBox,
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

from ...core.word_list_registry import WordListProvider, WordListRegistry
from ...utils.paths import get_word_lists_dir

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

        self._list_roles: dict[str, QComboBox] = {}
        self._display_name_inputs: dict[str, QLineEdit] = {}

        self._build_ui()

    @staticmethod
    def _get_default_display_name(name: str) -> str:
        name_lower = name.lower()
        for key, val in _DEFAULT_DISPLAY_NAMES.items():
            if key in name_lower:
                return val
        return name

    def _discover_providers(self) -> dict[str, WordListProvider]:
        providers: dict[str, WordListProvider] = {}
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
        header_lay.addWidget(QLabel("Role"))
        header_lay.addWidget(QLabel("List"))
        header_lay.addStretch()
        header_lay.addWidget(QLabel("Display Name"))
        visLayout.addLayout(header_lay)

        _RANK_ROLES = [
            ("stars_rank", "Stars + Rank"),
            ("stars", "Stars only"),
            ("rank", "Rank only"),
            ("off", "Off"),
        ]
        _LEVEL_ROLES = [
            ("level", "Level"),
            ("off", "Off"),
        ]

        for key, provider in sorted(self._discover_providers().items()):
            row = QHBoxLayout()
            combo = QComboBox()
            roles = _RANK_ROLES if provider.type == "rank" else _LEVEL_ROLES
            for role_key, role_label in roles:
                combo.addItem(role_label, role_key)
            combo.setCurrentIndex(0)
            self._list_roles[key] = combo
            row.addWidget(combo)

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

        self._files_container = QVBoxLayout()
        self._build_installed_files_section(layout)

        layout.addStretch()

    def _build_installed_files_section(self, layout: QVBoxLayout) -> None:
        group = QGroupBox("Installed Word List Files")
        glayout = QVBoxLayout()

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_installed_files)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        glayout.addLayout(toolbar)

        glayout.addLayout(self._files_container)
        self._refresh_installed_files()

        group.setLayout(glayout)
        layout.addWidget(group)

    def _file_analysis(
        self,
        filepath: str,
    ) -> dict:
        result: dict = {
            "type": "unknown",
            "status": "unknown",
            "lang_prefix": "",
        }
        fname = os.path.basename(filepath)
        try:
            with open(filepath, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            result["status"] = "unparseable"
            return result

        if WordListProvider._is_metadata_only(data):
            result["status"] = "metadata-only"
            return result

        type_ = WordListRegistry._detect_type(data)
        result["type"] = type_
        result["status"] = "ok"

        base = fname.replace(".json", "")
        for sep in (" ", "_"):
            parts = base.split(sep, 1)
            if len(parts) > 1:
                result["lang_prefix"] = parts[0].replace("_", " ")
                break
        return result

    def _refresh_installed_files(self) -> None:
        self._clear_layout(self._files_container)
        wl_dir = get_word_lists_dir()
        if not os.path.isdir(wl_dir):
            return

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>File</b>"), 3)
        header.addWidget(QLabel("<b>Type</b>"), 1)
        header.addWidget(QLabel("<b>Status</b>"), 1)
        header.addWidget(QLabel(""), 1)
        self._files_container.addLayout(header)

        for fname in sorted(os.listdir(wl_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(wl_dir, fname)
            analysis = self._file_analysis(fpath)

            row = QHBoxLayout()

            # Skip the nested word_lists/word_lists/ bug directory
            if os.path.isdir(fpath):
                continue

            size = os.path.getsize(fpath)
            label_parts = [fname, f" ({size:,} B)"]
            if analysis["lang_prefix"]:
                label_parts.append(f"  [{analysis['lang_prefix']}]")
            file_label = QLabel("".join(label_parts))
            row.addWidget(file_label, 3)

            type_label = QLabel(analysis["type"])
            row.addWidget(type_label, 1)

            status_map = {
                "ok": "OK",
                "metadata-only": "metadata-only (no word data)",
                "unparseable": "invalid JSON",
                "unknown": "unknown",
            }
            status_text = status_map.get(analysis["status"], analysis["status"])
            status_label = QLabel(status_text)
            if analysis["status"] != "ok":
                status_label.setStyleSheet("color: #cc4400;")
            row.addWidget(status_label, 1)

            del_btn = QPushButton("Delete")
            del_btn.setFixedWidth(60)
            del_btn.clicked.connect(
                lambda checked, p=fpath, n=fname: self._delete_word_list(p, n)
            )
            row.addWidget(del_btn, 1)

            self._files_container.addLayout(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            sub_layout = item.layout()
            if sub_layout is not None:
                while sub_layout.count():
                    ci = sub_layout.takeAt(0)
                    if ci is None:
                        continue
                    w = ci.widget()
                    if w is not None:
                        w.deleteLater()
                sub_layout.deleteLater()
            else:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

    def _delete_word_list(self, filepath: str, fname: str) -> None:
        from aqt.qt import QMessageBox

        reply = QMessageBox.question(
            self,
            "Delete Word List",
            f'Delete "{fname}"?\n\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(filepath)
        except OSError as e:
            QMessageBox.warning(self, "Error", f"Failed to delete: {e}")
            return
        if hasattr(self.mw, "miDictDB"):
            registry = getattr(self.mw.miDictDB, "_registry", None)
            if registry:
                registry.clear_cache()
            self.mw.miDictDB._extra_data_cache.clear()
        self._refresh_installed_files()

    def load_config(self, config: dict[str, Any]) -> None:
        self.freqStarChar.setText(config.get("star_char", "\u2605"))
        thresholds: list[int] = config.get(
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

        provider_roles: dict[str, str] = config.get("provider_roles", {})
        word_list_display_names: dict[str, dict[str, str]] = config.get(
            "word_list_display_names", {}
        )
        for key, combo in self._list_roles.items():
            role = provider_roles.get(key)
            if role is not None:
                idx = combo.findData(role)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            display_name = word_list_display_names.get(key.split("::")[0], {}).get(
                key.split("::")[1], ""
            )
            if display_name:
                self._display_name_inputs[key].setText(display_name)

    def save_config(self, config: dict[str, Any]) -> None:
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

        provider_roles: dict[str, str] = {}
        for key, combo in self._list_roles.items():
            role = combo.currentData()
            if role:
                provider_roles[key] = role
        config["provider_roles"] = provider_roles

        word_list_display_names: dict[str, dict[str, str]] = {}
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
