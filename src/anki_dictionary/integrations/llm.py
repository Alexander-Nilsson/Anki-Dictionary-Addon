# -*- coding: utf-8 -*-
"""
LLM API Integration for Anki Dictionary.
"""

import requests
import json
from typing import Optional, Dict, Any, Callable
from aqt.qt import QObject, pyqtSignal, QRunnable


class LLMWorkerSignals(QObject):
    """Signals for LLM worker."""

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()


class LLMWorker(QRunnable):
    """Worker for making LLM API calls in a separate thread."""

    def __init__(self, term: str, config: Dict[str, Any]):
        super().__init__()
        self.term = term
        self.config = config
        self.signals = LLMWorkerSignals()

    def run(self):
        """Execute the API call."""
        try:
            api_key = self.config.get("llm_api_key", "")
            base_url = self.config.get(
                "llm_base_url", "https://api.openai.com/v1/chat/completions"
            )
            model = self.config.get("llm_model", "gpt-3.5-turbo")
            prompt_template = self.config.get(
                "llm_prompt",
                "Provide a concise dictionary definition for the word: {term}",
            )

            if not api_key:
                self.signals.error_occurred.emit("LLM API key not configured")
                return

            prompt = prompt_template.replace("{term}", self.term)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }

            # Use requests for the API call
            response = requests.post(
                base_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Format as a dictionary entry
            result = {
                "term": self.term,
                "definition": content,
                "pronunciation": "",
                "altterm": "",
                "starCount": "LLM",
            }

            self.signals.result_ready.emit(result)

        except Exception as e:
            self.signals.error_occurred.emit(f"LLM Error: {str(e)}")
        finally:
            self.signals.finished.emit()
