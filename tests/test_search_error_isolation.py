"""External-service failures must never reach Anki's error dialog.

Forvo, the LLM and image search all report back from background workers via Qt
signals. An exception raised inside a Qt slot escapes into C++ and Anki turns
it into an error popup — so a lookup that merely failed, or a webview that was
destroyed mid-flight, has to be swallowed and logged instead.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from anki_dictionary.core.search.coordinator import ExternalServiceCoordinator


def _boom(*_args, **_kwargs):
    raise RuntimeError("webview destroyed")


class TestCoordinatorErrorIsolation(unittest.TestCase):
    def _coordinator(self, **callbacks):
        return ExternalServiceCoordinator(
            eval_fn=MagicMock(), threadpool=MagicMock(), **callbacks
        )

    def test_forvo_error_callback_cannot_escape(self):
        coord = self._coordinator(on_forvo_error=_boom)
        # Must not raise.
        coord._on_forvo_error({"error": "HTTP 403", "idName": "forvo-loader"})

    def test_forvo_result_callback_cannot_escape(self):
        coord = self._coordinator(on_forvo_result=_boom)
        coord._on_forvo_result({"items": [{"audio_url": "x"}], "idName": "f"})

    def test_llm_callbacks_cannot_escape(self):
        coord = self._coordinator(on_llm_result=_boom, on_llm_error=_boom)
        coord._on_llm_result({"idName": "llm"})
        coord._on_llm_error({"error": "nope", "idName": "llm"})

    def test_a_dead_webview_cannot_escape_when_removing_a_section(self):
        coord = ExternalServiceCoordinator(eval_fn=_boom, threadpool=MagicMock())
        # No forvo callback registered -> falls through to _remove_element,
        # which evals against a webview that has gone away.
        coord._on_forvo_error({"error": "HTTP 403", "idName": "forvo-loader"})

    def test_streaming_image_handlers_cannot_escape(self):
        coord = ExternalServiceCoordinator(eval_fn=_boom, threadpool=MagicMock())
        coord._on_image_results(("<div></div>", "gcon1"))
        coord._on_image_ready(["imgslot-a-0", "<div></div>"])
        coord._on_images_finished(["token", 3])


class TestPipelineErrorIsolation(unittest.TestCase):
    def test_removing_the_forvo_section_survives_a_dead_webview(self):
        from anki_dictionary.core.search.pipeline import SearchPipeline

        pipeline = SearchPipeline.__new__(SearchPipeline)
        pipeline.midict = MagicMock()
        pipeline.midict.eval.side_effect = _boom
        pipeline.onForvoError({"error": "HTTP 403", "idName": "forvo-loader"})


if __name__ == "__main__":
    unittest.main()
