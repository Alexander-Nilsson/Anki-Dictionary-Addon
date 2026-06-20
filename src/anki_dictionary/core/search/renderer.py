from __future__ import annotations

import re
from typing import Any, Dict, List


def clean_term(term: str) -> str:
    return (
        term.replace("%", "")
        .replace("_", "")
        .replace("\u300c", "")
        .replace("\u300d", "")
    )


def get_font_family(group: Dict[str, Any]) -> str:
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


def get_star_tooltip(star_count: str) -> str:
    if not star_count:
        return ""
    if star_count.startswith("\u2605"):
        num = len(star_count)
        return (
            f'<span class="starTooltip" title="{num} star(s)">{"&#9733;" * num}</span>'
        )
    return (
        f'<span class="starTooltip" title="Frequency rank">&#9733; #{star_count}</span>'
    )


def get_cleaned_urls(urls: List[str]) -> List[str]:
    return [
        u
        for u in urls
        if u
        and u.startswith("http")
        and u.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp"))
    ]
