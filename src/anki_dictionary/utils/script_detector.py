from __future__ import annotations

from typing import Any

CJK_UNIFIED = range(0x4E00, 0x9FFF + 1)
HIRAGANA = range(0x3040, 0x309F + 1)
KATAKANA = range(0x30A0, 0x30FF + 1)
KATAKANA_PHONETIC = range(0x31F0, 0x31FF + 1)
HANGUL_SYLLABLES = range(0xAC00, 0xD7AF + 1)
HANGUL_JAMO = range(0x1100, 0x11FF + 1)
HANGUL_COMPAT = range(0x3130, 0x318F + 1)
THAI = range(0x0E00, 0x0E7F + 1)
CYRILLIC = range(0x0400, 0x04FF + 1)
ARABIC = range(0x0600, 0x06FF + 1)
HEBREW = range(0x0590, 0x05FF + 1)
GREEK = range(0x0370, 0x03FF + 1)
DEVANAGARI = range(0x0900, 0x097F + 1)
BENGALI = range(0x0980, 0x09FF + 1)
TAMIL = range(0x0B80, 0x0BFF + 1)
TIBETAN = range(0x0F00, 0x0FFF + 1)
GEORGIAN = range(0x10A0, 0x10FF + 1)
ARMENIAN = range(0x0530, 0x058F + 1)
CANADIAN_ABORIGINAL = range(0x1400, 0x167F + 1)
CHEROKEE = range(0x13A0, 0x13FF + 1)
ETHIOPIC = range(0x1200, 0x137F + 1)
MONGOLIAN = range(0x1800, 0x18AF + 1)
MYANMAR = range(0x1000, 0x109F + 1)
KHMER = range(0x1780, 0x17FF + 1)
LAO = range(0x0E80, 0x0EFF + 1)
SINHALA = range(0x0D80, 0x0DFF + 1)

SCRIPT_TO_LANGUAGES: dict[str, list[str]] = {
    "Japanese": ["Japanese"],
    "Korean": ["Korean"],
    "Chinese": ["Chinese", "Japanese", "Korean"],
    "Thai": ["Thai"],
    "Russian": ["Russian"],
    "Arabic": ["Arabic"],
    "Hebrew": ["Hebrew"],
    "Greek": ["Greek"],
    "Hindi": ["Hindi"],
    "Bengali": ["Bengali"],
    "Tamil": ["Tamil"],
    "Tibetan": ["Tibetan"],
    "Georgian": ["Georgian"],
    "Armenian": ["Armenian"],
    "Cree": ["Cree"],
    "Cherokee": ["Cherokee"],
    "Amharic": ["Amharic"],
    "Mongolian": ["Mongolian"],
    "Burmese": ["Burmese"],
    "Khmer": ["Khmer"],
    "Lao": ["Lao"],
    "Sinhala": ["Sinhala"],
}


def _in_range(c: str, rng: range) -> bool:
    return ord(c) in rng


def _has_script(text: str, rng: range) -> bool:
    return any(_in_range(c, rng) for c in text)


def detect_language(term: str) -> str:
    if not term:
        return ""

    if (
        _has_script(term, HIRAGANA)
        or _has_script(term, KATAKANA)
        or _has_script(term, KATAKANA_PHONETIC)
    ):
        return "Japanese"

    if (
        _has_script(term, HANGUL_SYLLABLES)
        or _has_script(term, HANGUL_JAMO)
        or _has_script(term, HANGUL_COMPAT)
    ):
        return "Korean"

    if _has_script(term, CJK_UNIFIED):
        return "Chinese"

    if _has_script(term, THAI):
        return "Thai"

    if _has_script(term, CYRILLIC):
        return "Russian"

    if _has_script(term, ARABIC):
        return "Arabic"

    if _has_script(term, HEBREW):
        return "Hebrew"

    if _has_script(term, GREEK):
        return "Greek"

    if _has_script(term, DEVANAGARI):
        return "Hindi"

    if _has_script(term, BENGALI):
        return "Bengali"

    if _has_script(term, TAMIL):
        return "Tamil"

    if _has_script(term, TIBETAN):
        return "Tibetan"

    if _has_script(term, GEORGIAN):
        return "Georgian"

    if _has_script(term, ARMENIAN):
        return "Armenian"

    if _has_script(term, CANADIAN_ABORIGINAL):
        return "Cree"

    if _has_script(term, CHEROKEE):
        return "Cherokee"

    if _has_script(term, ETHIOPIC):
        return "Amharic"

    if _has_script(term, MONGOLIAN):
        return "Mongolian"

    if _has_script(term, MYANMAR):
        return "Burmese"

    if _has_script(term, KHMER):
        return "Khmer"

    if _has_script(term, LAO):
        return "Lao"

    if _has_script(term, SINHALA):
        return "Sinhala"

    return ""


def _find_group_by_language(
    lang_name: str,
    all_groups: dict[str, Any],
) -> str | None:
    lang_lower = lang_name.lower()
    for group_name, group_data in all_groups.items():
        dicts = group_data.get("dictionaries", [])
        for d in dicts:
            lang = d.get("lang", "")
            dict_lang_lower = lang.lower()
            if lang_lower in dict_lang_lower or dict_lang_lower in lang_lower:
                return group_name
    return None


def _find_group_by_name(
    group_name: str,
    user_groups: dict[str, Any],
    default_groups: dict[str, Any],
) -> str | None:
    group_name_lower = group_name.lower()

    if group_name_lower in (g.lower() for g in default_groups):
        for g in default_groups:
            if g.lower() == group_name_lower:
                return g

    if group_name_lower in (g.lower() for g in user_groups):
        for g in user_groups:
            if g.lower() == group_name_lower:
                return g

    return None


def find_matching_group(
    term: str,
    user_groups: dict[str, Any],
    default_groups: dict[str, Any],
    installed_langs: list[str] | None = None,
    language_defaults: dict[str, str] | None = None,
) -> str | None:
    detected = detect_language(term)
    if not detected:
        return None

    if language_defaults is None:
        language_defaults = {}
    if installed_langs is None:
        installed_langs = []

    candidate_langs = SCRIPT_TO_LANGUAGES.get(detected, [detected])

    if installed_langs:
        installed_lower = [il.lower() for il in installed_langs]
        matched = []
        for cl in candidate_langs:
            cl_lower = cl.lower()
            if any(
                cl_lower in il_lower or il_lower in cl_lower
                for il_lower in installed_lower
            ):
                matched.append(cl)
        if matched:
            candidate_langs = matched

    if not candidate_langs:
        candidate_langs = SCRIPT_TO_LANGUAGES.get(detected, [detected])

    all_groups = {**default_groups, **user_groups}

    defaults_lower = {k.lower(): v for k, v in language_defaults.items()}
    for lang in candidate_langs:
        lang_lower = lang.lower()
        for default_key, group_name in list(defaults_lower.items()):
            if lang_lower in default_key or default_key in lang_lower:
                match = _find_group_by_name(group_name, user_groups, default_groups)
                if match is not None:
                    return match

    for lang in candidate_langs:
        match = _find_group_by_language(lang, all_groups)
        if match is not None:
            return match

    for lang in candidate_langs:
        match = _find_group_by_name(lang, user_groups, default_groups)
        if match is not None:
            return match

    return None
