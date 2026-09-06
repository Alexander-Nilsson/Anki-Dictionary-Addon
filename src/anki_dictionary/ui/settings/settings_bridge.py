"""
Settings bridge — hosts the Svelte settings page inside an AnkiWebView and
handles the JS<->Python command protocol.

The settings window (``SettingsGui``) is a thin PyQt shell around this web
view. The actual UI — all five tabs plus the dictionary-group and export-
template editors — is the Svelte app built by ``web/`` into a self-contained
``settings.html``. Commands flow over the same ``pycmd``/``eval`` bridge used
by the dictionary page:

    JS -> Python    "settings:getConfig" etc.  ->  handleSettingsAction
    Python -> JS    self.eval("SETTINGS.setConfig(...)")

The reply surface (``window.SETTINGS``) is installed by
``web/src/lib/settings-bridge.ts``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from aqt.webview import AnkiWebView

from ...utils.config import get_addon_config, save_addon_config
from ...utils.constants import FORVO_LANGUAGES
from ...utils.logger import get_logger
from ...utils.paths import get_addon_root, get_word_lists_dir

logger = get_logger(__name__.split(".")[-1])


def _svelte_settings_path(addon_path: str) -> str:
    """Locate the built settings.html bundle (source checkout or packaged)."""
    candidates = (
        os.path.join(addon_path, "web", "dist", "settings.html"),
        os.path.join(addon_path, "assets", "web", "settings.html"),
    )
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]  # Last resort: report the intended path


class SettingsBridge(AnkiWebView):
    """AnkiWebView hosting the settings Svelte app."""

    def __init__(self, settings_gui: Any, mw: Any, addon_path: str) -> None:
        super().__init__()
        self.settings_gui = settings_gui
        self.mw = mw
        self.addon_path = addon_path
        self.onBridgeCmd = self.handleSettingsAction
        # Tab requested before the page announced itself (see focus_tab).
        self._pending_tab: str | None = None
        self._page_ready = False
        self.loadSettingsPage()

    def loadSettingsPage(self) -> None:
        html_path = _svelte_settings_path(self.addon_path)
        if os.path.isfile(html_path):
            with open(html_path, encoding="utf-8") as fh:
                html = fh.read()
        else:
            logger.error("Settings bundle not found at %s", html_path)
            html = "<html><body><h1>Settings bundle not found</h1></body></html>"
        # The bundle is fully self-contained (JS + CSS inlined), so no base
        # URL is needed — matching release_notes.py's AnkiWebView usage.
        self.setHtml(html)

    # ── reply helpers ──────────────────────────────────────

    def _push(self, name: str, payload: Any) -> None:
        """Send a JSON payload to the JS reply surface via eval."""
        try:
            self.eval(f"SETTINGS.{name}({json.dumps(payload, ensure_ascii=False)})")
        except Exception as e:
            logger.error(f"settings bridge eval({name}) failed: {e}")

    def focus_tab(self, tab_id: str) -> None:
        """Ask the web UI to select a tab, buffering until the page is ready."""
        if self._page_ready:
            self._push("setActiveTab", tab_id)
        else:
            self._pending_tab = tab_id

    # ── data providers ─────────────────────────────────────

    def _dictionary_names(self) -> list[str]:
        names: list[str] = []
        try:
            for info in self.mw.miDictDB.getAllDictsWithLang():
                clean = self.mw.miDictDB.cleanDictName(info["dict"]).replace("_", " ")
                if clean and clean not in names:
                    names.append(clean)
        except Exception:
            logger.debug("Could not enumerate dictionary names", exc_info=True)
        for extra, enabled in (
            ("Images", True),
            ("LLM", self._llm_enabled()),
            ("Forvo", self._forvo_enabled()),
        ):
            if enabled and extra not in names:
                names.append(extra)
        return sorted(names, key=str.casefold)

    def _llm_enabled(self) -> bool:
        try:
            return bool(self.settings_gui.config.get("llm_enabled", False))
        except Exception:
            return False

    def _forvo_enabled(self) -> bool:
        try:
            return bool(self.settings_gui.config.get("forvo_enabled", True))
        except Exception:
            return True

    def _word_list_data(self) -> dict[str, Any]:
        """Return installed word-list files + discovered providers."""
        files: list[dict[str, Any]] = []
        providers: list[dict[str, Any]] = []
        wl_dir = get_word_lists_dir()
        try:
            if os.path.isdir(wl_dir):
                from ...core.word_list_registry import (
                    WordListProvider,
                    WordListRegistry,
                )

                for fname in sorted(os.listdir(wl_dir)):
                    fpath = os.path.join(wl_dir, fname)
                    if not fname.endswith(".json") or os.path.isdir(fpath):
                        continue
                    status = "ok"
                    ftype = "unknown"
                    try:
                        with open(fpath, encoding="utf-8-sig") as fh:
                            data = json.load(fh)
                        if WordListProvider._is_metadata_only(data):
                            status = "metadata-only"
                        else:
                            ftype = WordListRegistry._detect_type(data)
                    except (json.JSONDecodeError, OSError):
                        status = "unparseable"
                    size = os.path.getsize(fpath)
                    lang = "Other"
                    base = fname.replace(".json", "")
                    for sep in (" ", "_"):
                        parts = base.split(sep, 1)
                        if len(parts) > 1:
                            lang = parts[0].replace("_", " ")
                            break
                    files.append(
                        {
                            "name": fname,
                            "size": size,
                            "type": ftype,
                            "status": status,
                            "lang": lang,
                        }
                    )
        except Exception:
            logger.debug("Could not enumerate word list files", exc_info=True)

        try:
            registry = getattr(self.mw.miDictDB, "_registry", None)
            if registry is not None:
                seen: set[str] = set()
                for lang in self.mw.miDictDB.getCurrentDbLangs():
                    for p in registry.get_providers(lang):
                        key = f"{lang}::{p.name}"
                        if key in seen:
                            continue
                        seen.add(key)
                        providers.append(
                            {"key": key, "lang": lang, "name": p.name, "type": p.type}
                        )
        except Exception:
            logger.debug("Could not discover word list providers", exc_info=True)

        # Group installed files by language for the collapsible list.
        by_lang: dict[str, list[dict[str, Any]]] = {}
        for f in files:
            by_lang.setdefault(f.pop("lang", "Other"), []).append(f)
        grouped = [
            {"lang": lang, "files": lst}
            for lang, lst in sorted(
                by_lang.items(), key=lambda kv: (kv[0] == "Other", kv[0])
            )
        ]
        return {"files": grouped, "providers": providers}

    def _note_types(self) -> dict[str, list[str]]:
        """Return {note type name: [field names]} from Anki's collection."""
        out: dict[str, list[str]] = {}
        try:
            for model in self.mw.col.models.all():
                out[model["name"]] = [fld["name"] for fld in model["flds"]]
        except Exception:
            logger.debug("Could not load note types", exc_info=True)
        return out

    def _languages_dicts(self) -> dict[str, list[str]]:
        """Return {language: [dictionary display names]}."""
        out: dict[str, list[str]] = {}
        try:
            db = self.mw.miDictDB
            for info in db.getAllDictsWithLang():
                lang = info["lang"]
                name = db.cleanDictName(info["dict"]).replace("_", " ")
                out.setdefault(lang, []).append(name)
        except Exception:
            logger.debug("Could not load languages/dictionaries", exc_info=True)
        return out

    def _forvo_languages(self) -> list[dict[str, str]]:
        """Return the full Forvo language catalogue for the language dropdown."""
        try:
            return [
                {"code": str(x["Code"]), "name": str(x["English name"])}
                for x in FORVO_LANGUAGES
            ]
        except Exception:
            logger.debug("Could not load Forvo language list", exc_info=True)
            return []

    # ── themes ─────────────────────────────────────────────

    def _theme_manager(self) -> Any:
        """The dictionary window's manager when it exists, else a fresh one.

        Reusing the open window's instance matters: applying a theme has to
        mutate the same object the window repaints from.
        """
        dict_int = getattr(self.mw, "ankiDictionary", None)
        manager = getattr(dict_int, "theme_manager", None)
        if manager is not None:
            return manager
        from ..themes import ThemeManager

        return ThemeManager(self.addon_path)

    def _push_themes(self, manager: Any | None = None) -> None:
        tm = manager or self._theme_manager()
        try:
            themes = {
                name: vars(colors) for name, colors in tm.selectable_themes().items()
            }
            self._push(
                "setThemes",
                {
                    "themes": themes,
                    "active": tm.current_theme,
                    "builtins": tm.builtin_names,
                },
            )
        except Exception:
            logger.exception("Could not enumerate themes")
            self._push("setThemes", {"themes": {}, "active": "light", "builtins": []})

    def _repaint_dictionary(self) -> None:
        """Repaint the dictionary window if it is open; a no-op otherwise."""
        dict_int = getattr(self.mw, "ankiDictionary", None)
        if dict_int is None:
            return
        try:
            dict_int.refresh_application_theme()
        except Exception:
            logger.debug("Could not repaint the dictionary window", exc_info=True)

    def _apply_theme(self, raw: str) -> None:
        try:
            name = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("settings:applyTheme received invalid JSON payload")
            return
        tm = self._theme_manager()
        if not isinstance(name, str) or name not in tm.themes:
            logger.warning("settings:applyTheme unknown theme %r", name)
            self._push_themes(tm)
            return
        tm.set_active_theme(name)
        self._repaint_dictionary()
        self._push_themes(tm)

    def _save_theme(self, raw: str) -> None:
        from ..themes import ThemeColors

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("settings:saveTheme received invalid JSON payload")
            return
        if not isinstance(payload, dict):
            return
        name = str(payload.get("name") or "").strip()
        colors = payload.get("colors")
        if not name or not isinstance(colors, dict):
            logger.warning("settings:saveTheme ignored: missing name or colors")
            return

        tm = self._theme_manager()
        fields = set(ThemeColors.__dataclass_fields__)
        missing = fields - colors.keys()
        if missing:
            logger.warning("settings:saveTheme missing colors: %s", sorted(missing))
            return
        try:
            theme = ThemeColors(**{k: str(colors[k]) for k in fields})
        except TypeError:
            logger.exception("settings:saveTheme rejected malformed colors")
            return

        tm.save_theme(name, theme)
        if payload.get("apply", True):
            tm.set_active_theme(name)
            self._repaint_dictionary()
        self._push_themes(tm)

    def _delete_theme(self, raw: str) -> None:
        try:
            name = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("settings:deleteTheme received invalid JSON payload")
            return
        tm = self._theme_manager()
        if isinstance(name, str) and tm.delete_theme(name):
            self._repaint_dictionary()
        self._push_themes(tm)

    # ── command handler ────────────────────────────────────

    def handleSettingsAction(self, dAct: str) -> None:
        try:
            self._handle_settings_action(dAct)
        except Exception:
            logger.exception("settings bridge command failed: %s", dAct[:120])

    def _handle_settings_action(self, dAct: str) -> None:
        if dAct == "settingsLoaded":
            self._page_ready = True
            if self._pending_tab:
                self._push("setActiveTab", self._pending_tab)
                self._pending_tab = None
            return
        if dAct == "settings:getConfig":
            self._push("setConfig", self.settings_gui.config or {})
        elif dAct == "settings:getDictionaryNames":
            self._push("setDictionaryNames", self._dictionary_names())
        elif dAct == "settings:getWordListData":
            self._push("setWordListData", self._word_list_data())
        elif dAct == "settings:getNoteTypes":
            self._push("setNoteTypes", self._note_types())
        elif dAct == "settings:getLanguagesDicts":
            self._push("setLanguagesDicts", self._languages_dicts())
        elif dAct == "settings:getForvoLanguages":
            self._push("setForvoLanguages", self._forvo_languages())
        elif dAct == "settings:getThemes":
            self._push_themes()
        elif dAct.startswith("settings:applyTheme:"):
            self._apply_theme(dAct[len("settings:applyTheme:") :])
        elif dAct.startswith("settings:saveTheme:"):
            self._save_theme(dAct[len("settings:saveTheme:") :])
        elif dAct.startswith("settings:deleteTheme:"):
            self._delete_theme(dAct[len("settings:deleteTheme:") :])
        elif dAct.startswith("settings:save:"):
            raw = dAct[len("settings:save:") :]
            try:
                config = json.loads(raw)
                self._apply_config(config)
            except json.JSONDecodeError:
                logger.error("settings:save received invalid JSON payload")
            self._push("setSaved", True)
        elif dAct.startswith("settings:testLLM:"):
            raw = dAct[len("settings:testLLM:") :]
            self._run_llm_test(raw)
        elif dAct.startswith("settings:deleteWordList:"):
            raw = dAct[len("settings:deleteWordList:") :]
            self._delete_word_list(raw)
        elif dAct == "settings:restoreDefaults":
            self._restore_defaults()
        elif dAct == "settings:close":
            self.settings_gui.close()
        elif dAct.startswith("settings:removeLanguage:"):
            raw = dAct[len("settings:removeLanguage:") :]
            self._remove_language(raw)
        elif dAct in (
            "settings:webInstallDicts",
            "settings:importDicts",
            "settings:webInstallFreq",
            "settings:importFreq",
            "settings:browseFontFile",
        ):
            self._delegate_native(dAct)
        else:
            logger.debug("Unhandled settings command: %s", dAct[:80])

    # ── command implementations ────────────────────────────

    def _apply_config(self, config: dict[str, Any]) -> None:
        """Persist the staged config and refresh dependents."""
        config = dict(config)
        saved = save_addon_config(config)
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            try:
                self.mw.refreshAnkiDictConfig(config)
            except Exception:
                logger.debug("Could not refresh addon config", exc_info=True)
        self.settings_gui.config = config
        if not saved:
            logger.warning("settings:save could not persist config")
        self.settings_gui.after_save()

    def _run_llm_test(self, raw: str) -> None:
        try:
            config = json.loads(raw)
        except json.JSONDecodeError:
            config = {}

        from ...integrations.llm import test_llm_config

        def run() -> dict[str, Any]:
            result: dict[str, Any] = {
                "success": False,
                "message": "Invalid test configuration",
            }
            if not isinstance(config, dict):
                return result
            try:
                test_llm_config(
                    config,
                    lambda ok, msg: result.update({"success": ok, "message": msg}),
                )
            except Exception as e:  # noqa: BLE001 - surface any crash to the UI
                result = {"success": False, "message": f"Test crashed with error: {e}"}
            return result

        def on_done(future: Any) -> None:
            try:
                self._push("setLLMTest", future.result())
            except Exception:  # noqa: BLE001
                self._push("setLLMTest", {"success": False, "message": "Test crashed"})

        taskman = getattr(self.mw, "taskman", None)
        if taskman is not None:
            # test_llm_config performs a blocking HTTP request; never run it on
            # the UI thread.
            taskman.run_in_background(run, on_done)
        else:
            self._push("setLLMTest", run())

    def _delete_word_list(self, raw: str) -> None:
        try:
            fname = json.loads(raw)
        except json.JSONDecodeError:
            fname = raw.strip('"')
        fpath = os.path.join(get_word_lists_dir(), fname)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
            except OSError as e:
                logger.error("Could not delete word list %s: %s", fname, e)
                return
            # Invalidate registry caches so the UI reflects the change.
            try:
                registry = getattr(self.mw.miDictDB, "_registry", None)
                if registry:
                    registry.clear_cache()
            except Exception:
                logger.debug("Could not clear registry cache", exc_info=True)
        # Refresh the file list in the web UI.
        self._push("setWordListData", self._word_list_data())

    def _restore_defaults(self) -> None:
        try:
            from aqt import mw as aqt_mw

            conf = aqt_mw.addonManager.addonConfigDefaults(get_addon_root()) or {}
        except Exception:
            conf = get_addon_config() or {}
        save_addon_config(conf)
        if hasattr(self.mw, "refreshAnkiDictConfig"):
            try:
                self.mw.refreshAnkiDictConfig(conf)
            except Exception:
                logger.debug("Could not refresh config after restore", exc_info=True)
        self.settings_gui.config = conf
        self._push("setConfig", conf)
        self.settings_gui.after_save()

    def _remove_language(self, raw: str) -> None:
        try:
            lang = json.loads(raw)
        except json.JSONDecodeError:
            lang = raw.strip('"')
        try:
            self.settings_gui.remove_language(lang)
        except Exception:
            logger.exception("Could not remove language %s", lang)
        self._push("setLanguagesDicts", self._languages_dicts())

    def _delegate_native(self, dAct: str) -> None:
        """Route native Qt flows (file dialogs / web installers) to the GUI."""
        method_map = {
            "settings:webInstallDicts": "web_install_dicts",
            "settings:importDicts": "import_dicts",
            "settings:webInstallFreq": "web_install_freq",
            "settings:importFreq": "import_freq",
            "settings:browseFontFile": "browse_font_file",
        }
        method = getattr(self.settings_gui, method_map[dAct], None)
        if method:
            method()
        else:
            logger.debug("No native handler for %s", dAct)
