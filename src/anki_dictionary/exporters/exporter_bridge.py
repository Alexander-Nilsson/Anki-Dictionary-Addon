"""
Card-exporter bridge — hosts the Svelte exporter page inside an AnkiWebView
and handles the JS<->Python command protocol.

The exporter window (:class:`~.card_exporter.CardExporter`) is a thin PyQt
shell around this web view; the UI itself — field editors, definition table,
media rows and the automatic-definition modal — is the Svelte app built by
``web/`` into a self-contained ``exporter.html``. Commands flow over the same
``pycmd``/``eval`` bridge the settings window uses:

    JS -> Python    "exporter:setField:<json>"  ->  handleExporterAction
    Python -> JS    self.eval("EXPORTER.setState(...)")

The reply surface (``window.EXPORTER``) is installed by
``web/src/lib/exporter-bridge.ts``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from aqt.webview import AnkiWebView

from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


def _svelte_exporter_path(addon_path: str) -> str:
    """Locate the built exporter.html bundle (source checkout or packaged)."""
    candidates = (
        os.path.join(addon_path, "web", "dist", "exporter.html"),
        os.path.join(addon_path, "assets", "web", "exporter.html"),
    )
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]  # Last resort: report the intended path


class ExporterBridge(AnkiWebView):
    """AnkiWebView hosting the card exporter Svelte app."""

    def __init__(self, exporter: Any, addon_path: str, theme_manager: Any) -> None:
        super().__init__()
        self.exporter = exporter
        self.addon_path = addon_path
        self.theme_manager = theme_manager
        self.onBridgeCmd = self.handleExporterAction
        # State pushed before the page announced itself is dropped by the
        # webview, so buffer the fact that a push is owed instead.
        self._page_ready = False
        self.loadExporterPage()

    def loadExporterPage(self) -> None:
        html_path = _svelte_exporter_path(self.addon_path)
        if os.path.isfile(html_path):
            with open(html_path, encoding="utf-8") as fh:
                html = fh.read()
        else:
            logger.error("Exporter bundle not found at %s", html_path)
            html = "<html><body><h1>Card exporter bundle not found</h1></body></html>"
        html = html.replace('<style id="customThemeCss"></style>', self.theme_css())
        self.setHtml(html)

    def theme_css(self) -> str:
        """Theme CSS for the exporter page (falls back to bundled defaults)."""
        try:
            from ..ui.theme_controller import generate_settings_css, get_theme_dict

            return generate_settings_css(get_theme_dict(self.theme_manager))
        except Exception:
            logger.debug("Could not generate exporter theme css", exc_info=True)
            return '<style id="customThemeCss"></style>'

    # ── reply helpers ──────────────────────────────────────

    def push(self, name: str, payload: Any) -> None:
        """Send a JSON payload to the JS reply surface via eval."""
        try:
            self.eval(f"EXPORTER.{name}({json.dumps(payload, ensure_ascii=False)})")
        except Exception as e:
            logger.error(f"exporter bridge eval({name}) failed: {e}")

    def push_state(self) -> None:
        """Replace the page's whole state with Python's."""
        if self._page_ready:
            self.push("setState", self.exporter.web_state())

    def repaint_theme(self) -> None:
        self.push("setThemeCss", self.theme_css())

    # ── command handler ────────────────────────────────────

    def handleExporterAction(self, dAct: str) -> None:
        try:
            self._handle(dAct)
        except Exception:
            logger.exception("exporter bridge command failed: %s", dAct[:120])

    def _handle(self, dAct: str) -> None:
        exporter = self.exporter
        if dAct == "exporterLoaded":
            self._page_ready = True
            self.push_state()
        elif dAct == "exporter:getState":
            self.push_state()
        elif dAct.startswith("exporter:setField:"):
            payload = json.loads(dAct[len("exporter:setField:") :])
            exporter.set_web_field(payload.get("field", ""), payload.get("value"))
        elif dAct.startswith("exporter:add:"):
            exporter.apply_web_state(json.loads(dAct[len("exporter:add:") :]))
            exporter.addCard()
        elif dAct == "exporter:clear":
            exporter.clearCurrent()
        elif dAct == "exporter:close":
            exporter.window.close()
        elif dAct == "exporter:playAudio":
            exporter.playAudio()
        elif dAct.startswith("exporter:removeDefinition:"):
            raw = dAct[len("exporter:removeDefinition:") :]
            try:
                exporter.removeDefinitionAt(int(raw))
            except ValueError:
                logger.error("exporter:removeDefinition got a non-integer index")
        elif dAct.startswith("exporter:search:"):
            payload = json.loads(dAct[len("exporter:search:") :])
            exporter.searchSelected(
                str(payload.get("text", "")), bool(payload.get("inBrowser"))
            )
        elif dAct.startswith("exporter:saveDefinitionSettings:"):
            rows = json.loads(dAct[len("exporter:saveDefinitionSettings:") :])
            exporter.saveDefinitionSettings(rows)
        else:
            logger.debug("Unhandled exporter command: %s", dAct[:80])
