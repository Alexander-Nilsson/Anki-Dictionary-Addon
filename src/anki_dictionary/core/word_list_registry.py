from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from ..utils.paths import get_db_dir

logger = get_logger("word_list_registry")


@dataclass
class LookupResult:
    rank: Optional[int] = None
    levels: List[str] = field(default_factory=list)
    reading: str = ""


class WordListProvider:
    def __init__(
        self,
        type_: str,
        name: str,
        lang: str,
        description: str,
        data: Any,
    ) -> None:
        self.type = type_
        self.name = name
        self.lang = lang
        self.description = description
        self._data = data
        self._index: Optional[Dict[str, Any]] = None

        if isinstance(data, dict):
            if "index" in data and isinstance(data["index"], dict):
                self._index = data["index"]
            elif "list" in data and isinstance(data["list"], list):
                self._index = {}
                for item in data["list"]:
                    if isinstance(item, list) and len(item) >= 1:
                        self._index[item[0]] = item
            else:
                self._index = data
        elif isinstance(data, list) and type_ == "rank":
            # Plain list format: ["term1", "term2", ...] — rank at index
            self._index = {}
            for idx, term in enumerate(data):
                if isinstance(term, str):
                    self._index[term] = idx
        elif isinstance(data, list) and type_ == "level":
            # List-of-lists format: [[term, ...level], ...]
            self._index = {}
            for item in data:
                if isinstance(item, list) and len(item) >= 3:
                    level_val = item[2]
                    if isinstance(level_val, (int, float)):
                        self._index[str(item[0])] = str(int(level_val))

    def lookup(self, term: str, reading: str = "") -> LookupResult:
        if self.type == "rank":
            return self._lookup_rank(term, reading)
        else:
            return self._lookup_level(term, reading)

    def _lookup_rank(self, term: str, reading: str = "") -> LookupResult:
        if self._index is None:
            return LookupResult()

        if (
            self._data.get("readingDictionaryType")
            if isinstance(self._data, dict)
            else False
        ):
            if term in self._data and reading in self._data[term]:
                return LookupResult(rank=self._data[term][reading])
            return LookupResult()

        rank = self._index.get(term)
        if rank is not None:
            return LookupResult(rank=rank)  # type: ignore[arg-type]
        return LookupResult()

    def _lookup_level(self, term: str, reading: str = "") -> LookupResult:
        if self._index is None:
            return LookupResult()

        entry = self._index.get(term)
        if entry is None:
            return LookupResult()

        result = LookupResult(reading=reading)

        if isinstance(entry, (int, str)):
            result.levels = [str(entry)]
        elif isinstance(entry, list):
            if len(entry) >= 3 and isinstance(entry[2], list):
                result.levels = entry[2]
                if len(entry) >= 2 and isinstance(entry[1], str):
                    result.reading = entry[1]
            elif len(entry) >= 2 and isinstance(entry[1], str):
                result.reading = entry[1]

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "lang": self.lang,
            "description": self.description,
        }


class WordListRegistry:
    DATA_DIR = "word_lists"

    def __init__(self, db_dir: str) -> None:
        self._dir = os.path.join(db_dir, self.DATA_DIR)
        self._cache: Dict[str, List[WordListProvider]] = {}
        self._migrated = False

    @property
    def word_lists_dir(self) -> str:
        return self._dir

    def get_providers(self, lang: str) -> List[WordListProvider]:
        if lang in self._cache:
            return self._cache[lang]

        self._ensure_migration()
        os.makedirs(self._dir, exist_ok=True)

        providers: List[WordListProvider] = []
        prefix_underscore = lang.replace(" ", "_") + "_"
        prefix_space = lang + " "

        if os.path.exists(self._dir):
            for filename in os.listdir(self._dir):
                if not filename.endswith(".json"):
                    continue
                if not (
                    filename.startswith(prefix_underscore)
                    or filename.startswith(prefix_space)
                    or filename.startswith(lang + "_")
                    or filename == f"{lang}.json"
                ):
                    continue

                filepath = os.path.join(self._dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
                    continue

                name = self._name_from_filename(filename, lang)
                type_ = self._detect_type(data)
                providers.append(WordListProvider(type_, name, lang, "", data))

        self._cache[lang] = providers
        return providers

    def add_list(
        self,
        lang: str,
        name: str,
        data: Any,
        type_: str,
        description: str = "",
    ) -> str:
        os.makedirs(self._dir, exist_ok=True)
        slug = self._slug(name)
        filename = f"{self._slug(lang)}_{slug}.json"
        filepath = os.path.join(self._dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        self._cache.pop(lang, None)
        return filepath

    def _ensure_migration(self) -> None:
        if self._migrated:
            return
        self._migrated = True

    def clear_cache(self, lang: Optional[str] = None) -> None:
        if lang:
            self._cache.pop(lang, None)
        else:
            self._cache.clear()

    @staticmethod
    def _detect_type(data: Any) -> str:
        if isinstance(data, list):
            if (
                data
                and isinstance(data[0], list)
                and len(data[0]) >= 3
                and data[0][1] == "freq"
            ):
                return "level"
            return "rank"
        if isinstance(data, dict):
            if "index" in data or "list" in data:
                return "level"
            if data.get("readingDictionaryType") is not None:
                return "rank"
            first_val = next(iter(data.values()), None)
            if isinstance(first_val, (int, float)):
                return "rank"
            if isinstance(first_val, str):
                return "level"
            return "level"
        return "rank"

    @staticmethod
    def _name_from_filename(filename: str, lang: str) -> str:
        name = filename.replace(".json", "")
        stripped = False
        for sep in [" ", "_"]:
            prefix = lang.replace(" ", sep) + sep
            if name.startswith(prefix):
                name = name[len(prefix) :]
                stripped = True
                break
        base = lang.replace(" ", "_")
        if not stripped and name.lower() == base.lower():
            name = "Frequency"
        if name == "" or name.lower() == "frequency":
            name = "Frequency"
        return name.replace("_", " ").title()

    @staticmethod
    def _slug(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "_", text)
        text = text.strip("_")
        return text or "unnamed"
