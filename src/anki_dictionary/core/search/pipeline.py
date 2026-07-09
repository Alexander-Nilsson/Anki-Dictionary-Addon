from __future__ import annotations

import json
import re
import time
from os.path import exists, join
from typing import Any

from ...integrations import llm as llm_integration
from ...utils.logger import get_logger
from .coordinator import ExternalServiceCoordinator
from .renderer import (
    ResultRenderer,
    clean_term,
    get_font_family,
)

logger = get_logger(__name__.split(".")[-1])


class SearchPipeline:
    """Orchestrates dictionary search, renders results, manages external services.

    Slim coordinator: delegates HTML generation to ``ResultRenderer``
    and worker lifecycle to ``ExternalServiceCoordinator``.
    """

    def __init__(self, midict: Any) -> None:
        self.midict = midict
        self.renderer = ResultRenderer(
            addon_root=midict.addon_root,
            iconpath=midict.dictInt.iconpath,
        )
        self.coordinator = ExternalServiceCoordinator(
            eval_fn=midict.eval,
            threadpool=midict.threadpool,
            on_llm_result=self.loadLLMResults,
            on_llm_error=self.showLLMError,
            on_forvo_result=self.onForvoResult,
            on_forvo_error=self.onForvoError,
        )

    # ── public entry point ─────────────────────────

    def addNewTab(self, term: str, selected_group: dict[str, Any]) -> None:
        if (
            selected_group.get("customFont")
            and selected_group.get("font")
            and selected_group["font"] not in self.midict.customFontsLoaded
        ):
            self.midict.customFontsLoaded.append(selected_group["font"])
            self._inject_font(selected_group["font"])

        id_name = f"llm-loader-{int(time.time() * 1000)}"
        html, cleaned, single_tab = self.getHTMLResult(term, selected_group, id_name)

        js_html = json.dumps(html.replace("\r", "").replace("\n", ""))
        js_cleaned = json.dumps(cleaned)
        js_single = "true" if single_tab == "true" else "false"
        js_id = json.dumps(id_name)
        self.midict.eval(f"addNewTab({js_html}, {js_cleaned}, {js_single}, {js_id});")

    # ── search + render ────────────────────────────

    def getHTMLResult(
        self, term: str, selected_group: dict[str, Any], id_name: str = ""
    ) -> tuple[str, str, str]:
        single_tab = self._get_tab_mode()
        cleaned = clean_term(term)
        font = get_font_family(selected_group)
        dict_defs = self.midict.config.get("dictSearch", 50)
        max_defs = self.midict.config.get("maxSearch", 1000)

        results = self.midict.db.searchTerm(
            term,
            selected_group,
            self.midict.conjugations,
            self.midict.sType.currentText(),
            self.midict.deinflect,
            str(dict_defs),
            max_defs,
        )

        group_dicts = [d["dict"] for d in selected_group.get("dictionaries", [])]

        # LLM
        if self.midict.config.get("llm_enabled", False) and "LLM" in group_dicts:
            star_count, level_labels, frequency_rank, fr_src_display = (
                self._extract_freq_from_results(results)
            )
            if not star_count and not level_labels:
                for d in selected_group.get("dictionaries", []):
                    lang = d.get("lang")
                    if lang:
                        info = self.midict.db.get_term_frequency_info(
                            cleaned, lang, self.midict.config
                        )
                        if info.get("starCount"):
                            star_count = info["starCount"]
                            freq_raw = info.get("frequency")
                            if freq_raw is not None:
                                frequency_rank = ResultRenderer.format_frequency(
                                    str(freq_raw)
                                )
                                fr_src_display = info.get(
                                    "frequency_rank_source_display", ""
                                )
                        if info.get("levelLabels"):
                            level_labels = info["levelLabels"]
                        if star_count or level_labels:
                            break

            pronunciation = ""
            if self.midict.config.get("llm_get_pronunciation", False):
                pronunciation = self._extract_pronunciation_from_results(
                    results, group_dicts
                )

            self._trigger_llm(
                cleaned,
                star_count,
                level_labels,
                id_name,
                pronunciation,
                frequency_rank,
                fr_src_display,
            )

        # Forvo
        forvo_id = ""
        if self.midict.config.get("forvo_enabled", False) and "Forvo" in group_dicts:
            forvo_lang = self.midict.config.get("forvo_language", "ja")
            for d in selected_group.get("dictionaries", []):
                if d["dict"] == "Forvo" and d.get("lang"):
                    forvo_lang = d["lang"]
                    break
            forvo_id = f"forvo-loader-{int(time.time() * 1000)}"
            self._trigger_forvo(cleaned, forvo_id, forvo_lang)

        html = self._prepare_results(results, cleaned, font, id_name, forvo_id)
        html = html.replace("\n", "")
        return html, cleaned, single_tab

    # ── result preparation ─────────────────────────

    def _prepare_results(
        self,
        results: dict[str, Any],
        term: str,
        font: str,
        id_name: str = "",
        forvo_id: str = "",
    ) -> str:
        config = self.midict.config
        front_b = config.get("frontBracket", "\u3010")
        back_b = config.get("backBracket", "\u3011")
        term_headers = getattr(self.midict, "termHeaders", None)
        is_dark = self.midict.dictInt.theme_manager.is_dark

        group = self.midict.dictInt.getSelectedDictGroup()
        group_dicts = [d["dict"] for d in group.get("dictionaries", [])]
        has_special = any(d in ("Images", "LLM", "Forvo") for d in group_dicts)

        if not results and not has_special:
            return self.renderer.get_no_results_html(term, is_dark)

        html = self.renderer.get_sidebar(
            results, term, font, front_b, back_b, config, term_headers
        )
        html += '<div class="mainDictDisplay">'
        dict_count = 0
        entry_count = 0
        img_tip, clip_tip, send_tip = self.renderer.get_tooltips(config)

        for d_info in group.get("dictionaries", []):
            dict_name = d_info["dict"]

            if dict_name == "Images":
                image_id = f"gcon{int(time.time() * 1000)}".replace(".", "")
                html += self.renderer.render_image_search_html(
                    term,
                    font,
                    front_b,
                    back_b,
                    config,
                    term_headers,
                    image_id,
                    is_dark,
                    settings_html=(
                        self._get_overwrite_html(dict_count, dict_name)
                        + self._get_field_html(dict_name)
                    ),
                )
                self._trigger_image_search(term, image_id)
                dict_count += 1
                entry_count += 1
                continue

            if dict_name == "LLM":
                if self.midict.config.get("llm_enabled", False):
                    loader = id_name if id_name else "llm-loader"
                    html += self._render_llm_placeholder(dict_count, font, loader)
                dict_count += 1
                entry_count += 1
                continue

            if dict_name == "Forvo":
                if self.midict.config.get("forvo_enabled", False):
                    loader = forvo_id if forvo_id else "forvo-loader"
                    html += self._render_forvo_placeholder(dict_count, font, loader)
                dict_count += 1
                entry_count += 1
                continue

            clean_name = self.midict.db.cleanDictName(dict_name)
            normalized = self.midict.db.normalize_dict_name(dict_name)
            dict_results = (
                results.get(dict_name)
                or results.get(clean_name)
                or results.get(normalized)
            )
            if dict_results is None:
                continue

            overwrite = self._get_overwrite_html(dict_count, dict_name)
            field_select = self._get_field_html(dict_name)
            html += (
                '<div data-index="'
                + str(dict_count)
                + '" class="dictionaryTitleBlock"><div '
                + font
                + ' class="dictionaryTitle">'
                + clean_name.replace("_", " ")
                + '</div><div class="dictionarySettings">'
                + overwrite
                + field_select
                + '<div class="dictNav">'
                + '<div onclick="navigateDict(event, false)" class="prevDict">\u25b2</div>'
                + '<div onclick="navigateDict(event, true)" class="nextDict">\u25bc</div>'
                + "</div></div></div>"
            )
            dict_count += 1

            for entry in dict_results:
                definition, extracted_freq = self.renderer.clean_definition(entry)
                entry["definition"] = definition

                html += self.renderer.render_term_pronunciation_block(
                    entry,
                    dict_name,
                    clean_name,
                    font,
                    front_b,
                    back_b,
                    extracted_freq,
                    config,
                    term_headers,
                    img_tip,
                    clip_tip,
                    send_tip,
                    is_dark,
                )
                html += self.renderer.render_definition_block(
                    definition, font, term, config
                )
                entry_count += 1

        html += "</div>"
        return html

    # ── LLM result injection ───────────────────────

    def loadLLMResults(self, result: dict[str, Any]) -> None:
        dict_name = result.get("dictName", "LLM")
        id_name = result.get("idName") or "llm-loader"
        group = self.midict.dictInt.getSelectedDictGroup()
        font = get_font_family(group)
        config = self.midict.config
        front_b = config.get("frontBracket", "\u3010")
        back_b = config.get("backBracket", "\u3011")
        term_headers = getattr(self.midict, "termHeaders", None)

        is_dark = self.midict.dictInt.theme_manager.is_dark
        definitions = llm_integration.split_llm_definitions(result["definition"])
        if not definitions:
            definitions = [result["definition"]]

        html_entries = ""
        for def_text in definitions:
            html_entries += self.renderer.render_llm_entry(
                result,
                dict_name,
                font,
                front_b,
                back_b,
                config,
                term_headers,
                is_dark,
            )
            html_entries += self.renderer.render_llm_definition_block(
                def_text,
                font,
                result["term"],
                config,
            )

        escaped = json.dumps(html_entries)
        self.midict.eval(
            f"var loader = document.getElementById('{id_name}'); "
            f"if(loader) {{ "
            f"  var placeholder = loader.querySelector('.llm-loading-placeholder'); "
            f"  if(placeholder) {{ "
            f"    placeholder.outerHTML = {escaped}; "
            f"  }} else {{ "
            f"    var old = loader.querySelector('.definitionBlock'); "
            f"    if(old) old.remove(); "
            f"    var tb = loader.querySelector('.dictionaryTitleBlock'); "
            f"    if(tb) tb.insertAdjacentHTML('afterend', {escaped}); "
            f"    else loader.insertAdjacentHTML('beforeend', {escaped}); "
            f"  }} "
            f"}} else {{ "
            f"  console.error('LLM container not found: {id_name}'); "
            f"}}"
        )

    def showLLMError(self, result: dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown LLM error")
        id_name = result.get("idName") or "llm-loader"
        esc = json.dumps(
            '<div class="definitionBlock llm-error" '
            'style="color: #ff5555; border: 1px solid #ff5555; padding: 15px; '
            'border-radius: 8px; background-color: rgba(255, 85, 85, 0.05);">'
            '<div style="font-weight: bold; margin-bottom: 8px; '
            'font-size: 1.1em;">LLM Connection Error</div>'
            f"<div>{error_msg}</div></div>"
        )
        try:
            self.midict.eval(
                f"var loader = document.getElementById('{id_name}'); "
                f"if(loader) {{ "
                f"  var old = loader.querySelector('.definitionBlock'); "
                f"  if(old) old.remove(); "
                f"  var tb = loader.querySelector('.dictionaryTitleBlock'); "
                f"  if(tb) tb.insertAdjacentHTML('afterend', {esc}); "
                f"}}"
            )
        except Exception:
            logger.debug(
                "Failed to inject LLM error into webview (may have been destroyed)"
            )

    # ── Forvo result injection ─────────────────────

    def onForvoResult(self, result: dict[str, Any]) -> None:
        id_name = result.get("idName") or "forvo-loader"
        term = result.get("term", "")
        items = result.get("items", [])
        if not items:
            self._remove_forvo_element(id_name)
            return

        group = self.midict.dictInt.getSelectedDictGroup()
        font = get_font_family(group)
        config = self.midict.config
        limit = config.get("forvo_limit", 3)
        img_tip, clip_tip, send_tip = self.renderer.get_tooltips(config)

        content = (
            f'<div {font} class="definitionBlock">'
            '<div class="forvo-container" '
            'style="padding: var(--spacing-sm) 0;">'
        )
        for idx, item in enumerate(items):
            user = item.get("user", "Unknown")
            votes = item.get("votes", 0)
            origin = item.get("origin", "")
            audio_url = item.get("audio_url", "")
            style = (
                "display: flex; align-items: center; "
                "margin-bottom: var(--spacing-sm); padding: var(--spacing-sm); "
                "border-bottom: 1px solid var(--border);"
            )
            extra = ""
            if idx >= limit:
                style += " display: none;"
                extra = "forvo-extra"
            content += (
                f'<div class="forvo-item {extra}" style="{style}">'
                '<div onclick="animateForvoPlay(this);'
                f" playAudio('{audio_url}')\" "
                'style="cursor:pointer; font-size: 20px; '
                "margin-right: var(--spacing-md); color: var(--primary); "
                "width: 32px; height: 32px; "
                "display: flex; align-items: center; justify-content: center; "
                "border-radius: 50%; "
                'background: var(--primary-light, rgba(33,150,243,0.1));">'
                '<span class="forvo-icon">\u25b6</span>'
                "</div>"
                f"<div><b>{user}</b> "
                f'<span style="font-size:0.85em">{origin}</span>'
                f'<div style="font-size:0.8em">Votes: {votes}</div></div>'
                '<div class="defTools" style="margin-left:auto;display:flex">'
                f"<div onclick=\"ankiAudioExport('{term}','{audio_url}')\" "
                f'class="ankiExportButton"><img {img_tip} '
                f'src="{self._base64_icon("anki.svg")}" '
                'style="width:18px;height:18px"></div></div></div>'
            )

        if len(items) > limit:
            more = len(items) - limit
            content += (
                '<div onclick="showMoreForvo(this)" class="forvo-load-more" '
                'style="text-align:center;padding:var(--spacing-sm);cursor:pointer;'
                "color:var(--primary);font-weight:bold;"
                'border:1px dashed var(--primary);border-radius:var(--border-radius-sm);">'
                f"Load more ({more})</div>"
            )
        content += "</div></div>"
        escaped = json.dumps(content)

        self.midict.eval(
            f"var loader = document.getElementById('{id_name}'); "
            f"if(loader) {{ "
            f"  var tb = loader.querySelector('.dictionaryTitleBlock'); "
            f"  if(tb) {{ loader.innerHTML = ''; loader.appendChild(tb); "
            f"    tb.insertAdjacentHTML('afterend', {escaped}); }} "
            f"}}"
        )

    def onForvoError(self, result: dict[str, Any]) -> None:
        error_msg = result.get("error", "Unknown Forvo error")
        logger.warning("Forvo unavailable: %s", error_msg)
        id_name = result.get("idName") or "forvo-loader"
        esc = json.dumps(
            '<div class="definitionBlock forvo-error" '
            'style="color:var(--danger,#ff5555);padding:12px;'
            'border-radius:8px;">'
            f"<div>{error_msg}</div></div>"
        )
        self.midict.eval(
            f"var loader = document.getElementById('{id_name}'); "
            f"if(loader) {{ "
            f"  var old = loader.querySelector('.definitionBlock'); "
            f"  if(old) old.remove(); "
            f"  var tb = loader.querySelector('.dictionaryTitleBlock'); "
            f"  if(tb) tb.insertAdjacentHTML('afterend', {esc}); "
            f"}}"
        )

    def _remove_forvo_element(self, id_name: str) -> None:
        self.midict.eval(
            f"var el = document.getElementById('{id_name}'); "
            f"if(el) el.remove(); "
            f"var titles = document.querySelectorAll('.listTitle'); "
            f"for (var i = 0; i < titles.length; i++) {{ "
            f"  if (titles[i].textContent === 'Forvo') {{ "
            f"    var list = titles[i].nextElementSibling; "
            f"    if(list && list.classList.contains('foundEntriesList')) list.remove(); "
            f"    titles[i].remove(); break; "
            f"  }} "
            f"}}"
        )

    # ── image search ───────────────────────────────

    def loadImageResults(self, results: tuple[str, str]) -> None:
        html, id_name = results
        self.midict.eval(f"loadImageHtml({json.dumps(html)}, {json.dumps(id_name)});")

    def loadMoreImages(self, search_term: str) -> None:
        if not hasattr(self.midict, "image_offsets"):
            self.midict.image_offsets = {}
        offset = self.midict.image_offsets.get(search_term, 0) + 15
        self.midict.image_offsets[search_term] = offset
        self.coordinator.trigger_image_search(
            search_term, self.midict.config, "load_more", offset
        )

    def loadMoreImageResults(self, results: tuple[str, str]) -> None:
        html, id_name = results
        if not html or html.strip() == "":
            self.midict.eval(
                "var btn = document.querySelector('.imageLoader'); "
                "if(btn) { btn.textContent = 'No more images'; btn.disabled = true; }"
            )
            return
        try:
            self.midict.eval(f"appendNewImages({json.dumps(html)});")
        except Exception as e:
            logger.error("Error in loadMoreImageResults: %s", e)

    def showNoImagesMessage(self) -> None:
        from aqt.utils import tooltip

        tooltip("No images found")

    # ── helpers ────────────────────────────────────

    def formatTermHeaders(
        self, ths: dict[str, list[str]]
    ) -> dict[str, list[str]] | None:
        result = self.renderer.format_term_headers(ths)
        return result if result else None

    def loadConjugations(self) -> dict[str, Any]:
        langs = self.midict.db.getCurrentDbLangs()
        conv: dict[str, Any] = {}
        for lang in langs:
            fp = join(
                self.midict.homeDir, "user_files", "db", "conjugation", f"{lang}.json"
            )
            if not exists(fp):
                fp = join(
                    self.midict.homeDir,
                    "user_files",
                    "dictionaries",
                    lang,
                    "conjugations.json",
                )
                if not exists(fp):
                    continue
            with open(fp, encoding="utf-8") as f:
                conv[lang] = json.loads(f.read())
        return conv

    def cleanTerm(self, term: str) -> str:
        return clean_term(term)

    def getFontFamily(self, group: dict[str, Any]) -> str:
        return get_font_family(group)

    def injectFont(self, font: str) -> None:
        self._inject_font(font)

    def formatSingleEntry(
        self,
        result: dict[str, Any],
        dict_name: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
    ) -> str:
        is_dark = self.midict.dictInt.theme_manager.is_dark
        return self.renderer.format_single_entry(
            result,
            dict_name,
            font,
            front_bracket,
            back_bracket,
            self.midict.config,
            getattr(self.midict, "termHeaders", None),
            is_dark,
        )

    def getCleanedUrls(self, urls: list[str]) -> list[str]:
        from .renderer import get_cleaned_urls

        return get_cleaned_urls(urls)

    # ── private ────────────────────────────────────

    def _get_tab_mode(self) -> str:
        return "true" if self.midict.dictInt.tabB.singleTab else "false"

    def _extract_freq_from_results(
        self, results: dict[str, Any]
    ) -> tuple[str, str, str, str]:
        star_count = ""
        level_labels = ""
        frequency_rank = ""
        frequency_rank_source_display = ""
        for _d_name, d_results in results.items():
            if not isinstance(d_results, list):
                continue
            for entry in d_results:
                s = entry.get("starCount", "")
                if s:
                    if s.startswith("\u2605"):
                        if not star_count.startswith("\u2605") or len(s) > len(
                            star_count
                        ):
                            star_count = s
                            freq = entry.get("frequency")
                            if freq is not None:
                                frequency_rank = self.renderer.format_frequency(
                                    str(freq)
                                )
                                frequency_rank_source_display = entry.get(
                                    "frequency_rank_source_display", ""
                                )
                    elif not star_count:
                        star_count = s
                        freq = entry.get("frequency")
                        if freq is not None:
                            frequency_rank = self.renderer.format_frequency(str(freq))
                            frequency_rank_source_display = entry.get(
                                "frequency_rank_source_display", ""
                            )
                ll = entry.get("levelLabels", "")
                if ll and len(ll) > len(level_labels):
                    level_labels = ll
        return star_count, level_labels, frequency_rank, frequency_rank_source_display

    def _extract_pronunciation_from_results(
        self, results: dict[str, Any], group_dicts: list[str]
    ) -> str:
        for d_name in group_dicts:
            if d_name in ("Images", "LLM", "Forvo"):
                continue
            d_results = results.get(d_name)
            if not isinstance(d_results, list):
                continue
            for entry in d_results:
                pron = entry.get("pronunciation", "")
                term = entry.get("term", "")
                if pron and pron != term:
                    return pron
        return ""

    def _trigger_llm(
        self,
        term: str,
        star_count: str,
        level_labels: str,
        id_name: str,
        pronunciation: str = "",
        frequency_rank: str = "",
        frequency_rank_source_display: str = "",
    ) -> None:
        self.coordinator.trigger_llm(
            term,
            self.midict.config,
            star_count,
            level_labels,
            id_name,
            pronunciation,
            frequency_rank,
            frequency_rank_source_display,
        )

    def _trigger_forvo(self, term: str, id_name: str, language: str) -> None:
        self.coordinator.trigger_forvo(term, self.midict.config, id_name, language)

    def _trigger_image_search(self, term: str, id_name: str) -> None:
        self.coordinator.trigger_image_search(term, self.midict.config, id_name, 0)

    def _render_llm_placeholder(self, dict_count: int, font: str, id_name: str) -> str:
        overwrite = self._get_overwrite_html(dict_count, "LLM")
        field_sel = self._get_field_html("LLM")
        return (
            f'<div id="{id_name}">'
            '<div data-index="' + str(dict_count) + '" '
            'class="dictionaryTitleBlock"><div '
            + font
            + ' class="dictionaryTitle">LLM</div>'
            '<div class="dictionarySettings">'
            + overwrite
            + field_sel
            + '<div class="dictNav">'
            '<div onclick="navigateDict(event,false)" class="prevDict">\u25b2</div>'
            '<div onclick="navigateDict(event,true)" class="nextDict">\u25bc</div>'
            "</div></div></div>"
            '<div class="definitionBlock llm-loading-placeholder">'
            "<i>Loading LLM definition...</i></div></div>"
        )

    def _render_forvo_placeholder(
        self, dict_count: int, font: str, id_name: str
    ) -> str:
        overwrite = self._get_overwrite_html(dict_count, "Forvo")
        field_sel = self._get_field_html("Forvo")
        return (
            f'<div id="{id_name}">'
            '<div data-index="' + str(dict_count) + '" '
            'class="dictionaryTitleBlock"><div '
            + font
            + ' class="dictionaryTitle">Forvo</div>'
            '<div class="dictionarySettings">'
            + overwrite
            + field_sel
            + '<div class="dictNav">'
            '<div onclick="navigateDict(event,false)" class="prevDict">\u25b2</div>'
            '<div onclick="navigateDict(event,true)" class="nextDict">\u25bc</div>'
            "</div></div></div>"
            '<div class="definitionBlock"><i>Loading Forvo pronunciations...</i>'
            "</div></div>"
        )

    def _get_overwrite_html(self, dict_count: int, dict_name: str) -> str:
        clean_name = self.midict.db.cleanDictName(dict_name)
        if dict_name in ("Images", "LLM", "Forvo") or clean_name in (
            "Images",
            "LLM",
            "Forvo",
        ):
            key = dict_name if dict_name in ("Images", "LLM", "Forvo") else clean_name
            add_type = self.midict.config.get(f"{key}AddType", "add")
        else:
            add_type = (
                self.midict.db.getAddType(dict_name)
                or self.midict.db.getAddType(clean_name)
                or "add"
            )

        tooltip = ""
        if self.midict.config.get("tooltips"):
            tooltip = (
                ' title="This determines the conditions for sending a definition'
                " to a field. Overwrite the target field's content."
                " Add to the target field's current contents."
                ' Only add definitions to the target field if it is empty."'
            )

        type_names = {"overwrite": "Overwrite", "no": "If Empty", "add": "Add"}
        type_name = f"&nbsp;{type_names.get(add_type, 'Add')}"
        return (
            '<div class="overwriteSelectCont"><div '
            + tooltip
            + ' class="overwriteSelect" onclick="showCheckboxes(event)">'
            + type_name
            + "</div>"
            + self._get_overwrite_checkboxes(dict_name, add_type)
            + "</div>"
        )

    def _get_overwrite_checkboxes(self, dict_name: str, add_type: str) -> str:
        count = str(self.midict.radioCount)
        if not hasattr(self.midict, "radioCount"):
            self.midict.radioCount = 0
        self.midict.radioCount += 1

        def _radio(value, label_text):
            checked = " checked" if add_type == value else ""
            return (
                '<label class="inCheckBox"><input'
                + checked
                + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio'
                + dict_name
                + '" type="radio" name="'
                + count
                + dict_name
                + '" value="'
                + value
                + '"/>'
                + label_text
                + "</label>"
            )

        return (
            '<div class="overwriteCheckboxes" data-dictname="'
            + dict_name
            + '">'
            + _radio("add", "Add")
            + _radio("overwrite", "Overwrite")
            + _radio("no", "If Empty")
            + "</div>"
        )

    def _get_field_html(self, dict_name: str) -> str:
        clean_name = self.midict.db.cleanDictName(dict_name)
        if dict_name in ("Images", "LLM", "Forvo") or clean_name in (
            "Images",
            "LLM",
            "Forvo",
        ):
            key = dict_name if dict_name in ("Images", "LLM", "Forvo") else clean_name
            selF = self.midict.config.get(f"{key}Fields", [])
        else:
            selF = (
                self.midict.db.getFieldsSetting(dict_name)
                or self.midict.db.getFieldsSetting(clean_name)
                or []
            )

        tooltip = ""
        if self.midict.config.get("tooltips"):
            tooltip = ' title="Select this dictionary\'s target fields for when sending a definition to a card."'
        title = "&nbsp;Select Fields \u25be"
        length = len(selF)
        if length > 0:
            title = "&nbsp;" + str(length) + " Selected"
        return (
            '<div class="fieldSelectCont"><div class="fieldSelect" '
            + tooltip
            + ' onclick="showCheckboxes(event)">'
            + title
            + "</div>"
            + self._get_checkboxes(dict_name, selF)
            + "</div>"
        )

    def _get_checkboxes(self, dict_name: str, selF: list) -> str:
        fields = self._get_field_names()
        options = (
            '<div class="fieldCheckboxes" data-dictname="' + dict_name + '">'
            '<input type="text" class="fieldSearchInput" placeholder="Search fields..." '
            'onclick="event.stopPropagation()" onkeyup="filterFieldOptions(this)" />'
            '<div class="fieldOptionsContainer">'
        )
        for f in fields:
            checked = " checked" if f in selF else ""
            options += (
                '<label class="fieldCheckboxLabel"><input type="checkbox"'
                + checked
                + ' class="fieldCheckbox" onchange="handleFieldCheckbox(this)" value="'
                + f
                + '" /><span>'
                + f
                + "</span></label>"
            )
        options += "</div></div>"
        return options

    def _get_field_names(self) -> list:
        mw = self.midict.dictInt.mw
        models = mw.col.models.all()
        fields = []
        for model in models:
            for fld in model["flds"]:
                if fld["name"] not in fields:
                    fields.append(fld["name"])
        fields.sort()
        return fields

    def _inject_font(self, font: str) -> None:
        name = re.sub(r"\..*$", "", font)
        self.midict.eval(f"addCustomFont({json.dumps(font)}, {json.dumps(name)});")

    def _base64_icon(self, name: str) -> str:
        return self.renderer.get_base64_icon(
            name, self.midict.dictInt.theme_manager.is_dark
        )
