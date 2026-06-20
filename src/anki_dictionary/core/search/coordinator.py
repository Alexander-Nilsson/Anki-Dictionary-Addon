from __future__ import annotations

import time
import json
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QThreadPool

from ...integrations import image_search as duckduckgoimages
from ...integrations import llm as llm_integration
from ...integrations import forvo as forvo_integration
from ...utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class ExternalServiceCoordinator:
    """Manages async external-service workers: LLM, Forvo, Image search.

    Owns the worker lifecycle, signal wiring, and result injection.
    Requires a callable ``eval_fn`` (typically ``midict.eval``) to push
    HTML into the web view, and a ``threadpool`` for background workers.
    """

    def __init__(
        self,
        eval_fn: Any,
        threadpool: QThreadPool,
        on_llm_result: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_llm_error: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._eval = eval_fn
        self._threadpool = threadpool
        self._on_llm_result_cb = on_llm_result
        self._on_llm_error_cb = on_llm_error

    # ── LLM ────────────────────────────────────────

    def trigger_llm(
        self,
        term: str,
        config: Dict[str, Any],
        star_count: str = "",
        level_labels: str = "",
        id_name: str = "",
    ) -> None:
        worker = llm_integration.LLMWorker(
            term, config, star_count, level_labels, id_name
        )
        worker.signals.result_ready.connect(self._on_llm_result)
        worker.signals.error_occurred.connect(self._on_llm_error)
        self._threadpool.start(worker)

    def _on_llm_result(self, result: Dict[str, Any]) -> None:
        if self._on_llm_result_cb is not None:
            self._on_llm_result_cb(result)

    def _on_llm_error(self, result: Dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown LLM error")
        logger.warning("LLM error: %s", error_msg)
        if self._on_llm_error_cb is not None:
            self._on_llm_error_cb(result)

    # ── Forvo ──────────────────────────────────────

    def trigger_forvo(
        self,
        term: str,
        config: Dict[str, Any],
        id_name: str = "",
        language: Optional[str] = None,
    ) -> None:
        if language is None:
            language = config.get("forvo_language", "ja")
        assert language is not None
        worker = forvo_integration.ForvoWorker(term, language, config, id_name)
        worker.signals.result_ready.connect(self._on_forvo_result)
        worker.signals.error_occurred.connect(self._on_forvo_error)
        self._threadpool.start(worker)

    def _on_forvo_result(self, result: Dict[str, Any]) -> None:
        id_name = result.get("idName") or "forvo-loader"
        items = result.get("items", [])
        if not items:
            self._remove_element(id_name, "Forvo")
            return

    def _on_forvo_error(self, result: Dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown Forvo error")
        logger.warning("Forvo unavailable: %s", error_msg)
        id_name = result.get("idName") or "forvo-loader"

    # ── Image search ───────────────────────────────

    def trigger_image_search(
        self,
        term: str,
        config: Dict[str, Any],
        id_name: str = "",
        offset: int = 0,
    ) -> None:
        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(term, id_name)
        imager.search_offset = offset
        imager.auto_convert = config.get("imageAutoConvert", True)
        imager.setSearchRegion(config.get("imageSearchRegion", "United States"))
        imager.signals.resultsFound.connect(self._on_image_results)
        imager.signals.noResults.connect(self._show_no_images)
        self._threadpool.start(imager)

    def _on_image_results(self, results: tuple) -> None:
        html, id_name = results
        if not html or html.strip() == "":
            self._show_no_images()
            return
        try:
            escaped = json.dumps(html)
            if id_name == "load_more":
                self._eval(f"appendNewImages({escaped});")
            else:
                self._eval(f"loadImageHtml({escaped}, {json.dumps(id_name)});")
        except Exception as e:
            logger.error("Error injecting image results: %s", e)

    def _show_no_images(self) -> None:
        from aqt.utils import tooltip

        tooltip("No images found")

    # ── helpers ────────────────────────────────────

    def _remove_element(self, id_name: str, label: str) -> None:
        self._eval(
            f"var el = document.getElementById('{id_name}'); "
            f"if(el) el.remove(); "
            f"var titles = document.querySelectorAll('.listTitle'); "
            f"for (var i = 0; i < titles.length; i++) {{ "
            f"  if (titles[i].textContent === '{label}') {{ "
            f"    var list = titles[i].nextElementSibling; "
            f"    if (list && list.classList.contains('foundEntriesList')) list.remove(); "
            f"    titles[i].remove(); "
            f"    break; "
            f"  }} "
            f"}}"
        )
