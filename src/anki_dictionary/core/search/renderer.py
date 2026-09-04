from __future__ import annotations

import json
import re
from os.path import exists, join
from typing import Any

from ...utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


def clean_term(term: str) -> str:
    return (
        term.replace("%", "")
        .replace("_", "")
        .replace("\u300c", "")
        .replace("\u300d", "")
    )


def get_font_family(group: dict[str, Any]) -> str:
    if not group.get("font"):
        return " "
    if group.get("customFont"):
        return ' style="font-family:' + re.sub(r"\..*$", "", group["font"]) + ';" '
    return ' style="font-family:' + group["font"] + ';" '


def escape_punctuation(term: str) -> str:
    return re.sub(r"([.*+(\[\]{}\\?)!])", "\\\1", term)


def process_definition_html(text: Any) -> str:
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.strip()
    text = text.replace("\n", "<br>")
    text = re.sub(r"<br\s*/?>", "<br>", text, flags=re.IGNORECASE)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = re.sub(r"(<br>\s*){2,}", "<br><br>", text)
    text = re.sub(r"^(<br>\s*)+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(<br>\s*)+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\[\?\]\s*", "", text)
    return text.strip()


def get_cleaned_urls(urls: list[str]) -> list[str]:
    return [
        u
        for u in urls
        if u
        and u.startswith("http")
        and u.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp"))
    ]


