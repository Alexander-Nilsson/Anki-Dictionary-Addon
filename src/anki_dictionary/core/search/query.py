from __future__ import annotations

import re
import sqlite3
from collections import OrderedDict
from threading import Lock
from typing import Any

from ...utils.config import get_addon_config
from ...utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

_SEARCH_COLUMNS = (
    "term, altterm, pronunciation, pos, definition, examples, audio, "
    "starCount, frequency"
)
_CACHE_MAX_ENTRIES = 256
_CACHE_MAX_ROWS = 4096
_SQL_CHUNK = 900


class SearchQueryBuilder:
    def __init__(self, dict_db: Any) -> None:
        self._db = dict_db
        self._row_cache: OrderedDict[tuple[Any, ...], list[tuple[Any, ...]]] = (
            OrderedDict()
        )
        self._cached_rows = 0
        self._cache_revision: int | None = None
        self._cache_lock = Lock()
        self._indexed_columns: set[tuple[str, str]] = set()
        self._index_lock = Lock()

    def get_def_ex(self, sT: str) -> bool:
        return sT == "Definition"

    def apply_search_type(self, terms: list[str], sT: str) -> list[str]:
        for idx, _term in enumerate(terms):
            if sT in ("Forward", "Pronunciation"):
                terms[idx] = terms[idx] + "%"
            elif sT == "Backward":
                terms[idx] = "%_" + terms[idx]
            elif sT == "Anywhere":
                terms[idx] = "%" + terms[idx] + "%"
            elif sT == "Exact":
                terms[idx] = terms[idx]
            elif sT == "Definition":
                terms[idx] = "%" + terms[idx] + "%"
            else:
                # Unknown/legacy mode: behave like Forward rather than
                # searching a punctuation pattern that no data contains.
                terms[idx] = terms[idx] + "%"
        return terms

    def deconjugate(
        self, terms: list[str], conjugations: list[dict[str, Any]]
    ) -> list[str]:
        deconjugations: list[str] = []
        for term in terms:
            for c in conjugations:
                if term.endswith(c["inflected"]):
                    for x in c["dict"]:
                        deinflected = self._rreplace(term, c["inflected"], x, 1)
                        if "prefix" in c:
                            prefix = c["prefix"]
                            if deinflected.startswith(prefix):
                                deprefixed = deinflected[len(prefix) :]
                                if deprefixed not in deconjugations:
                                    deconjugations.append(deprefixed)
                        if deinflected not in deconjugations:
                            deconjugations.append(deinflected)
        deconjugations = [x for x in set(filter(lambda x: len(x) > 1, deconjugations))]
        return terms + deconjugations

    @staticmethod
    def _rreplace(s: str, old: str, new: str, occurrence: int) -> str:
        return new.join(s.rsplit(old, occurrence))

    @staticmethod
    def get_query_criteria(col: str, terms: list[str], op: str = "LIKE") -> str:
        clauses = [f" {col} {op} ? " for _ in terms]
        return " OR ".join(clauses)

    @staticmethod
    def _quote_identifier(name: str) -> str:
        return f'"{name}"'

    @staticmethod
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

    @staticmethod
    def clean_lt(text: Any) -> str:
        return re.sub(r"<((?:[^b][^r])|(?:[b][^r]))", r"&lt;\1", str(text))

    @staticmethod
    def result_to_dict(r: tuple[Any, ...]) -> dict[str, Any]:
        frequency: Any = r[8] if len(r) > 8 else ""
        return {
            "term": r[0],
            "altterm": r[1],
            "pronunciation": r[2],
            "pos": r[3],
            "definition": SearchQueryBuilder.process_definition_html(r[4]),
            "examples": r[5],
            "audio": r[6],
            "starCount": r[7],
            "frequency": frequency,
            "levelLabels": "",
        }

    @staticmethod
    def _covering_column(column: str, op: str, terms: list[str]) -> str | None:
        """Return the column to index for a substring scan, if supported.

        Only leading-wildcard LIKE patterns need the covering scan.  Prefix
        and exact searches already use the term B-trees, and ``definition``
        matches still require a table scan (no FTS index is maintained).
        """
        if op != "LIKE" or column not in ("term", "altterm", "pronunciation"):
            return None
        if any(isinstance(t, str) and t.startswith("%") for t in terms):
            return column
        return None

    def _ensure_covering_index(self, dict_name: str, column: str) -> bool:
        key = (dict_name, column)
        if key in self._indexed_columns:
            return True
        with self._index_lock:
            if key in self._indexed_columns:
                return True
            if self._db.ensure_frequency_index(dict_name, column):
                self._indexed_columns.add(key)
                return True
            return False

    def _table_search(
        self,
        cursor: sqlite3.Cursor,
        dict_name: str,
        to_query: str,
        dict_limit: int,
        term_tuple: tuple[Any, ...],
    ) -> list[tuple[Any, ...]]:
        safe_table = self._quote_identifier(dict_name)
        cursor.execute(
            f"SELECT {_SEARCH_COLUMNS} FROM {safe_table} WHERE {to_query}"
            " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT ?",
            term_tuple + (dict_limit,),
        )
        return cursor.fetchall()

    def _covered_search(
        self,
        cursor: sqlite3.Cursor,
        dict_name: str,
        to_query: str,
        dict_limit: int,
        term_tuple: tuple[Any, ...],
    ) -> list[tuple[Any, ...]]:
        """Match and rank on the covering index, then fetch full rows.

        The original query reads every table row (including the definition
        text) just to throw most of them away.  Scanning ``(column, term,
        frequency)`` keeps the match/order phase index-only; only the LIMIT
        rows are read from the table.
        """
        safe_table = self._quote_identifier(dict_name)
        cursor.execute(
            f"SELECT rowid, term, frequency FROM {safe_table} WHERE {to_query}"
            " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT ?",
            term_tuple + (dict_limit,),
        )
        ranked = cursor.fetchall()
        if not ranked:
            return []
        rowids = [row[0] for row in ranked]
        rows_by_id: dict[int, tuple[Any, ...]] = {}
        for start in range(0, len(rowids), _SQL_CHUNK):
            chunk = rowids[start : start + _SQL_CHUNK]
            placeholders = ",".join("?" for _ in chunk)
            cursor.execute(
                f"SELECT rowid, {_SEARCH_COLUMNS} FROM {safe_table}"
                f" WHERE rowid IN ({placeholders})",
                chunk,
            )
            for row in cursor.fetchall():
                rows_by_id[row[0]] = row[1:]
        return [rows_by_id[rid] for rid in rowids if rid in rows_by_id]

    def _sync_cache_revision(self) -> None:
        revision = self._db.data_revision
        if revision != self._cache_revision:
            self._row_cache.clear()
            self._cached_rows = 0
            self._cache_revision = revision

    def _cache_get(self, key: tuple[Any, ...]) -> list[tuple[Any, ...]] | None:
        with self._cache_lock:
            self._sync_cache_revision()
            rows = self._row_cache.get(key)
            if rows is None:
                return None
            self._row_cache.move_to_end(key)
            return rows

    def _cache_put(self, key: tuple[Any, ...], rows: list[tuple[Any, ...]]) -> None:
        if len(rows) > _CACHE_MAX_ROWS:
            return
        with self._cache_lock:
            self._sync_cache_revision()
            if key in self._row_cache:
                return
            self._row_cache[key] = rows
            self._cached_rows += len(rows)
            while self._row_cache and (
                len(self._row_cache) > _CACHE_MAX_ENTRIES
                or self._cached_rows > _CACHE_MAX_ROWS
            ):
                _, evicted = self._row_cache.popitem(last=False)
                self._cached_rows -= len(evicted)

    def execute_search(
        self,
        dict_name: str,
        to_query: str,
        dict_limit: int,
        term_tuple: tuple[Any, ...],
        covering_column: str | None = None,
    ) -> list[tuple[Any, ...]]:
        cache_key = (dict_name, to_query, term_tuple, dict_limit)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        cursor = self._db._get_cursor()
        try:
            if covering_column and self._ensure_covering_index(
                dict_name, covering_column
            ):
                rows = self._covered_search(
                    cursor, dict_name, to_query, dict_limit, term_tuple
                )
            else:
                rows = self._table_search(
                    cursor, dict_name, to_query, dict_limit, term_tuple
                )
        except sqlite3.Error as e:
            logger.error(f"Search error in dictionary '{dict_name}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching dictionary '{dict_name}': {e}")
            return []
        self._cache_put(cache_key, rows)
        return rows

    def get_term_frequency_info(
        self, term: str, lang: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        if not lang:
            return {"term": term, "starCount": "", "levelLabels": ""}
        providers = self._db._get_extra_data(lang)
        if not providers:
            return {"term": term, "starCount": "", "levelLabels": ""}
        entry = {
            "term": term,
            "altterm": "",
            "pronunciation": "",
            "starCount": "",
            "levelLabels": "",
        }
        self._apply_frequency_info(entry, providers, config)
        return entry

    def _apply_frequency_info(
        self,
        entry: dict[str, Any],
        providers: list[Any],
        config: dict[str, Any],
    ) -> None:
        self._db._apply_frequency_info(entry, providers, config)

    def search(
        self,
        term: str,
        selected_group: dict[str, Any],
        conjugations: dict[str, list[dict[str, Any]]],
        sT: str,
        deinflect: bool,
        dict_limit: int,
        max_defs: int,
    ) -> dict[str, Any]:
        already_conj_typed: dict[str, list[str]] = {}
        results: dict[str, Any] = {}
        group = selected_group["dictionaries"]
        total_defs = 0
        def_ex = self.get_def_ex(sT)
        op = "LIKE"
        if def_ex:
            column = "definition"
        elif sT == "Pronunciation":
            column = "pronunciation"
        else:
            column = "term"
        if sT == "Exact":
            op = "="
        base_terms = [term]
        if term.lower() not in base_terms:
            base_terms.append(term.lower())
        if term.capitalize() not in base_terms:
            base_terms.append(term.capitalize())

        dict_mapping = self._db.getDictToTable()
        langs = set()
        for dic in group:
            d_name = dic["dict"]
            if d_name in ("Images", "LLM", "Forvo"):
                continue
            info = dict_mapping.get(d_name) or dict_mapping.get(
                self._db.cleanDictName(d_name)
            )
            if info:
                langs.add(info["lang"])
            elif "lang" in dic:
                langs.add(dic["lang"])

        extra_data = {lang: self._db._get_extra_data(lang) for lang in langs}
        config = get_addon_config()

        for dic in group:
            d_name = dic["dict"]
            if d_name in ("Images", "LLM", "Forvo"):
                results[d_name] = True
                continue

            info = (
                dict_mapping.get(d_name)
                or dict_mapping.get(d_name.lower())
                or dict_mapping.get(self._db.cleanDictName(d_name))
                or dict_mapping.get(self._db.cleanDictName(d_name).lower())
                or dict_mapping.get(self._db.normalize_dict_name(d_name))
                or dict_mapping.get(self._db.normalize_dict_name(d_name).lower())
            )
            if info:
                table_name = info["dict"]
                lang = info["lang"]
            else:
                table_name = d_name
                lang = dic.get("lang", "")

            providers = extra_data.get(lang, [])

            cache_key = f"{lang}_{sT}" if not deinflect else lang
            if cache_key in already_conj_typed:
                current_terms = already_conj_typed[cache_key]
            else:
                if deinflect and lang in conjugations:
                    current_terms = self.deconjugate(
                        list(base_terms), conjugations[lang]
                    )
                else:
                    current_terms = list(base_terms)
                current_terms = self.apply_search_type(current_terms, sT)
                already_conj_typed[cache_key] = current_terms

            to_query = self.get_query_criteria(column, current_terms, op)
            term_tuple = tuple(current_terms)
            all_rows = self.execute_search(
                table_name,
                to_query,
                dict_limit,
                term_tuple,
                self._covering_column(column, op, current_terms),
            )

            if all_rows:
                dict_res = []
                for r in all_rows:
                    total_defs += 1
                    entry = self.result_to_dict(r)
                    self._apply_frequency_info(entry, providers, config)
                    dict_res.append(entry)
                    if total_defs >= max_defs:
                        results[d_name] = dict_res
                        return results
                results[d_name] = dict_res
            elif not def_ex and sT != "Pronunciation":
                for col in ("altterm", "pronunciation"):
                    to_query = self.get_query_criteria(col, current_terms, op)
                    all_rows = self.execute_search(
                        table_name,
                        to_query,
                        dict_limit,
                        term_tuple,
                        self._covering_column(col, op, current_terms),
                    )
                    if all_rows:
                        dict_res = []
                        for r in all_rows:
                            total_defs += 1
                            entry = self.result_to_dict(r)
                            self._apply_frequency_info(entry, providers, config)
                            dict_res.append(entry)
                            if total_defs >= max_defs:
                                results[d_name] = dict_res
                                return results
                        results[d_name] = dict_res
                        break
        return results

    def get_def_for_mass_exp(
        self, term: str, dN: str, limit: int, rN: str
    ) -> tuple[list[dict[str, Any]], Any, Any]:
        dup_result = self._db.getDuplicateSetting(rN)
        duplicate_header, term_header = dup_result if dup_result else (None, None)
        results: list[dict[str, Any]] = []
        for col in ("term", "altterm", "pronunciation"):
            terms = [term]
            to_query = f" {col} = ? "
            all_rows = self.execute_search(dN, to_query, limit, tuple(terms))
            if all_rows:
                results = [self.result_to_dict(r) for r in all_rows]
                break
        return results, duplicate_header, term_header
