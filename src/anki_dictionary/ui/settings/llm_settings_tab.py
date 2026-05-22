from __future__ import annotations

from typing import Any, Dict

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
from aqt.utils import showInfo

from ...utils.common import miInfo


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
        self.llmPrompt = QTextEdit()
        self.llmPrompt.setAcceptRichText(False)
        self.llmPrompt.setFixedHeight(100)
        self.llmTemperature = QDoubleSpinBox()
        self.llmTemperature.setRange(0.0, 2.0)
        self.llmTemperature.setSingleStep(0.1)
        self.llmTemperature.setDecimals(1)
        self.llmKeepAlive = QLineEdit()
        self.llmKeepAlive.setPlaceholderText("e.g., 30m, 1h, 0")
        self.llmThink = QCheckBox()
        self.llmStream = QCheckBox()
        self.testLLMButton = QPushButton("Test API Connection")
        self.testLLMButton.clicked.connect(self.test_llm)
        self.llmStatusLabel = QLabel("")
        self.llmStatusLabel.setWordWrap(True)
        self.llmStatusLabel.setStyleSheet("font-weight: bold;")

        self._build_ui()

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
        formLayout.addRow("Prompt Template:", self.llmPrompt)

        promptHint = QLabel("Use {term} as a placeholder for the word being searched.")
        promptHint.setStyleSheet("font-size: 10px; color: gray;")
        formLayout.addRow("", promptHint)

        formGroup.setLayout(formLayout)
        layout.addWidget(formGroup)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.testLLMButton)
        buttonLayout.addWidget(self.llmStatusLabel)
        buttonLayout.addStretch()
        layout.addLayout(buttonLayout)

        layout.addStretch()

    def load_config(self, config: Dict[str, Any]) -> None:
        self.llmEnabled.setChecked(config.get("llm_enabled", False))
        self.llmApiKey.setText(config.get("llm_api_key", ""))
        self.llmBaseUrl.setText(
            config.get("llm_base_url", "https://api.openai.com/v1/chat/completions")
        )
        self.llmModel.setText(config.get("llm_model", "gpt-3.5-turbo"))
        self.llmPrompt.setPlainText(
            config.get(
                "llm_prompt",
                "Provide a concise dictionary definition for the word: {term}",
            )
        )
        self.llmTemperature.setValue(config.get("llm_temperature", 0.3))
        self.llmKeepAlive.setText(config.get("llm_keep_alive", "30m"))
        self.llmThink.setChecked(config.get("llm_think", False))
        self.llmStream.setChecked(config.get("llm_stream", False))

    def save_config(self, config: Dict[str, Any]) -> None:
        config["llm_enabled"] = self.llmEnabled.isChecked()
        config["llm_api_key"] = self.llmApiKey.text()
        config["llm_base_url"] = self.llmBaseUrl.text()
        config["llm_model"] = self.llmModel.text()
        config["llm_prompt"] = self.llmPrompt.toPlainText()
        config["llm_temperature"] = self.llmTemperature.value()
        config["llm_keep_alive"] = self.llmKeepAlive.text()
        config["llm_think"] = self.llmThink.isChecked()
        config["llm_stream"] = self.llmStream.isChecked()

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
                self.llmStatusLabel.setText("Success!")
                self.llmStatusLabel.setStyleSheet("color: green; font-weight: bold;")
                showInfo(message, self)
            else:
                self.llmStatusLabel.setText("Failed!")
                self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
                miInfo(message, self)
        except Exception as e:
            self.llmStatusLabel.setText("Error!")
            self.llmStatusLabel.setStyleSheet("color: red; font-weight: bold;")
            miInfo(f"Test crashed with error: {str(e)}", self)
