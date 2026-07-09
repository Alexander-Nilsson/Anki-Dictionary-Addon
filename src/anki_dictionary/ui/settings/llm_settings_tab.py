from __future__ import annotations

from typing import Any

from aqt.qt import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class _PromptRow(QWidget):
    """A single prompt row: checkbox + QTextEdit + Remove button."""

    def __init__(
        self, text: str = "", active: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._active_checkbox = QCheckBox()
        self._active_checkbox.setChecked(active)
        self._active_checkbox.setToolTip(
            "Uncheck to disable this prompt without deleting it"
        )
        self._active_checkbox.stateChanged.connect(self._on_toggle)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setFixedHeight(80)
        self.text_edit.setPlainText(text)

        self.remove_btn = QPushButton("\u2715")
        self.remove_btn.setFixedSize(30, 30)
        self.remove_btn.setToolTip("Remove this prompt")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(self._active_checkbox, 0)
        layout.addWidget(self.text_edit, 1)
        layout.addWidget(self.remove_btn, 0)

        self._apply_stylesheet()

    def is_active(self) -> bool:
        return self._active_checkbox.isChecked()

    def _on_toggle(self) -> None:
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        opacity = "1.0" if self.is_active() else "0.45"
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background-color: rgba(128, 128, 128, 0.05); opacity: {opacity}; }}"
        )


DEFAULT_SINGLE_PROMPT = "Provide a concise dictionary definition for the word: {term}"


