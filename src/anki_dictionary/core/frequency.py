from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from ..utils.config import get_addon_config
from ..utils.logger import get_logger
from ..utils.paths import get_db_dir
from .word_list_registry import WordListProvider, WordListRegistry

logger = get_logger(__name__.split(".")[-1])

# ── kana helpers (pure) ───────────────────────────

HIRAGANA = (
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"
    "あいうえおかきくけこさしすせそたちつてと"
    "なにぬねのはひふへほまみむめもやゆよらりるれろ"
    "わをんぁぃぅぇぉゃゅょっゐゑ"
)

KATAKANA = (
    "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"
    "アイウエオカキクケコサシスセソタチツテト"
    "ナニヌネノハヒフヘホマミムメモヤユヨラリルレロ"
    "ワヲンァィゥェォャュョッヰヱ"
)

_HIRA_ORDS = [ord(c) for c in HIRAGANA]
_KATA_ORDS = [ord(c) for c in KATAKANA]
_HIRAGANA_TABLE = dict(zip(_KATA_ORDS, HIRAGANA))
_KATAKANA_TABLE = dict(zip(_HIRA_ORDS, KATAKANA))


def kana_converter(to_translate: str, hiraganer: bool = False) -> str:
    """Convert between Hiragana and Katakana."""
    table = _HIRAGANA_TABLE if hiraganer else _KATAKANA_TABLE
    return to_translate.translate(table)


def adjust_reading(reading: str) -> str:
    """Adjust reading for frequency lookup (katakana → hiragana)."""
    return kana_converter(reading)


def get_star_count(
    freq: int, star_char: str = "\u2605", thresholds: Optional[List[int]] = None
) -> str:
    """Convert frequency rank to star rating string."""
    if thresholds is None:
        thresholds = [1501, 5001, 15001, 30001, 60001]
    if freq < thresholds[0]:
        return star_char * 5
    if freq < thresholds[1]:
        return star_char * 4
    if freq < thresholds[2]:
        return star_char * 3
    if freq < thresholds[3]:
        return star_char * 2
    if freq < thresholds[4]:
        return star_char * 1
    return ""


# ── FrequencyEngine ───────────────────────────────


class FrequencyEngine:
    """Applies word-list frequency/level data to dictionary entries.

    Owns the multi-provider lookup logic, star computation, and level-label
    assembly. Does NOT own SQLite — callers pass providers explicitly.

    One adapter (WordListRegistry) = hypothetical seam.
    To test with fake providers, pass a list of WordListProvider directly.
    """

    def __init__(self, registry: Optional[WordListRegistry] = None) -> None:
        self._registry = registry

    # ── public ─────────────────────────────────────

    def apply(
        self,
        entry: Dict[str, Any],
        providers: List[WordListProvider],
        config: Dict[str, Any],
    ) -> None:
        """Mutate *entry* in-place with starCount, frequency, levelLabels."""
        show_stars = config.get("show_stars", True)
        show_rank = config.get("show_rank", False)
        show_level_labels = config.get("show_level_labels", True)
        word_list_visibility = config.get("word_list_visibility", {})

        levels: List[str] = []
        frequency: int = 999999
        term = entry["term"]
        alt = entry.get("altterm", "")
        entry_reading = adjust_reading(entry.get("pronunciation", "") or term)

        for provider in providers:
            name = provider.name
            lang_vis = word_list_visibility.get(provider.lang, {})
            if not lang_vis.get(name, True):
                continue

            result = provider.lookup(term, entry_reading)

            if not result.rank and not result.levels:
                if alt:
                    alt_result = provider.lookup(alt, entry_reading)
                    if alt_result and (
                        alt_result.rank is not None or alt_result.levels
                    ):
                        result = alt_result

            if result.rank is not None and result.rank < frequency:
                frequency = result.rank

            for level in result.levels:
                levels.append(f"{name}:{level}")

        # Apply collected levels
        entry["levelLabels"] = (
            " / ".join(levels) if levels and show_level_labels else ""
        )

        # Apply best found frequency rank
        if frequency == 999999 and entry.get("frequency"):
            try:
                frequency = int(entry["frequency"])
            except (ValueError, TypeError):
                logger.debug("Could not parse frequency: %s", entry.get("frequency"))

        if frequency != 999999:
            if show_stars:
                star_char = config.get("star_char", "\u2605")
                thresholds = config.get(
                    "star_thresholds", [1501, 5001, 15001, 30001, 60001]
                )
                entry["starCount"] = get_star_count(frequency, star_char, thresholds)
            if show_rank:
                entry["frequency"] = frequency
        else:
            if not show_stars:
                entry["starCount"] = ""
            if not show_rank:
                entry["frequency"] = ""

    def get_providers_for_lang(self, lang: str) -> List[WordListProvider]:
        if self._registry is None:
            return []
        return self._registry.get_providers(lang)

    # ── persistence helper ─────────────────────────

    def reapply_for_language(
        self,
        lang: str,
        config: Dict[str, Any],
        conn: sqlite3.Connection,
        dict_db: Any,
    ) -> int:
        """Re-compute and persist frequency/starCount for all existing
        dictionary entries of a given language.

        Requires a live SQLite connection and a DictDB reference for schema
        queries. Returns the number of entries updated.
        """
        providers = self.get_providers_for_lang(lang)
        if not providers:
            return 0

        cursor = conn.cursor()
        total = 0
        dict_names = dict_db.getDictsByLanguage(lang)

        for dict_name in dict_names:
            lid = dict_db.getLangIdFromDict(dict_name)
            if lid is None:
                continue
            table = dict_db.formatDictName(lid, dict_name)
            safe_table = f'"{table}"'

            try:
                cursor.execute(
                    f"SELECT rowid, term, altterm, pronunciation, definition, "
                    f"examples, audio, frequency, starCount FROM {safe_table}"
                )
            except Exception as e:
                logger.debug("Skipping %s: %s", table, e)
                continue

            for row in cursor.fetchall():
                entry: Dict[str, Any] = {
                    "term": row[1],
                    "altterm": row[2] or "",
                    "pronunciation": row[3] or "",
                    "definition": row[4] or "",
                    "frequency": row[7] or "",
                    "starCount": row[8] or "",
                    "levelLabels": "",
                }
                self.apply(entry, providers, config)

                new_freq = entry.get("frequency", "")
                new_stars = entry.get("starCount", "")
                try:
                    cursor.execute(
                        f"UPDATE {safe_table} SET frequency = ?, starCount = ? "
                        f"WHERE rowid = ?",
                        (new_freq, new_stars, row[0]),
                    )
                    total += 1
                except Exception as e:
                    logger.debug("Error updating row %s: %s", row[0], e)

            conn.commit()

        return total
