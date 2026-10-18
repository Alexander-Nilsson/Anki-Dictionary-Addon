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

import importlib.util
import json
import os
from typing import Any

from aqt.webview import AnkiWebView

from ...utils.config import get_addon_config, save_addon_config
from ...utils.constants import COUNTRY_TO_DDG, FORVO_LANGUAGES
from ...utils.logger import get_logger
from ...utils.paths import get_addon_root, get_conjugation_dir, get_word_lists_dir
from ...web import config as webConfig

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
        # Web install (install modals): one worker at a time + streamed log.
        self._install_worker: Any = None
        self._web_install_log: list[str] = []
        self._pending_setup: dict[str, Any] | None = None
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
        # The active theme is injected into the page's customThemeCss hook so
        # the settings window matches the dictionary window.
        html = html.replace('<style id="customThemeCss"></style>', self._settings_css())
        self.setHtml(html)

    def _settings_css(self) -> str:
        """Theme CSS for the settings page (falls back to bundled defaults)."""
        try:
            from ..theme_controller import generate_settings_css, get_theme_dict

            return generate_settings_css(get_theme_dict(self._theme_manager()))
        except Exception:
            logger.debug("Could not generate settings theme css", exc_info=True)
            return '<style id="customThemeCss"></style>'

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

    def _image_regions(self) -> list[str]:
        """Country names the image search can target."""
        return sorted(COUNTRY_TO_DDG, key=str.casefold)

    def _setup_status(self) -> dict[str, Any]:
        """Small health summary rendered on the General tab."""
        status: dict[str, Any] = {
            "languages": [],
            "dictionary_count": 0,
            "word_list_count": 0,
            "conjugation_languages": [],
            "missing_conjugation": [],
            "curl_cffi": False,
            "forvo_enabled": self._forvo_enabled(),
            "llm_enabled": self._llm_enabled(),
            "llm_configured": False,
        }
        installed_languages: list[str] = []
        try:
            db = self.mw.miDictDB
            languages = db.getCurrentDbLangs()
            if isinstance(languages, list):
                installed_languages = [str(name) for name in languages]
            status["languages"] = installed_languages
            dictionaries = db.getAllDictsWithLang()
            status["dictionary_count"] = (
                len(dictionaries) if isinstance(dictionaries, list) else 0
            )
        except Exception:
            logger.debug("Could not read dictionary status", exc_info=True)

        try:
            word_lists = self._word_list_data()["files"]
            status["word_list_count"] = sum(
                len(group.get("files", [])) for group in word_lists
            )
        except Exception:
            logger.debug("Could not read word-list status", exc_info=True)

        try:
            conj_dir = get_conjugation_dir()
            if os.path.isdir(conj_dir):
                status["conjugation_languages"] = sorted(
                    name[:-5] for name in os.listdir(conj_dir) if name.endswith(".json")
                )
        except Exception:
            logger.debug("Could not read conjugation status", exc_info=True)

        status["missing_conjugation"] = sorted(
            lang
            for lang in installed_languages
            if lang and lang not in status["conjugation_languages"]
        )

        try:
            status["curl_cffi"] = importlib.util.find_spec("curl_cffi") is not None
        except (ImportError, ValueError):
            status["curl_cffi"] = False

        try:
            config = self.settings_gui.config
            status["llm_configured"] = bool(
                config.get("llm_base_url") and config.get("llm_model")
            )
        except Exception:
            logger.debug("Could not read LLM status", exc_info=True)
        return status

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

    def _repaint_settings(self) -> None:
        """Re-push the theme CSS so the settings page follows theme changes."""
        self._push("setThemeCss", self._settings_css())

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
        self._repaint_settings()

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
        self._repaint_settings()

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
        self._repaint_settings()

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
        elif dAct == "settings:getSetupStatus":
            self._push("setSetupStatus", self._setup_status())
        elif dAct == "settings:getImageRegions":
            self._push("setImageRegions", self._image_regions())
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
            "settings:importDicts",
            "settings:importFreq",
            "settings:browseFontFile",
        ):
            self._delegate_native(dAct)
        elif dAct.startswith("settings:getWebIndex:"):
            raw = dAct[len("settings:getWebIndex:") :]
            self._fetch_web_index(raw)
        elif dAct.startswith("settings:webInstall:"):
            raw = dAct[len("settings:webInstall:") :]
            self._start_web_install(raw)
        elif dAct == "settings:webInstallCancel":
            self._cancel_web_install()
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
        self._push("setSetupStatus", self._setup_status())

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
        """Route native Qt flows (file dialogs) to the GUI."""
        method_map = {
            "settings:importDicts": "import_dicts",
            "settings:importFreq": "import_freq",
            "settings:browseFontFile": "browse_font_file",
        }
        method = getattr(self.settings_gui, method_map[dAct], None)
        if method:
            method()
        else:
            logger.debug("No native handler for %s", dAct)

    # ── web install (settings install modals) ──────────────

    def _fetch_web_index(self, raw: str) -> None:
        """Download the dictionary server index off the UI thread."""
        try:
            server = json.loads(raw)
        except json.JSONDecodeError:
            server = ""
        if not isinstance(server, str) or not server.strip():
            server = webConfig.DEFAULT_SERVER

        def run() -> dict[str, Any]:
            index = webConfig.download_index(server)
            if index is None:
                return {"ok": False, "server": server}
            return {"ok": True, "server": server, "index": index}

        def on_done(future: Any) -> None:
            try:
                self._push("setWebIndex", future.result())
            except Exception:  # noqa: BLE001
                logger.exception("Web index fetch failed")
                self._push("setWebIndex", {"ok": False, "server": server})

        taskman = getattr(self.mw, "taskman", None)
        if taskman is not None:
            taskman.run_in_background(run, on_done)
        else:
            self._push("setWebIndex", run())

    def _start_web_install(self, raw: str) -> None:
        """Kick off a WebInstallWorker for the modal's selection."""
        if self._install_worker is not None and self._install_worker.isRunning():
            logger.warning("Web install already running; ignoring new request")
            return
        try:
            selection = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("settings:webInstall received invalid JSON payload")
            return
        if not isinstance(selection, dict):
            return

        from ...web.install_service import WebInstallWorker

        setup = selection.pop("apply_setup", None)
        self._pending_setup = setup if isinstance(setup, dict) else None
        self._web_install_log = []
        worker = WebInstallWorker(selection)
        worker.log_line.connect(self._on_install_log)
        worker.progress.connect(
            lambda pct: self._push("setWebInstall", {"percent": pct, "running": True})
        )
        worker.done.connect(self._on_install_done)
        self._install_worker = worker
        self._push("setWebInstall", {"percent": 0, "running": True, "log": []})
        worker.start()

    def _cancel_web_install(self) -> None:
        if self._install_worker is not None and self._install_worker.isRunning():
            self._install_worker.cancel_requested = True

    def _on_install_log(self, line: str) -> None:
        self._web_install_log.append(line)
        self._push(
            "setWebInstall",
            {"log": self._web_install_log[-400:], "running": True},
        )

    def _on_install_done(self, completed: bool) -> None:
        failed = 0
        installed = 0
        skipped = 0
        if self._install_worker is not None:
            failed = getattr(self._install_worker, "failed", 0)
            installed = getattr(self._install_worker, "installed", 0)
            skipped = getattr(self._install_worker, "skipped", 0)
            self._install_worker.wait()
            self._install_worker = None
        # Invalidate caches so installed data is picked up immediately.
        db = getattr(self.mw, "miDictDB", None)
        if db is not None:
            try:
                if db._registry is not None:
                    db._registry.clear_cache()
                db._extra_data_cache.clear()
            except Exception:
                logger.debug("Could not clear db caches after install", exc_info=True)
        self._push(
            "setWebInstall",
            {
                "percent": 100 if (completed or failed) else 0,
                "running": False,
                "completed": completed,
                "failed": failed,
                "installed": installed,
                "skipped": skipped,
            },
        )
        if completed and self._pending_setup:
            self._apply_setup(self._pending_setup)
        self._pending_setup = None
        if hasattr(self.settings_gui, "_after_native_change"):
            self.settings_gui._after_native_change()
        self._push("setSetupStatus", self._setup_status())

    def _apply_setup(self, setup: dict[str, Any]) -> None:
        """Apply the target language chosen by the Quick Setup card."""
        try:
            config = dict(get_addon_config())
            language = str(setup.get("language") or "").strip()
            if language:
                defaults = dict(config.get("language_defaults") or {})
                defaults[language] = language
                config["language_defaults"] = defaults
                # Default groups are named after the language.
                config["currentGroup"] = language
            forvo_language = str(setup.get("forvo_language") or "").strip()
            if forvo_language:
                config["forvo_language"] = forvo_language
            if setup.get("deinflect"):
                config["deinflect"] = True
            save_addon_config(config)
            self.settings_gui.config = config
            if hasattr(self.mw, "refreshAnkiDictConfig"):
                self.mw.refreshAnkiDictConfig(config)
            self._push("setConfig", config)
        except Exception:
            logger.exception("Could not apply quick-setup configuration")
