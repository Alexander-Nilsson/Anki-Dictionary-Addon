# -*- coding: utf-8 -*-
"""
LLM Integration for Anki Dictionary.
Supports OpenAI-compatible APIs and Ollama /api/chat.
"""

import requests
import json
import re
from typing import Optional, Dict, Any, Callable, Tuple

from ..utils.logger import get_logger

logger = get_logger("LLM")

try:
    from aqt.qt import QObject, pyqtSignal, QRunnable
except ImportError:
    # Fallback to standard PyQt6 for standalone testing/development
    from PyQt6.QtCore import QObject, pyqtSignal, QRunnable


class LLMWorkerSignals(QObject):
    """Signals for LLM worker."""

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(dict)
    finished = pyqtSignal()


def prepare_llm_payload(
    base_url: str, model: str, content: str, config: Dict[str, Any], is_test: bool = False
) -> Dict[str, Any]:
    """
    Prepare the request payload based on the endpoint type.
    Handles Ollama /api/chat and standard OpenAI formats.
    """
    is_ollama_chat = base_url.endswith("/api/chat")
    
    # Get user configurable parameters
    temperature = config.get("llm_temperature", 0.3)
    keep_alive = config.get("llm_keep_alive", "30m")
    think = config.get("llm_think", False)
    stream = config.get("llm_stream", False)

    if is_ollama_chat:
        # Ollama /api/chat format
        return {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "stream": stream,
            "think": think,
            "keep_alive": keep_alive,
            "temperature": temperature,
        }
    else:
        # Standard OpenAI-compatible /v1/chat/completions format
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "stream": stream,
            "temperature": temperature,
        }
        # Connection test often needs tokens limited for speed
        if is_test:
            payload["max_tokens"] = 20
        return payload


def extract_llm_content(data: Dict[str, Any], base_url: str) -> str:
    """
    Extract the response content from various API formats.
    """
    # OpenAI /v1/chat/completions format
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            return choice["message"]["content"]
        elif "text" in choice:
            return choice["text"]

    # Ollama /api/chat format or generic message
    if "message" in data and "content" in data["message"]:
        return data["message"]["content"]

    # Generic response/content fields
    if "response" in data:
        return data["response"]

    if "content" in data:
        if isinstance(data["content"], list) and len(data["content"]) > 0:
            content = data["content"][0].get("text", "")
            if content:
                return content
        return str(data["content"])

    raise ValueError(
        f"Unexpected API response format from {base_url}. Received keys: {list(data.keys())}"
    )


def clean_llm_content(content: str, config: Dict[str, Any]) -> str:
    """
    Remove thinking tags and perform basic cleanup based on configuration.
    """
    if not content:
        return ""
    
    # Remove thinking tags if NOT explicitly enabled in config
    if not config.get("llm_think", False):
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        
    return content.strip()



class LLMWorker(QRunnable):
    """Worker for making LLM calls in a separate thread."""

    def __init__(
        self,
        term: str,
        config: Dict[str, Any],
        star_count: str = "",
        hsk_level: str = "",
        idName: str = "",
    ):
        super().__init__()
        self.term = term
        self.config = config
        self.star_count = star_count
        self.hsk_level = hsk_level
        self.idName = idName  # Track the UI tab ID
        self.signals = LLMWorkerSignals()
        # Allow custom timeout via config, default to 15 seconds
        self.timeout = config.get("llm_timeout", 15)

    def run(self):
        """Execute the API call."""
        try:
            api_key = self.config.get("llm_api_key", "")
            base_url = self.config.get(
                "llm_base_url", "https://api.openai.com/v1/chat/completions"
            ).strip()
            model = self.config.get("llm_model", "gpt-3.5-turbo")
            prompt_template = self.config.get(
                "llm_prompt",
                "Provide a concise dictionary definition for the word: {term}",
            )

            prompt = prompt_template.replace("{term}", self.term)

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = prepare_llm_payload(base_url, model, prompt, self.config)

            logger.debug(f"[LLM] Sending request to {base_url}")
            response = requests.post(
                base_url, headers=headers, json=payload, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            raw_content = extract_llm_content(data, base_url)
            content = clean_llm_content(raw_content, self.config)

            if not content:

                raise ValueError("API returned an empty response.")

            # Format as a dictionary entry
            result = {
                "term": self.term,
                "definition": content,
                "pronunciation": "",
                "altterm": "",
                "starCount": self.star_count,
                "hskLevel": self.hsk_level,
                "dictName": "LLM",
                "idName": self.idName,  # Send the ID back to the frontend
            }

            self.signals.result_ready.emit(result)

        except Exception as e:
            error_msg = f"LLM Error: {str(e)}"
            logger.debug(f"[LLM] {error_msg}")
            self.signals.error_occurred.emit(
                {"error": error_msg, "idName": self.idName}
            )
        finally:
            self.signals.finished.emit()


def test_llm_config(config: Dict[str, Any], callback: Callable[[bool, str], None]):
    """
    Test the LLM configuration with a simple ping.
    This runs synchronously and should be called from a thread.
    """
    base_url = config.get(
        "llm_base_url", "https://api.openai.com/v1/chat/completions"
    ).strip()
    logger.debug(f"Testing LLM connection to {base_url}...")

    try:
        api_key = config.get("llm_api_key", "")
        model = config.get("llm_model", "gpt-3.5-turbo")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = prepare_llm_payload(
            base_url, model, "Hello, respond with only the word 'OK'.", config, is_test=True
        )

        logger.debug(f"Sending test request to {base_url}")
        response = requests.post(base_url, headers=headers, json=payload, timeout=10)
        logger.debug(f"Response received: status code {response.status_code}")
        response.raise_for_status()

        data = response.json()
        content = clean_llm_content(extract_llm_content(data, base_url), config)

        if content:

            logger.debug("Test successful!")
            callback(True, "Successfully connected to LLM!")
        else:
            callback(False, "Connected but got empty response.")

    except Exception as e:
        logger.debug(f"Test failed with error: {str(e)}")
        callback(False, f"Connection failed: {str(e)}")
