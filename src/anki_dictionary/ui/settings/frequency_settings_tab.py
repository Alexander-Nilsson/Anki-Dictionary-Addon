from __future__ import annotations

import json
import logging
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
    Qt,
    QVBoxLayout,
    QWidget,
)

from ...core.frequency import get_star_count
from ...core.word_list_registry import WordListProvider, WordListRegistry
from ...utils.paths import get_word_lists_dir

_DEFAULT_DISPLAY_NAMES = {"hsk": "HSK³", "jlpt": "JLPT", "cefr": "CEFR"}
logger = logging.getLogger(__name__)


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
        self._frequency_source_checkboxes: dict[str, QCheckBox] = {}
        self._preview_label = QLabel()
        self._preview_label.setTextFormat(Qt.TextFormat.RichText)
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("padding: 8px;")

        self._build_ui()
        self._wire_preview_updates()

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

    def _wire_preview_updates(self) -> None:
        self.freqStarChar.textChanged.connect(self._update_preview)
        self.freqThreshold1.valueChanged.connect(self._update_preview)
        self.freqThreshold2.valueChanged.connect(self._update_preview)
        self.freqThreshold3.valueChanged.connect(self._update_preview)
        self.freqThreshold4.valueChanged.connect(self._update_preview)
        self.freqThreshold5.valueChanged.connect(self._update_preview)
        self.showStars.stateChanged.connect(self._update_preview)
        self.showRank.stateChanged.connect(self._update_preview)
        self.showLevelLabels.stateChanged.connect(self._update_preview)

    def _update_preview(self) -> None:
        try:
            star_char = self.freqStarChar.text() or "\u2605"
            thresholds = [
                self.freqThreshold1.value(),
                self.freqThreshold2.value(),
                self.freqThreshold3.value(),
                self.freqThreshold4.value(),
                self.freqThreshold5.value(),
            ]
            show_stars = self.showStars.isChecked()
            show_rank = self.showRank.isChecked()
            show_labels = self.showLevelLabels.isChecked()

            providers_info = self._discover_providers()
            mock_freqs = [1501, 4000, 12000, 28000, 55000, 120000]

            rank_entries: list[str] = []
            star_freq: int | None = None
            level_entries: list[str] = []
            idx = 0

            for key, combo in sorted(self._list_roles.items()):
                role = combo.currentData()
                if role == "off":
                    continue

                mock_freq = mock_freqs[min(idx, len(mock_freqs) - 1)]
                idx += 1

                display_input = self._display_name_inputs.get(key)
                display_name = (
                    display_input.text().strip()
                    if display_input and display_input.text().strip()
                    else None
                )
                if not display_name:
                    provider = providers_info.get(key)
                    display_name = (
                        self._get_default_display_name(provider.name)
                        if provider
                        else key.split("::")[-1]
                    )

                if role in ("stars_rank", "stars"):
                    if star_freq is None or mock_freq < star_freq:
                        star_freq = mock_freq

                if role in ("stars_rank", "rank") and show_rank:
                    show_src = self._frequency_source_checkboxes.get(
                        key, QCheckBox()
                    ).isChecked()
                    fmt = self._format_freq_k(mock_freq)
                    if show_src:
                        rank_entries.append(f"{display_name} {fmt}")
                    else:
                        rank_entries.append(f"{fmt}")

                if role == "level":
                    level_entries.append(f"{display_name}:N3")

            parts: list[str] = []

            if show_stars and star_freq is not None:
                stars_str = get_star_count(star_freq, star_char, thresholds)
                if stars_str:
                    parts.append(f'<span class="starcount">{stars_str}</span>')

            for rank_val in rank_entries:
                parts.append(
                    f'<span class="starcount frequency-rank">[{rank_val}]</span>'
                )

            if show_labels and level_entries:
                for lev in level_entries:
                    parts.append(f'<span class="starcount level-label">{lev}</span>')

            freq_info = " " + " ".join(parts) if parts else ""
            html = (
                '<div style="display: flex; align-items: center; gap: 8px;'
                ' flex-wrap: wrap;">'
                '<span style="font-weight: 700; font-size: 15px;">例文</span>'
                '<span class="pronunciation"'
                ' style="color: #666; font-size: 13px;">れいぶん</span>'
                f"{freq_info}"
                "</div>"
            )
            self._preview_label.setText(html)
        except Exception:
            logger.exception("Failed to update frequency preview")
            self._preview_label.setText(
                '<div style="display: flex; align-items: center; gap: 8px;'
                ' flex-wrap: wrap;">'
                '<span style="font-weight: 700; font-size: 15px;">例文</span>'
                '<span class="pronunciation"'
                ' style="color: #666; font-size: 13px;">れいぶん</span>'
                "</div>"
            )

    @staticmethod
    def _format_freq_k(freq: int) -> str:
        if freq >= 10000:
            return f"{freq // 1000}k"
        whole = freq // 1000
        frac = (freq % 1000) // 100
        if frac:
            return f"{whole}.{frac}k"
        return f"{whole}k"

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        infoLabel = QLabel(
            "Configure how frequency information and level labels are displayed."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        previewGroup = QGroupBox("Preview")
        previewLayout = QVBoxLayout()
        previewLayout.addWidget(self._preview_label)
        previewGroup.setLayout(previewLayout)
        layout.addWidget(previewGroup)

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

        all_providers = list(self._discover_providers().items())
        rank_providers = [(k, v) for k, v in all_providers if v.type == "rank"]
        level_providers = [(k, v) for k, v in all_providers if v.type == "level"]

        # ── Rank (Frequency) Lists ──────────────────────
        rankGroup = QGroupBox("Rank (Frequency) Lists")
        rankLayout = QVBoxLayout()
        rankInfo = QLabel(
            "Smaller rank number = more common word. "
            "Displayed as e.g. 1.5k (= 1,500th most common)."
        )
        rankInfo.setWordWrap(True)
        rankInfo.setStyleSheet("font-size: 11px; color: gray; margin-bottom: 4px;")
        rankLayout.addWidget(rankInfo)
        rankLayout.addWidget(self.showStars)
        rankLayout.addWidget(self.showRank)

        if rank_providers:
            header = QHBoxLayout()
            header.addWidget(QLabel("<small><b>Role</b></small>"))
            header.addWidget(QLabel("<small><b>Src</b></small>"))
            header.addWidget(QLabel("<small><b>List</b></small>"))
            header.addStretch()
            header.addWidget(QLabel("<small><b>Display Name</b></small>"))
            rankLayout.addLayout(header)

            for key, provider in sorted(rank_providers):
                row = QHBoxLayout()
                combo = QComboBox()
                for role_key, role_label in _RANK_ROLES:
                    combo.addItem(role_label, role_key)
                combo.setCurrentIndex(0)
                self._list_roles[key] = combo
                row.addWidget(combo)

                src_cb = QCheckBox()
                src_cb.setToolTip(
                    "Show list name before rank number (e.g. 'JMdict [1.5k]')"
                )
                src_cb.stateChanged.connect(self._update_preview)
                self._frequency_source_checkboxes[key] = src_cb
                row.addWidget(src_cb)

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

                rankLayout.addLayout(row)
        else:
            rankLayout.addWidget(
                QLabel("No rank-based word lists found for your languages.")
            )

        rankGroup.setLayout(rankLayout)
        layout.addWidget(rankGroup)

        # ── Level Lists ──────────────────────────
        levelGroup = QGroupBox("Level Lists")
        levelLayout = QVBoxLayout()
        levelLayout.addWidget(self.showLevelLabels)

        if level_providers:
            header = QHBoxLayout()
            header.addWidget(QLabel("<small><b>Role</b></small>"))
            header.addWidget(QLabel("<small><b>List</b></small>"))
            header.addStretch()
            header.addWidget(QLabel("<small><b>Display Name</b></small>"))
            levelLayout.addLayout(header)

            for key, provider in sorted(level_providers):
                row = QHBoxLayout()
                combo = QComboBox()
                for role_key, role_label in _LEVEL_ROLES:
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

                levelLayout.addLayout(row)
        else:
            levelLayout.addWidget(
                QLabel("No level-based word lists found for your languages.")
            )

        levelGroup.setLayout(levelLayout)
        layout.addWidget(levelGroup)

        # ── Star Configuration ────────────────────
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

        files_by_lang: dict[str, list[tuple[str, str, dict]]] = {}
        for fname in sorted(os.listdir(wl_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(wl_dir, fname)
            if os.path.isdir(fpath):
                continue  # Skip nested word_lists/ bug directory
            analysis = self._file_analysis(fpath)
            lang = analysis.get("lang_prefix") or "Other"
            files_by_lang.setdefault(lang, []).append((fname, fpath, analysis))

        for lang in sorted(files_by_lang, key=lambda x: (x == "Other", x)):
            entries = files_by_lang[lang]
            count = len(entries)
            group = QGroupBox(f"{lang}  ({count})")
            group.setCheckable(True)
            group.setChecked(False)
            group.setStyleSheet("QGroupBox::indicator { width: 14px; height: 14px; }")
            glayout = QVBoxLayout()

            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)

            for fname, fpath, analysis in entries:
                row = QHBoxLayout()

                size = os.path.getsize(fpath)
                file_label = QLabel(f"{fname}  ({size:,} B)")
                row.addWidget(file_label, 3)

                type_label = QLabel(analysis["type"])
                row.addWidget(type_label, 1)

                status_map = {
                    "ok": "OK",
                    "metadata-only": "metadata-only",
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

                content_layout.addLayout(row)

            group.toggled.connect(content_widget.setVisible)
            content_widget.setVisible(False)
            glayout.addWidget(content_widget)
            group.setLayout(glayout)
            self._files_container.addWidget(group)

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

        frequency_source_visibility: dict[str, bool] = config.get(
            "frequency_source_visibility", {}
        )
        for key, cb in self._frequency_source_checkboxes.items():
            cb.setChecked(frequency_source_visibility.get(key, False))

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

        self._update_preview()

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
        config.pop("show_frequency_source_name", None)

        frequency_source_visibility: dict[str, bool] = {}
        for key, cb in self._frequency_source_checkboxes.items():
            frequency_source_visibility[key] = cb.isChecked()
        config["frequency_source_visibility"] = frequency_source_visibility

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