class LLMSettingsTab(QWidget):
    def __init__(self, mw: Any, addon_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mw = mw
        self.addon_path = addon_path

        self.llmEnabled = QCheckBox()
        self.llmApiKey = QLineEdit()
        self.llmApiKey.setEchoMode(QLineEdit.EchoMode.Password)
        self.llmBaseUrl = QLineEdit()
        self.llmModel = QLineEdit()
        self.llmTemperature = QDoubleSpinBox()
        self.llmTemperature.setRange(0.0, 2.0)
        self.llmTemperature.setSingleStep(0.1)
        self.llmTemperature.setDecimals(1)
        self.llmKeepAlive = QLineEdit()
        self.llmKeepAlive.setPlaceholderText("e.g., 30m, 1h, 0")
        self.llmThink = QCheckBox()
        self.llmStream = QCheckBox()
        self.llmGetPronunciation = QCheckBox(
            "Get pronunciation from first dictionary entry"
        )
        self.testLLMButton = QPushButton("Test API Connection")
        self.testLLMButton.clicked.connect(self.test_llm)
        self.llmStatusLabel = QLabel("")
        self.llmStatusLabel.setWordWrap(True)
        self.llmStatusLabel.setStyleSheet("font-weight: bold;")

        # Dynamic prompt rows
        self._prompt_rows: list[_PromptRow] = []
        self._prompts_container = QVBoxLayout()
        self._prompts_label = QLabel("Prompt Templates:")
        self._prompts_hint = QLabel(
            "Each prompt becomes a separate request. Responses are joined as independent definitions."
            " Use {term} as a placeholder for the word being searched."
        )
        self._prompts_hint.setStyleSheet("font-size: 10px; color: gray;")
        self._prompts_hint.setWordWrap(True)
        self._add_prompt_btn = QPushButton("+ Add Prompt")
        self._add_prompt_btn.clicked.connect(lambda: self._add_prompt_row())

        self._build_ui()

    # --- Prompt rows management ---

    def _add_prompt_row(self, text: str = "", active: bool = True) -> _PromptRow:
        if not isinstance(text, str):
            text = str(text) if text else ""
        row = _PromptRow(text, active)
        row.remove_btn.clicked.connect(lambda: self._remove_prompt_row(row))
        self._prompt_rows.append(row)
        self._prompts_container.addWidget(row)
        return row

    def _remove_prompt_row(self, row: _PromptRow) -> None:
        if len(self._prompt_rows) <= 1:
            return  # Keep at least one prompt
        self._prompt_rows.remove(row)
        self._prompts_container.removeWidget(row)
        row.deleteLater()

    def _clear_prompt_rows(self) -> None:
        for row in list(self._prompt_rows):
            self._prompts_container.removeWidget(row)
            row.deleteLater()
        self._prompt_rows.clear()

    # --- UI building ---

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        infoLabel = QLabel(
            "Configure an OpenAI-compatible LLM to get AI-generated definitions."
        )
        infoLabel.setWordWrap(True)
        infoLabel.setStyleSheet("font-style: italic; margin-bottom: 10px;")
        layout.addWidget(infoLabel)

        formGroup = QGroupBox("LLM Configuration")
        formLayout = QFormLayout()

        formLayout.addRow("Enable LLM Dictionary:", self.llmEnabled)
        formLayout.addRow("API Key:", self.llmApiKey)
        formLayout.addRow("Base URL:", self.llmBaseUrl)

        baseUrlHint = QLabel(
            "Supports Ollama (e.g., http://localhost:11434/api/chat) or OpenAI-style endpoints."
        )
        baseUrlHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", baseUrlHint)

        formLayout.addRow("Model:", self.llmModel)
        formLayout.addRow("Temperature:", self.llmTemperature)
        formLayout.addRow("Keep Alive:", self.llmKeepAlive)
        formLayout.addRow("Enable Thinking", self.llmThink)
        formLayout.addRow("Enable Streaming:", self.llmStream)
        formLayout.addRow("", self.llmGetPronunciation)

        formGroup.setLayout(formLayout)
        layout.addWidget(formGroup)

        # --- Prompt templates section ---
        layout.addWidget(self._prompts_label)
        layout.addWidget(self._prompts_hint)

        # Start with one empty prompt row (populated in load_config)
        self._add_prompt_row()
        layout.addLayout(self._prompts_container)
        layout.addWidget(self._add_prompt_btn)

        # --- Test button ---
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.testLLMButton)
        buttonLayout.addWidget(self.llmStatusLabel)
        buttonLayout.addStretch()
        layout.addLayout(buttonLayout)

        layout.addStretch()

    # --- Load / Save ---

    def load_config(self, config: dict[str, Any]) -> None:
        self.llmEnabled.setChecked(config.get("llm_enabled", False))
        self.llmApiKey.setText(config.get("llm_api_key", ""))
        self.llmBaseUrl.setText(
            config.get("llm_base_url", "https://api.openai.com/v1/chat/completions")
        )
        self.llmModel.setText(config.get("llm_model", "gpt-3.5-turbo"))
        self.llmTemperature.setValue(config.get("llm_temperature", 0.3))
        self.llmKeepAlive.setText(config.get("llm_keep_alive", "30m"))
        self.llmThink.setChecked(config.get("llm_think", False))
        self.llmStream.setChecked(config.get("llm_stream", False))
        self.llmGetPronunciation.setChecked(config.get("llm_get_pronunciation", False))

        # Load prompts: prefer llm_prompts (list of strings or dicts),
        # fall back to llm_prompt (string)
        prompts = config.get("llm_prompts")
        if not prompts:
            single = config.get("llm_prompt", DEFAULT_SINGLE_PROMPT)
            prompts = [single]

        self._clear_prompt_rows()
        if not prompts:
            self._add_prompt_row()
        else:
            for entry in prompts:
                if isinstance(entry, dict):
                    text = entry.get("text", "")
                    active = entry.get("active", True)
                else:
                    text = str(entry) if entry else ""
                    active = True  # migrate old plain-string format
                self._add_prompt_row(text, active)

    def save_config(self, config: dict[str, Any]) -> None:
        config["llm_enabled"] = self.llmEnabled.isChecked()
        config["llm_api_key"] = self.llmApiKey.text()
        config["llm_base_url"] = self.llmBaseUrl.text()
        config["llm_model"] = self.llmModel.text()
        config["llm_temperature"] = self.llmTemperature.value()
        config["llm_keep_alive"] = self.llmKeepAlive.text()
        config["llm_think"] = self.llmThink.isChecked()
        config["llm_stream"] = self.llmStream.isChecked()
        config["llm_get_pronunciation"] = self.llmGetPronunciation.isChecked()

        # Save all prompts as array of dicts with active state
        prompts = [
            {"text": row.text_edit.toPlainText(), "active": row.is_active()}
            for row in self._prompt_rows
        ]
        config["llm_prompts"] = prompts
        # Keep llm_prompt synced for backwards compatibility (first active prompt)
        first_active = next(
            (p["text"] for p in prompts if p["active"] and p["text"]),
            None,
        )
        config["llm_prompt"] = first_active or DEFAULT_SINGLE_PROMPT

    # --- Tooltips ---

    def init_tooltips(self) -> None:
        self.llmTemperature.setToolTip(
            "Controls randomness: Lower is more focused/deterministic, higher is more creative."
        )
        self.llmKeepAlive.setToolTip(
            "How long the model stays loaded in memory after the request (e.g., '30m', '1h'). Set to '0' to unload immediately."
        )
        self.llmThink.setToolTip(
            "If enabled, internal reasoning/thinking tags (like <think>) will be visible in the results. Currently supported by models like DeepSeek."
        )
        self.llmStream.setToolTip(
            "Enable streaming response. Note: The addon currently waits for the full response before displaying, but this can affect API behavior."
        )
        self.llmGetPronunciation.setToolTip(
            "When enabled, the LLM heading will show pronunciation from the first dictionary "
            "entry (in group order) that has pronunciation data."
        )

    # --- Test ---

    def test_llm(self) -> None:
        self.testLLMButton.setEnabled(False)
        self.testLLMButton.setText("Testing...")
        self.llmStatusLabel.setText("Testing...")
        self.llmStatusLabel.setStyleSheet("color: blue; font-weight: bold;")

        config = {
            "llm_api_key": self.llmApiKey.text().strip(),
            "llm_base_url": self.llmBaseUrl.text().strip(),
            "llm_model": self.llmModel.text().strip(),
        }

        from ...integrations.llm import test_llm_config

        def run_test() -> dict:
            result_data = {"success": False, "message": ""}

            def test_callback(success: bool, message: str) -> None:
                result_data["success"] = success
                result_data["message"] = message

            test_llm_config(config, test_callback)
            return result_data

        self.mw.taskman.run_in_background(run_test, self._on_test_finished)

    def _on_test_finished(self, future: Any) -> None:
        self.testLLMButton.setEnabled(True)
        self.testLLMButton.setText("Test API Connection")

        try:
            result = future.result()
            success = result["success"]
            message = result["message"]

            if success:
                self.llmStatusLabel.setText(message)
                self.llmStatusLabel.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.llmStatusLabel.setText(message)
                self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            msg = f"Test crashed with error: {str(e)}"
            self.llmStatusLabel.setText(msg)
            self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
