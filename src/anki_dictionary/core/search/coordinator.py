from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QThreadPool

from ...integrations import forvo as forvo_integration
from ...integrations import image_search as duckduckgoimages
from ...integrations import llm as llm_integration
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
        on_llm_result: Callable[[dict[str, Any]], None] | None = None,
        on_llm_error: Callable[[dict[str, Any]], None] | None = None,
        on_forvo_result: Callable[[dict[str, Any]], None] | None = None,
        on_forvo_error: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._eval = eval_fn
        self._threadpool = threadpool
        self._on_llm_result_cb = on_llm_result
        self._on_llm_error_cb = on_llm_error
        self._on_forvo_result_cb = on_forvo_result
        self._on_forvo_error_cb = on_forvo_error

    # ── LLM ────────────────────────────────────────

    def trigger_llm(
        self,
        term: str,
        config: dict[str, Any],
        star_count: str = "",
        level_labels: str = "",
        id_name: str = "",
        pronunciation: str = "",
        frequency_rank: str = "",
        frequency_rank_source_display: str = "",
    ) -> None:
        worker = llm_integration.LLMWorker(
            term,
            config,
            star_count,
            level_labels,
            id_name,
            pronunciation,
            frequency_rank,
            frequency_rank_source_display,
        )
        worker.signals.result_ready.connect(self._on_llm_result)
        worker.signals.error_occurred.connect(self._on_llm_error)
        self._threadpool.start(worker)

    def _on_llm_result(self, result: dict[str, Any]) -> None:
        if self._on_llm_result_cb is not None:
            self._safe_call(self._on_llm_result_cb, result)

    def _on_llm_error(self, result: dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown LLM error")
        logger.debug("LLM error: %s", error_msg)
        if self._on_llm_error_cb is not None:
            self._safe_call(self._on_llm_error_cb, result)

    # ── Forvo ──────────────────────────────────────

    def trigger_forvo(
        self,
        term: str,
        config: dict[str, Any],
        id_name: str = "",
        language: str | None = None,
    ) -> None:
        if language is None:
            language = config.get("forvo_language", "ja")
        assert language is not None
        worker = forvo_integration.ForvoWorker(term, language, config, id_name)
        worker.signals.result_ready.connect(self._on_forvo_result)
        worker.signals.error_occurred.connect(self._on_forvo_error)
        self._threadpool.start(worker)

    def _on_forvo_result(self, result: dict[str, Any]) -> None:
        id_name = result.get("idName") or "forvo-loader"
        items = result.get("items", [])
        if not items:
            self._remove_element(id_name, "Forvo")
            return
        if self._on_forvo_result_cb is not None:
            self._safe_call(self._on_forvo_result_cb, result)

    @staticmethod
    def _safe_call(callback: Any, result: dict[str, Any]) -> None:
        """Invoke a result/error callback without letting it reach Anki.

        These fire from background-worker signals. An exception raised inside a
        Qt slot escapes into C++ and surfaces as Anki's error dialog, so a
        lookup that failed (or a webview that went away mid-flight) must never
        be able to pop one.
        """
        try:
            callback(result)
        except Exception:
            logger.exception("Search result callback failed")

    def _safe_eval(self, script: str) -> None:
        """Run JS in the results view, swallowing a destroyed-webview error.

        Called from background-worker signals: an exception raised inside a Qt
        slot escapes into C++ and surfaces as Anki's error dialog, so a failed
        lookup must never be able to raise here.
        """
        try:
            self._eval(script)
        except Exception:
            logger.debug("Webview eval failed (view may have been destroyed)")

    def _on_forvo_error(self, result: dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown Forvo error")
        logger.warning("Forvo unavailable: %s", error_msg)
        if self._on_forvo_error_cb is not None:
            self._safe_call(self._on_forvo_error_cb, result)
        else:
            id_name = result.get("idName") or "forvo-loader"
            self._remove_element(id_name, "Forvo")

    # ── Image search ───────────────────────────────

    def trigger_image_search(
        self,
        term: str,
        config: dict[str, Any],
        id_name: str = "",
        offset: int = 0,
    ) -> None:
        imager = duckduckgoimages.DuckDuckGo()
        imager.setTermIdName(term, id_name)
        imager.search_offset = offset
        imager.auto_convert = config.get("imageAutoConvert", True)
        imager.setSearchRegion(config.get("imageSearchRegion", "United States"))
        imager.signals.resultsFound.connect(self._on_image_results)
        imager.signals.imageReady.connect(self._on_image_ready)
        imager.signals.imagesFinished.connect(self._on_images_finished)
        imager.signals.noResults.connect(self._show_no_images)
        self._threadpool.start(imager)

    def _on_image_results(self, results: tuple) -> None:
        """Inject the grid shell (placeholder tiles); the images follow."""
        html, id_name = results
        if not html or html.strip() == "":
            # A "load more" that came back empty means the gallery is
            # exhausted — say so on the tile instead of a bare tooltip.
            if id_name == "load_more":
                self._eval(
                    "var btn = document.querySelector('.imageLoader'); "
                    "if (btn) { btn.textContent = 'No more images'; "
                    "btn.classList.add('exhausted'); btn.onclick = null; }"
                )
            else:
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

    def _on_image_ready(self, payload: list) -> None:
        """Fill one placeholder tile as its download lands."""
        slot_id, html = payload
        try:
            self._eval(f"fillImageSlot({json.dumps(slot_id)}, {json.dumps(html)});")
        except Exception as e:
            logger.error("Error injecting image tile: %s", e)

    def _on_images_finished(self, payload: list) -> None:
        """Drop the placeholders whose downloads never produced an image."""
        token, rendered = payload
        try:
            self._eval(f"finishImageLoad({json.dumps(token)}, {int(rendered)});")
        except Exception as e:
            logger.error("Error finishing image load: %s", e)

    def _show_no_images(self) -> None:
        from aqt.utils import tooltip

        tooltip("No images found")

    # ── helpers ────────────────────────────────────

    def _remove_element(self, id_name: str, label: str) -> None:
        self._safe_eval(
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
