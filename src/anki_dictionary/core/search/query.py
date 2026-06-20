from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List, Tuple

from ...utils.config import get_addon_config
from ...utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class SearchQueryBuilder:
    def __init__(self, dict_db: Any) -> None:
        self._db = dict_db

    def get_def_ex(self, sT: str) -> bool:
        return sT in ("Definition", "Example")

    def apply_search_type(self, terms: List[str], sT: str) -> List[str]:
        for idx, term in enumerate(terms):
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
                terms[idx] = "%「%" + terms[idx] + "%」%"
        return terms

    def deconjugate(
        self, terms: List[str], conjugations: List[Dict[str, Any]]
    ) -> List[str]:
        deconjugations: List[str] = []
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
    def get_query_criteria(col: str, terms: List[str], op: str = "LIKE") -> str:
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
    def result_to_dict(r: Tuple[Any, ...]) -> Dict[str, Any]:
        return {
            "term": r[0],
            "altterm": r[1],
            "pronunciation": r[2],
            "pos": r[3],
            "definition": SearchQueryBuilder.process_definition_html(r[4]),
            "examples": r[5],
            "audio": r[6],
            "starCount": r[7],
            "levelLabels": "",
        }

    def execute_search(
        self,
        dict_name: str,
        to_query: str,
        dict_limit: int,
        term_tuple: Tuple[Any, ...],
    ) -> List[Tuple[Any, ...]]:
        cursor = self._db._get_cursor()
        safe_table = self._quote_identifier(dict_name)
        cols = (
            "term, altterm, pronunciation, pos, definition, examples, audio, starCount"
        )
        query = (
            f"SELECT {cols} FROM {safe_table} WHERE {to_query}"
            " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT ?"
        )
        try:
            cursor.execute(query, term_tuple + (dict_limit,))
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Search error in dictionary '{dict_name}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching dictionary '{dict_name}': {e}")
            return []

    def get_term_frequency_info(
        self, term: str, lang: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        entry: Dict[str, Any],
        providers: List[Any],
        config: Dict[str, Any],
    ) -> None:
        for provider in providers:
            lookup = provider.lookup(entry["term"], entry.get("altterm") or "")
            if lookup.frequency is not None:
                freq = int(lookup.frequency) if lookup.frequency else 0
                count = self._db.getStarCount(freq)
                if count:
                    entry["starCount"] = count
                if lookup.labels:
                    entry["levelLabels"] = ", ".join(lookup.labels)

    def search(
        self,
        term: str,
        selected_group: Dict[str, Any],
        conjugations: Dict[str, List[Dict[str, Any]]],
        sT: str,
        deinflect: bool,
        dict_limit: int,
        max_defs: int,
    ) -> Dict[str, Any]:
        already_conj_typed: Dict[str, List[str]] = {}
        results: Dict[str, Any] = {}
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
            all_rows = self.execute_search(table_name, to_query, dict_limit, term_tuple)

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
                        table_name, to_query, dict_limit, term_tuple
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
    ) -> Tuple[List[Dict[str, Any]], Any, Any]:
        dup_result = self._db.getDuplicateSetting(rN)
        duplicate_header, term_header = dup_result if dup_result else (None, None)
        results: List[Dict[str, Any]] = []
        for col in ("term", "altterm", "pronunciation"):
            terms = [term]
            to_query = f" {col} = ? "
            all_rows = self.execute_search(dN, to_query, limit, tuple(terms))
            if all_rows:
                results = [self.result_to_dict(r) for r in all_rows]
                break
        return results, duplicate_header, term_header
