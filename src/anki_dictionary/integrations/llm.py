# -*- coding: utf-8 -*-
"""
LLM API Integration for Anki Dictionary.
Supports OpenAI-compatible APIs like OpenAI, llama.cpp, vLLM, Ollama, etc.
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

            # API key is optional for local providers like llama.cpp or vLLM
            # but usually required for cloud providers.
            
            prompt = prompt_template.replace("{term}", self.term)

            headers = {
                "Content-Type": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "think": self.config.get("llm_think", False),
                "temperature": 0.3,
            }

            # Use requests for the API call
            response = requests.post(
                base_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            
            # Extract content from response
            content = ""
            # OpenAI format
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
            # Ollama /api/chat format
            elif "message" in data and "content" in data["message"]:
                content = data["message"]["content"]
            # Ollama /api/generate format
            elif "response" in data:
                content = data["response"]
            else:
                raise ValueError("Unexpected API response format: " + json.dumps(data))

            # Format as a dictionary entry
            result = {
                "term": self.term,
                "definition": content.strip(),
                "pronunciation": "",
                "altterm": "",
                "starCount": "LLM",
                "dictName": "LLM API",
            }

            self.signals.result_ready.emit(result)

        except Exception as e:
            self.signals.error_occurred.emit(f"LLM Error: {str(e)}")
        finally:
            self.signals.finished.emit()


def test_llm_config(config: Dict[str, Any], callback: Callable[[bool, str], None]):
    """
    Test the LLM configuration with a simple ping.
    This runs synchronously and should be called from a thread.
    """
    print(f"Testing LLM connection to {config.get('llm_base_url')}...")
    try:
        api_key = config.get("llm_api_key", "")
        base_url = config.get(
            "llm_base_url", "https://api.openai.com/v1/chat/completions"
        )
        model = config.get("llm_model", "gpt-3.5-turbo")
        
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Simple test prompt
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, respond with only the word 'OK'."}],
            "max_tokens": 10,
            "stream": False,
            "think": config.get("llm_think", False),
            "temperature": 0.1,
        }

        print(f"Sending request to {base_url} with model {model}...")
        response = requests.post(
            base_url, headers=headers, json=payload, timeout=10
        )
        print(f"Response received: status code {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        if "choices" in data or "message" in data or "response" in data:
            print("Test successful!")
            callback(True, "Successfully connected to LLM API!")
        else:
            print(f"Test failed: unexpected response format: {data}")
            callback(False, f"Connected but got unexpected response: {json.dumps(data)[:100]}...")
            
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        callback(False, f"Connection failed: {str(e)}")