class ResultRenderer:
    """Produces HTML for dictionary search results.

    Pure-ish: takes data + config, returns HTML strings.
    No Qt, no thread, no eval — testable with plain dicts.
    """

    def __init__(self, addon_root: str, iconpath: str) -> None:
        self.addon_root = addon_root
        self.iconpath = iconpath

    # ── helpers ────────────────────────────────────

    def get_tooltips(self, config: dict[str, Any]) -> tuple[str, str, str]:
        if not config.get("tooltips", True):
            return "", "", ""

        img_tip = (
            ' title="Add this definition, or any selected text to the card exporter'
            ' (opens the card exporter if it is not yet opened)." '
        )
        clip_tip = (
            ' title="Copy this definition, or any selected text to the clipboard." '
        )
        send_tip = (
            ' title="Send this definition, or any selected text to this'
            " dictionary's target fields."
            ' It will send it to the current target window" '
        )
        return img_tip, clip_tip, send_tip

    def get_star_tip(self, star_count: str, source: str = "") -> str:
        """Tooltip text for a star-count badge ("" when there is no count)."""
        if not star_count or not isinstance(star_count, str):
            return ""
        return f"Frequency: {source}" if source else "Frequency"

    def get_star_tooltip_html(self, star_count: str, source: str = "") -> str:
        tip = self.get_star_tip(star_count, source)
        return f' title="{tip}" ' if tip else ""

    @staticmethod
    def format_frequency(raw: str) -> str:
        if not raw:
            return raw
        if "k" in raw.lower():
            return raw
        try:
            num = int(raw)
        except ValueError:
            return raw
        if num < 1000:
            return str(num)
        k = num / 1000.0
        if k >= 100:
            return f"{k:.0f}k"
        formatted = f"{k:.1f}k"
        return formatted.replace(".0k", "k")

    def _levels_data(self, entry: dict[str, Any]) -> list[dict[str, str]] | None:
        """Structured level-label data: ``[{label, source?}]`` (None when none)."""
        data = entry.get("levelLabelsData")
        if data and isinstance(data, list):
            items: list[dict[str, str]] = []
            for item in data:
                label = item.get("label", "")
                if not label:
                    continue
                source = item.get("source", "")
                items.append(
                    {"label": label, "source": source} if source else {"label": label}
                )
            return items if items else None
        levels = entry.get("levelLabels", "")
        if levels:
            return [{"label": levels}]
        return None

    def _build_level_labels_html(self, entry: dict[str, Any]) -> str:
        items = self._levels_data(entry)
        if not items:
            return ""
        parts = []
        for item in items:
            source = item.get("source", "")
            tip = f' title="{source}"' if source else ""
            parts.append(
                f'<span class="starcount level-label"{tip}>{item["label"]}</span>'
            )
        return " " + " ".join(parts)

    def _rank_data(
        self, entry: dict[str, Any], extracted_freq: str, config: dict[str, Any]
    ) -> tuple[str, str]:
        """(label, tooltip) for the frequency-rank badge (shared by HTML + doc)."""
        rank_tip = entry.get("frequency_rank_source_display", "")
        rank_source_name = entry.get("frequency_rank_source", "")
        frequency_source_visibility: dict[str, bool] = config.get(
            "frequency_source_visibility", {}
        )
        show_source = frequency_source_visibility.get(
            rank_source_name, False
        ) or config.get("show_frequency_source_name", False)
        if show_source and extracted_freq and rank_tip:
            return f"{rank_tip} [{extracted_freq}]", rank_tip
        return f"[{extracted_freq}]", rank_tip

    def get_base64_icon(self, icon_name: str, is_dark: bool) -> str:
        if is_dark:
            if icon_name == "anki.svg":
                icon_name = "nightanki.svg"
            elif "." in icon_name:
                name, ext = icon_name.rsplit(".", 1)
                if not name.endswith("night"):
                    night = f"{name}night.{ext}"
                    if exists(join(self.iconpath, night)):
                        icon_name = night
        try:
            path = join(self.iconpath, icon_name)
            with open(path, "rb") as f:
                import base64

                data = base64.b64encode(f.read()).decode()
                return f"data:image/svg+xml;base64,{data}"
        except Exception:
            return ""

    def highlight_target(self, text: str, term: str, config: dict[str, Any]) -> str:
        if not config.get("highlightTarget", False):
            return text
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        try:
            parts = re.split(r"(<[^>]*>)", text)
            for i in range(0, len(parts), 2):
                if parts[i]:
                    if any(
                        "\u4e00" <= c <= "\u9fff"
                        or "\u3040" <= c <= "\u309f"
                        or "\u30a0" <= c <= "\u30ff"
                        for c in term
                    ):
                        pat = "(" + escape_punctuation(term) + ")"
                    else:
                        pat = r"\b(" + escape_punctuation(term) + r")\b"
                    parts[i] = re.sub(
                        pat, r'<span class="targetTerm">\1</span>', parts[i]
                    )
            return "".join(parts)
        except Exception as e:
            logger.error("Error during highlight_target: %s", e)
            return text

    def format_term_headers(self, ths: dict[str, list[str]]) -> dict[str, list[str]]:
        if not ths:
            return {}
        formatted: dict[str, list[str]] = {}
        for dictname, headers in ths.items():
            header_str = ""
            sb_str = ""
            for h in headers:
                if h == "term":
                    header_str += (
                        '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b '
                    )
                    sb_str += '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b '
                elif h == "altterm":
                    header_str += (
                        '\u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y '
                    )
                    sb_str += '\u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y '
                elif h == "pronunciation":
                    header_str += '<span class="pronunciation">\u25f3p</span>'
                    sb_str += '<span class="listPronunciation">\u25f3p</span>'
            formatted[dictname] = [header_str, sb_str]
        return formatted

    # ── term headers ───────────────────────────────

    def get_term_header_html(
        self,
        dict_name: str,
        front_bracket: str,
        back_bracket: str,
        target: str,
        term: str,
        altterm: str,
        pronunciation: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        sb: bool = False,
    ) -> str:
        """Headword/pronunciation header as an HTML fragment.

        Single source of truth for both the legacy HTML renderer and the
        structured search document (the components inject the fragment).
        ``sb=True`` produces the sidebar variant (listTerm/listAltTerm).
        """
        alt_fb = front_bracket
        alt_bb = back_bracket
        if pronunciation == term:
            pronunciation = ""
        if altterm == term:
            altterm = ""
        if altterm == "":
            alt_fb = ""
            alt_bb = ""

        clean_name = re.sub(r"l\d+name", "", dict_name)
        if (
            not term_headers
            or dict_name in ("Images", "LLM", "Forvo")
            or clean_name in ("Images", "LLM", "Forvo")
        ):
            if sb:
                header = (
                    '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b '
                    '\u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y '
                    '<span class="listPronunciation">\u25f3p</span>'
                )
            else:
                header = (
                    '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b '
                    '\u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y '
                    '<span class="pronunciation">\u25f3p</span>'
                )
        else:
            lookup = dict_name if dict_name in term_headers else clean_name
            if lookup in term_headers:
                header = term_headers[lookup][1 if sb else 0]
            else:
                if sb:
                    header = (
                        '\u25f3f<span class="listTerm">\u25f3t</span>\u25f3b '
                        '\u25f3x<span class="listAltTerm">\u25f3a</span>\u25f3y '
                        '<span class="listPronunciation">\u25f3p</span>'
                    )
                else:
                    header = (
                        '\u25f3f<span class="term mainword">\u25f3t</span>\u25f3b '
                        '\u25f3x<span class="altterm  mainword">\u25f3a</span>\u25f3y '
                        '<span class="pronunciation">\u25f3p</span>'
                    )

        return (
            header.replace("\u25f3t", self.highlight_target(term, target, config))
            .replace("\u25f3a", self.highlight_target(altterm, target, config))
            .replace("\u25f3p", self.highlight_target(pronunciation, target, config))
            .replace("\u25f3f", front_bracket)
            .replace("\u25f3b", back_bracket)
            .replace("\u25f3x", alt_fb)
            .replace("\u25f3y", alt_bb)
        )

    def get_prepared_term_header(
        self,
        dict_name: str,
        front_bracket: str,
        back_bracket: str,
        target: str,
        term: str,
        altterm: str,
        pronunciation: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        sb: bool = False,
    ) -> str:
        """Backwards-compatible alias for the legacy HTML callers."""
        return self.get_term_header_html(
            dict_name,
            front_bracket,
            back_bracket,
            target,
            term,
            altterm,
            pronunciation,
            config,
            term_headers,
            sb,
        )

    # ── sidebar ────────────────────────────────────

    def get_sidebar(
        self,
        results: dict[str, Any],
        term: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
    ) -> str:
        html = "<div" + font + 'class="definitionSideBar"><div class="innerSideBar">'
        dict_count = 0
        entry_count = 0
        for dict_name, dict_results in results.items():
            display = re.sub(r"l\d+name", "", dict_name).replace("_", " ")
            if dict_name in ("Images", "LLM", "Forvo"):
                html += (
                    '<div data-index="'
                    + str(dict_count)
                    + '" class="listTitle">'
                    + display
                    + '</div><ol class="foundEntriesList"><li data-index="'
                    + str(entry_count)
                    + '">'
                    + self.get_prepared_term_header(
                        dict_name,
                        front_bracket,
                        back_bracket,
                        term,
                        term,
                        term,
                        term,
                        config,
                        term_headers,
                        True,
                    )
                    + "</li></ol>"
                )
                entry_count += 1
                dict_count += 1
                continue
            html += (
                '<div data-index="'
                + str(dict_count)
                + '" class="listTitle">'
                + display
                + '</div><ol class="foundEntriesList">'
            )
            dict_count += 1
            for entry in dict_results:
                html += (
                    '<li data-index="'
                    + str(entry_count)
                    + '">'
                    + self.get_prepared_term_header(
                        dict_name,
                        front_bracket,
                        back_bracket,
                        term,
                        entry["term"],
                        entry["altterm"],
                        entry["pronunciation"],
                        config,
                        term_headers,
                        True,
                    )
                    + "</li>"
                )
                entry_count += 1
            html += "</ol>"
        return (
            html
            + '<br></div><div class="resizeBar" '
            + 'onmousedown="hresize(event)"></div></div>'
        )

    # ── definition cleaning ────────────────────────

    def clean_definition(self, entry: dict[str, Any]) -> tuple[str, str]:
        definition = entry["definition"].strip()
        extracted_freq = ""

        while True:
            definition = re.sub(
                r"^(<br>\s*)+|(<br>\s*)+$", "", definition, flags=re.IGNORECASE
            ).strip()
            freq_match = re.search(
                r"^\u3010[^\u3011]+\u3011\s*\[([\dk+]+)\]\s*", definition
            )
            if freq_match:
                if not extracted_freq:
                    extracted_freq = self.format_frequency(freq_match.group(1))
                definition = definition[freq_match.end() :].strip()
                continue
            head_match = re.search(r"^\u3010[^\u3011]+\u3011\s*", definition)
            if head_match:
                definition = definition[head_match.end() :].strip()
                continue
            break

        term_escaped = re.escape(entry["term"])
        repeat_pat = (
            r"^\s*[\(\uff08\[[\uff3b][^\uff09\)]*?"
            + term_escaped
            + r"[^\uff09\)]*?[\)\uff09\]\uff3b]\s*"
        )
        definition = re.sub(repeat_pat, "", definition)
        definition = re.sub(
            r"^(<br>\s*)+|(<br>\s*)+$", "", definition, flags=re.IGNORECASE
        ).strip()

        if not extracted_freq and entry.get("frequency"):
            extracted_freq = self.format_frequency(str(entry["frequency"]))

        return definition, extracted_freq

    # ── entry rendering ────────────────────────────

    def render_term_pronunciation_block(
        self,
        entry: dict[str, Any],
        dict_name: str,
        clean_name: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        extracted_freq: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        img_tooltip: str = "",
        clip_tooltip: str = "",
        send_tooltip: str = "",
        is_dark: bool = False,
    ) -> str:
        stars = entry.get("starCount", "")
        star_source = entry.get("frequency_source_display", "")
        rank_tip = entry.get("frequency_rank_source_display", "")
        rank_tip_attr = f' title="{rank_tip}"' if rank_tip else ""
        rank_label, rank_tip = self._rank_data(entry, extracted_freq, config)
        rank_display = (
            f' <span class="starcount frequency-rank"{rank_tip_attr}>'
            f"{rank_label}</span>"
            if extracted_freq
            else ""
        )
        levels_display = self._build_level_labels_html(entry)
        return (
            '<div data-index="'
            + str(999)
            + '" class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + self.get_prepared_term_header(
                dict_name,
                front_bracket,
                back_bracket,
                entry["term"],
                entry["term"],
                entry.get("altterm", ""),
                entry.get("pronunciation", ""),
                config,
                term_headers,
            )
            + ' <span class="starcount"'
            + self.get_star_tooltip_html(stars, star_source)
            + ">"
            + stars
            + "</span>"
            + rank_display
            + levels_display
            + '</span><div class="defTools">'
            + "<div onclick=\"ankiExport(event, '"
            + clean_name
            + '\')" role="button" tabindex="0" aria-label="Export to Anki" class="ankiExportButton"><img '
            + img_tooltip
            + ' src="'
            + self.get_base64_icon("anki.svg", is_dark)
            + '"></div><div onclick="clipText(event)" '
            + clip_tooltip
            + ' role="button" tabindex="0" aria-label="Copy to clipboard" class="clipper">\u2702</div><div '
            + send_tooltip
            + " onclick=\"sendToField(event, '"
            + clean_name
            + '\')" role="button" tabindex="0" aria-label="Send to field" class="sendToField">\u279e</div>'
            + '<div class="defNav"><div onclick="navigateDef(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous definition" class="prevDef">\u25b2</div>'
            + '<div onclick="navigateDef(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next definition" class="nextDef">\u25bc</div></div></div></div>'
        )

    def render_definition_block(
        self, definition: str, font: str, term: str, config: dict[str, Any]
    ) -> str:
        return (
            "<div"
            + font
            + ' class="definitionBlock">'
            + self.highlight_target(process_definition_html(definition), term, config)
            + "</div>"
        )

    # ── structured document builders ────────────────
    # These produce the JSON search document consumed by the Svelte shell
    # (Phase 2). The side effects (search, triggers) stay in the pipeline; the
    # renderer only maps data -> document blocks. The legacy HTML renderers
    # above remain for the legacy fallback page and the dynamic service flows.

    def build_sidebar_data(
        self,
        results: dict[str, Any],
        term: str,
        front_bracket: str,
        back_bracket: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Sidebar structure: displayed dict names + highlighted headwords.

        Mirrors ``get_sidebar`` (same iteration/counters) so the Svelte
        ``<Sidebar />`` renders listTitle *i* / li *j* in the same order the
        scrollspy expects.
        """
        sidebar: list[dict[str, Any]] = []
        dict_count = 0
        entry_count = 0
        for dict_name, dict_results in results.items():
            display = re.sub(r"l\d+name", "", dict_name).replace("_", " ")
            if dict_name in ("Images", "LLM", "Forvo"):
                sidebar.append(
                    {
                        "displayName": display,
                        "dataIndex": dict_count,
                        "entries": [
                            {
                                "dataIndex": entry_count,
                                "headerHtml": self.get_term_header_html(
                                    dict_name,
                                    front_bracket,
                                    back_bracket,
                                    term,
                                    term,
                                    term,
                                    term,
                                    config,
                                    term_headers,
                                    True,
                                ),
                            }
                        ],
                    }
                )
                entry_count += 1
                dict_count += 1
                continue
            entries = []
            for entry in dict_results:
                entries.append(
                    {
                        "dataIndex": entry_count,
                        "headerHtml": self.get_term_header_html(
                            dict_name,
                            front_bracket,
                            back_bracket,
                            term,
                            entry["term"],
                            entry["altterm"],
                            entry["pronunciation"],
                            config,
                            term_headers,
                            True,
                        ),
                    }
                )
                entry_count += 1
            sidebar.append(
                {
                    "displayName": display,
                    "dataIndex": dict_count,
                    "entries": entries,
                }
            )
            dict_count += 1
        return sidebar

    def build_title_block(
        self,
        dict_count: int,
        clean_name: str,
        font: str,
        overwrite_html: str,
        field_html: str,
    ) -> dict[str, Any]:
        return {
            "type": "dictionaryTitle",
            "dataIndex": dict_count,
            "title": clean_name.replace("_", " "),
            "font": font,
            "overwriteHtml": overwrite_html,
            "fieldHtml": field_html,
        }

    def build_term_pronunciation_block(
        self,
        entry: dict[str, Any],
        dict_name: str,
        clean_name: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        extracted_freq: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        definition_html: str = "",
    ) -> dict[str, Any]:
        stars = str(entry.get("starCount", ""))
        star_source = entry.get("frequency_source_display", "")
        rank_label, rank_tip = self._rank_data(entry, extracted_freq, config)
        return {
            "type": "termPronunciation",
            "dataIndex": 999,
            "dictName": dict_name,
            "cleanName": clean_name,
            "font": font,
            "headerHtml": self.get_term_header_html(
                dict_name,
                front_bracket,
                back_bracket,
                entry["term"],
                entry["term"],
                entry.get("altterm", ""),
                entry.get("pronunciation", ""),
                config,
                term_headers,
            ),
            "stars": stars,
            "starTip": self.get_star_tip(stars, star_source),
            "rank": {"label": rank_label, "tip": rank_tip} if extracted_freq else None,
            "levels": self._levels_data(entry),
            "definitionHtml": definition_html,
        }

    def build_definition_block(
        self, definition: str, font: str, term: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "type": "definition",
            "font": font,
            "html": self.highlight_target(
                process_definition_html(definition), term, config
            ),
        }

    # ── LLM rendering ──────────────────────────────

    def process_llm_definition(self, definition: str, term: str) -> str:
        definition = re.sub(r"(\*\*|__|\u2605\u2605)(.*?)\1", r"<b>\2</b>", definition)
        definition = re.sub(r"(\*|_)(.*?)\1", r"<i>\2</i>", definition)
        definition = definition.replace("\u2605", "<b>\u2605</b>")
        definition = re.sub(r"^\s*[-*+]\s+", "\u2022 ", definition, flags=re.MULTILINE)

        term_lower = term.lower()
        lines = definition.split("\n")
        if len(lines) > 1:
            first = (
                lines[0]
                .strip()
                .lower()
                .replace("<b>", "")
                .replace("</b>", "")
                .replace("**", "")
                .replace("#", "")
                .strip()
            )
            if first == term_lower:
                definition = "\n".join(lines[1:]).strip()
            lines = definition.split("\n")
            if len(lines) > 1:
                last = (
                    lines[-1]
                    .strip()
                    .lower()
                    .replace("<b>", "")
                    .replace("</b>", "")
                    .replace("**", "")
                    .replace("#", "")
                    .strip()
                )
                if last == term_lower:
                    definition = "\n".join(lines[:-1]).strip()

        term_escaped = re.escape(term)
        repeat = (
            r"^\s*[\(\uff08\[[\uff3b][^\uff09\)]*?"
            + term_escaped
            + r"[^\uff09\)]*?[\)\uff09\]\uff3b]\s*"
        )
        definition = re.sub(repeat, "", definition).strip()
        return definition

    def render_llm_entry(
        self,
        result: dict[str, Any],
        dict_name: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        is_dark: bool = False,
    ) -> str:
        img, clip, send = self.get_tooltips(config)
        stars = str(result.get("starCount", ""))
        star_source = result.get("frequency_source_display", "")
        levels_html = self._build_level_labels_html(result)

        frequency_rank = result.get("frequency_rank", "")
        fr_src_display = result.get("frequency_rank_source_display", "")
        fr_tip_attr = f' title="{fr_src_display}"' if fr_src_display else ""
        rank_display = (
            f' <span class="starcount frequency-rank"{fr_tip_attr}>'
            f"[{frequency_rank}]</span>"
            if frequency_rank
            else ""
        )
        return (
            '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + self.get_prepared_term_header(
                dict_name,
                front_bracket,
                back_bracket,
                result["term"],
                result["term"],
                result.get("altterm", ""),
                result.get("pronunciation", ""),
                config,
                term_headers,
            )
            + ' <span class="starcount"'
            + self.get_star_tooltip_html(stars, star_source)
            + ">"
            + stars
            + "</span>"
            + rank_display
            + levels_html
            + '</span><div class="defTools">'
            + "<div onclick=\"ankiExport(event, '"
            + dict_name
            + '\')" role="button" tabindex="0" aria-label="Export to Anki" class="ankiExportButton"><img '
            + img
            + ' src="'
            + self.get_base64_icon("anki.svg", is_dark)
            + '"></div><div onclick="clipText(event)" '
            + clip
            + ' role="button" tabindex="0" aria-label="Copy to clipboard" class="clipper">\u2702</div><div '
            + send
            + " onclick=\"sendToField(event, '"
            + dict_name
            + '\')" role="button" tabindex="0" aria-label="Send to field" class="sendToField">\u279e</div>'
            + '<div class="defNav"><div onclick="navigateDef(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous definition" class="prevDef">\u25b2</div>'
            + '<div onclick="navigateDef(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next definition" class="nextDict">\u25bc</div></div></div></div>'
        )

    def render_llm_definition_block(
        self, definition: str, font: str, term: str, config: dict[str, Any]
    ) -> str:
        processed = self.process_llm_definition(definition, term)
        return self.render_definition_block(processed, font, term, config)

    def format_single_entry(
        self,
        result: dict[str, Any],
        dict_name: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        is_dark: bool = False,
    ) -> str:
        img, clip, send = self.get_tooltips(config)
        html = (
            '<div class="dictionaryTitleBlock"><div '
            + font
            + ' class="dictionaryTitle">'
            + dict_name
            + '</div><div class="dictionarySettings">'
            + '<div class="dictNav"><div onclick="navigateDict(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous dictionary" class="prevDict">\u25b2</div>'
            + '<div onclick="navigateDict(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next dictionary" class="nextDict">\u25bc</div></div></div></div>'
        )

        stars = str(result.get("starCount", ""))
        star_source = result.get("frequency_source_display", "")
        levels_html = self._build_level_labels_html(result)

        html += (
            '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + self.get_prepared_term_header(
                dict_name,
                front_bracket,
                back_bracket,
                result["term"],
                result["term"],
                result.get("altterm", ""),
                result.get("pronunciation", ""),
                config,
                term_headers,
            )
            + ' <span class="starcount"'
            + self.get_star_tooltip_html(stars, star_source)
            + ">"
            + stars
            + "</span>"
            + levels_html
            + '</span><div class="defTools">'
            + "<div onclick=\"ankiExport(event, '"
            + dict_name
            + '\')" role="button" tabindex="0" aria-label="Export to Anki" class="ankiExportButton"><img '
            + img
            + ' src="'
            + self.get_base64_icon("anki.svg", is_dark)
            + '"></div><div onclick="clipText(event)" '
            + clip
            + ' role="button" tabindex="0" aria-label="Copy to clipboard" class="clipper">\u2702</div><div '
            + send
            + " onclick=\"sendToField(event, '"
            + dict_name
            + '\')" role="button" tabindex="0" aria-label="Send to field" class="sendToField">\u279e</div>'
            + '<div class="defNav"><div onclick="navigateDef(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous definition" class="prevDef">\u25b2</div>'
            + '<div onclick="navigateDef(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next definition" class="nextDef">\u25bc</div></div></div></div>'
        )

        definition = result.get("definition", "")
        processed = self.process_llm_definition(definition, result["term"])
        html += self.render_definition_block(processed, font, result["term"], config)
        return html

    # ── image search rendering ─────────────────────

    def render_image_search_html(
        self,
        term: str,
        font: str,
        front_bracket: str,
        back_bracket: str,
        config: dict[str, Any],
        term_headers: dict[str, list[str]] | None = None,
        id_name: str = "",
        is_dark: bool = False,
        settings_html: str = "",
    ) -> str:
        img, clip, send = self.get_tooltips(config)
        prepared = self.get_prepared_term_header(
            "Images",
            front_bracket,
            back_bracket,
            term,
            term,
            "",
            "",
            config,
            term_headers,
        )
        return (
            '<div data-index="'
            + "0"
            + '" class="dictionaryTitleBlock">'
            + '<div class="dictionaryTitle">Images</div>'
            + '<div class="dictionarySettings">'
            + settings_html
            + '<div class="dictNav">'
            + '<div onclick="navigateDict(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous dictionary" class="prevDict">\u25b2</div>'
            + '<div onclick="navigateDict(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next dictionary" class="nextDict">\u25bc</div>'
            + "</div></div></div>"
            + '<div class="termPronunciation"><span '
            + font
            + ' class="tpCont">'
            + prepared
            + '</span><div class="defTools">'
            + "<div onclick=\"ankiExport(event, 'Images')\" "
            + 'role="button" tabindex="0" aria-label="Export to Anki" class="ankiExportButton"><img '
            + img
            + ' src="'
            + self.get_base64_icon("anki.svg", is_dark)
            + '"></div><div onclick="clipText(event)" '
            + clip
            + ' role="button" tabindex="0" aria-label="Copy to clipboard" class="clipper">\u2702</div><div '
            + send
            + " onclick=\"sendToField(event, 'Images'\") "
            + 'role="button" tabindex="0" aria-label="Send to field" class="sendToField">\u279e</div>'
            + '<div class="defNav">'
            + '<div onclick="navigateDef(event, false)" '
            + 'role="button" tabindex="0" aria-label="Previous definition" class="prevDef">\u25b2</div>'
            + '<div onclick="navigateDef(event, true)" '
            + 'role="button" tabindex="0" aria-label="Next dictionary" class="nextDict">\u25bc</div>'
            + "</div></div></div>"
            + '<div class="definitionBlock">'
            + '<div class="imageBlock is-loading" id="'
            + id_name
            + '">Loading...</div></div>'
        )

    def inject_font_js(self, font: str) -> str:
        name = re.sub(r"\..*$", "", font)
        return json.dumps(font) + ", " + json.dumps(name)

    def get_no_results_html(self, term: str, is_dark: bool) -> str:
        icon = self.get_base64_icon("search.svg", is_dark)
        return (
            "<style>.noresults{font-family: Arial;}"
            ".vertical-center{height: 400px; width: 60%; margin: 0 auto; "
            "display: flex; justify-content: center; align-items: center;}</style>"
            ' <div class="vertical-center noresults">'
            ' <div align="center"> <img src="' + icon + '" width="50px" height="40px">'
            ' <h3 align="center">No dictionary entries were found for "'
            + term
            + '".</h3> </div></div>'
        )
