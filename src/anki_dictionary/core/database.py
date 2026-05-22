# -*- coding: utf-8 -*-

import sqlite3
import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from aqt.utils import showInfo
from aqt import mw
from ..utils.paths import (
    get_addon_root,
    get_db_dir,
    get_frequency_dir,
    get_hsk_dir,
    get_addon_name,
)
from ..utils.common import miInfo
from ..utils.logger import get_logger
from ..utils.config import get_addon_config

# Initialize logger
logger = get_logger("database")


class DictDB:
    """Database interface for dictionary management."""

    def __init__(self) -> None:
        """Initialize the database connection."""
        self.conn: Optional[sqlite3.Connection] = None
        self.c: Optional[sqlite3.Cursor] = None
        self.oldConnection: Optional[sqlite3.Cursor] = None
        self._freq_cache: Dict[str, Dict[str, Any]] = {}
        self._hsk_cache: Dict[str, Dict[str, int]] = {}
        self._extra_data_cache: Dict[str, List[Dict[str, Any]]] = {}

        # Get the root addon directory
        self.addon_root = get_addon_root()
        addon_name = get_addon_name()

        # First try direct path from addon root
        db_file = os.path.join(get_db_dir(), "dictionaries.sqlite")

        # If that doesn't exist, try using Anki's addon folder structure
        if not os.path.exists(db_file):
            db_file = os.path.join(
                mw.pm.addonFolder(),
                addon_name,
                "user_files",
                "db",
                "dictionaries.sqlite",
            )

        # Ensure the directory exists
        db_dir = os.path.dirname(db_file)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        try:
            self.conn = sqlite3.connect(db_file, check_same_thread=False)
            self.c = self.conn.cursor()
            self.c.execute("PRAGMA foreign_keys = ON")
            self.c.execute("PRAGMA case_sensitive_like=ON;")
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e} - Path: {db_file}")
            miInfo(f"Database error: {e}\nAttempted path: {db_file}", level="err")
            raise

    def _ensure_connection(self) -> bool:
        """Ensure database connection is active. Returns True if connection is ready."""
        return self.conn is not None and self.c is not None

    def _get_connection(self) -> sqlite3.Connection:
        """Get the database connection, ensuring it exists."""
        if not self._ensure_connection() or self.conn is None:
            raise RuntimeError("Database connection not initialized")
        return self.conn

    def _get_cursor(self) -> sqlite3.Cursor:
        """Get the database cursor, ensuring it exists."""
        if not self._ensure_connection() or self.c is None:
            raise RuntimeError("Database connection not initialized")
        return self.c

    def closeConnection(self) -> None:
        """Close the database connection."""
        if self.c:
            self.c.close()
        if self.conn:
            self.conn.close()

    def _get_extra_data(self, lang: str) -> List[Dict[str, Any]]:
        """Load all frequency and level data for a language."""
        if lang in self._extra_data_cache:
            return self._extra_data_cache[lang]

        providers = []
        config = get_addon_config()

        # 1. Try to load main frequency list from frequency/{lang}.json
        main_freq = self._get_frequency_list(lang)
        if main_freq:
            providers.append({"type": "rank", "name": "Frequency", "data": main_freq})

        # 2. Try to load HSK data (Special case for Chinese for now)
        if any(x in lang.lower() for x in ["zh", "chinese", "cn"]):
            hsk_mode = config.get("hsk_mode", "hsk3")
            hsk_data = self._get_hsk_list(lang, hsk_mode)
            if hsk_data:
                for version, data in hsk_data.items():
                    name = "HSK"
                    if version == "2.0":
                        name = "HSK²"
                    elif version == "3.0":
                        name = "HSK³"
                    providers.append({"type": "level", "name": name, "data": data})

        # 3. Future: Scan frequency directory for any {lang}_*.json files
        # This allows for arbitrary extra data like JLPT, CEFR etc.
        freq_dir = get_frequency_dir()
        if os.path.exists(freq_dir):
            for filename in os.listdir(freq_dir):
                if filename.startswith(lang + "_") and filename.endswith(".json"):
                    label = filename[len(lang) + 1 : -5]
                    data = self._load_extra_file(os.path.join(freq_dir, filename))
                    if data:
                        providers.append(
                            {
                                "type": "level" if isinstance(data, dict) else "rank",
                                "name": label,
                                "data": data,
                            }
                        )

        self._extra_data_cache[lang] = providers
        return providers

    def _load_extra_file(self, path: str) -> Any:
        """Load a JSON file and return its data."""
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading extra data file {path}: {e}")
            return None

    def _get_frequency_list(self, lang: str) -> Optional[Dict[str, Any]]:
        """Load frequency list for a language from central file."""
        if lang in self._freq_cache:
            return self._freq_cache[lang]

        freq_path = os.path.join(get_frequency_dir(), f"{lang}.json")
        if not os.path.exists(freq_path):
            return None

        try:
            with open(freq_path, "r", encoding="utf-8-sig") as f:
                frequency_list = json.load(f)

            if not frequency_list:
                return None

            frequency_dict = {}
            if isinstance(frequency_list[0], str):
                yomi = False
                frequency_dict["readingDictionaryType"] = False
            elif (
                isinstance(frequency_list[0], list)
                and len(frequency_list[0]) == 2
                and isinstance(frequency_list[0][0], str)
                and isinstance(frequency_list[0][1], str)
            ):
                yomi = True
                frequency_dict["readingDictionaryType"] = True
            else:
                return None

            for idx, f in enumerate(frequency_list):
                if yomi:
                    term = f[0].strip()
                    reading = f[1].strip()
                    if term in frequency_dict:
                        frequency_dict[term][reading] = idx
                    else:
                        frequency_dict[term] = {reading: idx}
                else:
                    term = f.strip()
                    if term not in frequency_dict:
                        frequency_dict[term] = idx

            self._freq_cache[lang] = frequency_dict
            return frequency_dict
        except Exception as e:
            logger.error(f"Error loading frequency list for {lang}: {e}")
            return None

    def _get_hsk_list(self, lang: str, mode: str = "hsk3") -> Optional[Dict[str, Any]]:
        """Load HSK level list(s) from central file."""
        cache_key = f"{lang}_{mode}"
        if cache_key in self._hsk_cache:
            return self._hsk_cache[cache_key]

        hsk_dir = get_hsk_dir()
        result = {}

        def load_file(filename):
            path = os.path.join(hsk_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading HSK file {filename}: {e}")
            return None

        if mode == "hsk2":
            data = (
                load_file(f"{lang}_hsk2.json")
                or load_file("zh_hsk2.json")
                or load_file(f"{lang}.json")
                or load_file("zh.json")
            )
            if data:
                result["2.0"] = data
        elif mode == "hsk3":
            data = (
                load_file(f"{lang}_hsk3.json")
                or load_file("zh_hsk3.json")
                or load_file(f"{lang}.json")
                or load_file("zh.json")
            )
            if data:
                result["3.0"] = data
        elif mode == "both":
            d2 = load_file(f"{lang}_hsk2.json") or load_file("zh_hsk2.json")
            d3 = load_file(f"{lang}_hsk3.json") or load_file("zh_hsk3.json")
            if d2:
                result["2.0"] = d2
            if d3:
                result["3.0"] = d3
            if not d2 and not d3:
                data = load_file(f"{lang}.json") or load_file("zh.json")
                if data:
                    result["both"] = data

        if not result:
            return None

        self._hsk_cache[cache_key] = result
        return result

    def getStarCount(self, freq: int) -> str:
        """Convert frequency rank to star rating."""
        config = get_addon_config()
        star_char = config.get("star_char", "★")
        thresholds = config.get("star_thresholds", [1501, 5001, 15001, 30001, 60001])

        if freq < thresholds[0]:
            return star_char * 5
        elif freq < thresholds[1]:
            return star_char * 4
        elif freq < thresholds[2]:
            return star_char * 3
        elif freq < thresholds[3]:
            return star_char * 2
        elif freq < thresholds[4]:
            return star_char * 1
        else:
            return ""

    def _apply_frequency_info(self, entry, providers, config):
        """Apply frequency and level information to an entry from multiple providers."""
        show_stars = config.get("show_stars", True)
        show_rank = config.get("show_rank", False)
        show_hsk = config.get("show_hsk", True)

        levels = []
        frequency = 999999
        term = entry["term"]
        alt = entry["altterm"]

        for provider in providers:
            p_type = provider.get("type")
            p_name = provider.get("name")
            p_data = provider.get("data")

            if p_type == "level" and show_hsk:
                # Level map: {"term": level}
                lvl = p_data.get(term) or p_data.get(alt)
                if lvl:
                    levels.append(f"{p_name}:{lvl}")

            elif p_type == "rank" and (show_stars or show_rank):
                # Rank list: {"term": rank} or {"term": {"reading": rank}}
                entry_reading = self.adjustReading(entry["pronunciation"] or term)

                if p_data.get("readingDictionaryType"):
                    if term in p_data and entry_reading in p_data[term]:
                        p_rank = p_data[term][entry_reading]
                        if p_rank < frequency:
                            frequency = p_rank
                elif term in p_data:
                    p_rank = p_data[term]
                    if p_rank < frequency:
                        frequency = p_rank

        # Apply collected levels
        if levels:
            entry["hskLevel"] = " / ".join(levels)

        # Apply best found frequency rank
        # Fallback to entry's own frequency if still not found
        if frequency == 999999 and entry.get("frequency"):
            try:
                frequency = int(entry["frequency"])
            except (ValueError, TypeError):
                pass

        if frequency != 999999:
            if show_stars:
                entry["starCount"] = self.getStarCount(frequency)
            if show_rank:
                entry["frequency"] = frequency
        else:
            # If we have no frequency number but we DO have a starCount string from the dict
            # and stars are enabled, keep it. Otherwise clear it.
            if not show_stars:
                entry["starCount"] = ""
            if not show_rank:
                entry["frequency"] = ""

    def kana_converter(self, to_translate: str, hiraganer: bool = False) -> str:
        """Convert between Hiragana and Katakana."""
        hiragana = (
            "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"
            "あいうえおかきくけこさしすせそたちつてと"
            "なにぬねのはひふへほまみむめもやゆよらりるれろ"
            "わをんぁぃぅぇぉゃゅょっゐゑ"
        )
        katakana = (
            "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"
            "アイウエオカキクケコサシスセソタチツテト"
            "ナニヌネノハヒフヘホマミムメモヤユヨラリルレロ"
            "ワヲンァィゥェォャュョッヰヱ"
        )
        if hiraganer:
            katakana_ords = [ord(char) for char in katakana]
            translate_table = dict(zip(katakana_ords, hiragana))
            return to_translate.translate(translate_table)
        else:
            hiragana_ords = [ord(char) for char in hiragana]
            translate_table = dict(zip(hiragana_ords, katakana))
            return to_translate.translate(translate_table)

    def adjustReading(self, reading: str) -> str:
        """Adjust reading for frequency lookup."""
        return self.kana_converter(reading)

    def getLangId(self, lang: str) -> Optional[int]:
        """Get language ID from language name."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT id FROM langnames WHERE langname = ?;", (lang,))
        result = cursor.fetchone()
        return result[0] if result else None

    def deleteDict(self, d: str) -> None:
        """Delete a dictionary and its associated tables."""
        if not self._ensure_connection():
            return

        # d can be the raw table name (l1name...) or just the dict name
        if d.startswith("l") and "name" in d:
            table_name = d
            d_clean = self.cleanDictName(d)
        else:
            d_clean = d
            lid = self.getLangIdFromDict(d_clean)
            table_name = self.formatDictName(lid, d_clean)

        self.dropTables(table_name)
        cursor = self._get_cursor()
        cursor.execute(
            "DELETE FROM dictnames WHERE dictname = ? COLLATE NOCASE;", (d_clean,)
        )
        self.commitChanges()
        cursor.execute("VACUUM;")

    def getLangIdFromDict(self, dictname: str) -> Optional[int]:
        """Get language ID for a given dictionary name."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT lid FROM dictnames WHERE dictname = ? COLLATE NOCASE;", (dictname,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def getDictsByLanguage(self, lang: str) -> List[str]:
        """Get all dictionary names for a given language."""
        if not self._ensure_connection():
            return []
        lid = self.getLangId(lang)
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname FROM dictnames WHERE lid = ?;", (lid,))
        try:
            langs: List[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def dictExists(self, dictname: str, lang: str) -> bool:
        """Check if a dictionary already exists for a given language."""
        if not self._ensure_connection():
            return False
        lid = self.getLangId(lang)
        if lid is None:
            return False
        clean_name = self.normalize_dict_name(dictname)
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT 1 FROM dictnames WHERE dictname = ? COLLATE NOCASE AND lid = ?;",
            (clean_name, lid),
        )
        return cursor.fetchone() is not None

    def addDict(
        self, dictname: str, lang: str, termHeader: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Add a new dictionary to the database."""
        if not self._ensure_connection():
            return False, "Database connection failed", None
        try:
            lid = self.getLangId(lang)
            clean_name = self.normalize_dict_name(dictname)
            cursor = self._get_cursor()

            # Check if it already exists
            cursor.execute(
                "SELECT lid FROM dictnames WHERE dictname = ? COLLATE NOCASE;",
                (clean_name,),
            )
            existing = cursor.fetchone()
            if existing:
                return False, "duplicate", clean_name

            cursor.execute(
                'INSERT INTO dictnames (dictname, lid, fields, addtype, termHeader, duplicateHeader) VALUES (?, ?, "[]", "add", ?, 0);',
                (clean_name, lid, termHeader),
            )
            self.createDB(self.formatDictName(lid, clean_name))
            self.commitChanges()

            success = True
            message = "Dictionary added successfully"
            final_name = clean_name
            return success, message, final_name

        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                return False, "duplicate", self.normalize_dict_name(dictname)
            return False, str(e), None
        except Exception as e:
            success = False
            message = str(e)
            final_name = None
            return success, message, final_name

    def normalize_dict_name(self, name: str) -> str:
        """Normalize dictionary name for database use."""
        if not name:
            return "unnamed_dictionary"

        replacements = {
            "[": "",
            "]": "",
            "(": "",
            ")": "",
            "{": "",
            "}": "",
            "<": "",
            ">": "",
            "'": "",
            '"': "",
            "`": "",
            "´": "",
            "/": "_",
            "\\": "_",
            "|": "_",
            ":": "_",
            "*": "",
            "?": "",
            "!": "",
            "@": "",
            "#": "",
            "$": "",
            "%": "",
            "^": "",
            "&": "",
            "=": "",
            "+": "",
            ",": "",
            ";": "",
            "~": "",
            "-": "",
            ".": "",
            "．": ".",
            "。": ".",
            "　": "_",  # Full-width space
            " ": "_",  # Regular space
        }

        result = name
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        # Remove any remaining problematic characters
        result = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", result)

        # Ensure valid length
        if len(result) > 100:
            result = result[:100]

        return result if result else "unnamed_dictionary"

    def formatDictName(self, lid: Optional[int], name: str) -> str:
        """Format dictionary name with language ID prefix."""
        return "l" + str(lid) + "name" + name

    def deleteLanguage(self, langname: str) -> None:
        """Delete a language and all its dictionaries."""
        if not self._ensure_connection():
            return
        self.dropTables("l" + str(self.getLangId(langname)) + "name%")
        cursor = self._get_cursor()
        cursor.execute("DELETE FROM langnames WHERE langname = ?;", (langname,))
        self.commitChanges()
        cursor.execute("VACUUM;")

    def addLanguages(self, list: List[str]) -> None:
        """Add multiple languages to the database."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        for l in list:
            cursor.execute("INSERT INTO langnames (langname) VALUES (?);", (l,))
        self.commitChanges()

    def getCurrentDbLangs(self) -> List[str]:
        """Get all languages currently in the database."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT langname FROM langnames;")
        try:
            langs: List[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def getUserGroups(self, dicts: List[str]) -> List[Dict[str, str]]:
        """Get user dictionary groups based on provided dictionary names."""
        currentDicts = self.getDictToTable()
        foundDicts: List[Dict[str, str]] = []
        for d in dicts:
            # Check for both raw table name and clean name
            if d in currentDicts:
                foundDicts.append(currentDicts[d])
            elif d in ["Images", "LLM", "Forvo"]:
                # Virtual dictionaries
                if d == "Images":
                    foundDicts.append({"dict": "Images", "lang": ""})
                elif d == "LLM":
                    foundDicts.append({"dict": "LLM", "lang": ""})
                elif d == "Forvo":
                    foundDicts.append({"dict": "Forvo", "lang": ""})
                # Try finding by clean name if d is a table name
                clean_d = self.cleanDictName(d)
                if clean_d in currentDicts:
                    foundDicts.append(currentDicts[clean_d])
        return foundDicts

    def getDictToTable(self) -> Dict[str, Dict[str, str]]:
        """Get dictionary to table mapping."""
        if not self._ensure_connection():
            return {}
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;"
        )
        try:
            dicts: Dict[str, Dict[str, str]] = {}
            allDs = cursor.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    # Key by both clean name and formatted table name for easier lookup
                    table_name = self.formatDictName(d[1], d[0])
                    info = {
                        "dict": table_name,
                        "lang": d[2],
                    }
                    # Store with original casing
                    dicts[d[0]] = info
                    dicts[table_name] = info
                    # Also store with lowercase for case-insensitive lookup
                    dicts[d[0].lower()] = info
                    dicts[table_name.lower()] = info
            return dicts
        except:
            return {}

    def fetchDefs(self) -> List[str]:
        """Fetch definitions from dictname table."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT definition FROM dictname LIMIT 10;")
        try:
            langs: List[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def getAllDicts(self) -> List[str]:
        """Get all dictionary names formatted with language prefix."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, lid FROM dictnames;")
        try:
            dicts: List[str] = []
            allDs = cursor.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append(self.formatDictName(d[1], d[0]))
            return dicts
        except:
            return []

    def getAllDictsWithLang(self) -> List[Dict[str, str]]:
        """Get all dictionaries with their languages."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;"
        )
        try:
            dicts: List[Dict[str, str]] = []
            allDs = cursor.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append(
                        {"dict": self.formatDictName(d[1], d[0]), "lang": d[2]}
                    )
            return dicts
        except:
            return []

    def getDefaultGroups(self) -> Dict[str, Dict[str, Any]]:
        """Get default dictionary groups by language."""
        langs = self.getCurrentDbLangs()
        dictsByLang: Dict[str, Dict[str, Any]] = {}
        cursor = self._get_cursor()
        for lang in langs:
            cursor.execute(
                "SELECT dictname, lid FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid WHERE langname = ?;",
                (lang,),
            )
            allDs = cursor.fetchall()
            dicts: Dict[str, Any] = {}
            dicts["customFont"] = False
            dicts["font"] = False
            dicts["dictionaries"] = []
            if len(allDs) > 0:
                for d in allDs:
                    dicts["dictionaries"].append(
                        {"dict": self.formatDictName(d[1], d[0]), "lang": lang}
                    )
            if len(dicts["dictionaries"]) > 0:
                dictsByLang[lang] = dicts
        return dictsByLang

    def cleanDictName(self, name: str) -> str:
        """Clean language ID prefix from dictionary name."""
        return re.sub(r"l\d+name", "", name)

    def getDuplicateSetting(self, name: str) -> Optional[Tuple[int, List[str]]]:
        """Get duplicate setting for a dictionary."""
        if not self._ensure_connection():
            return None
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT duplicateHeader, termHeader  FROM dictnames WHERE dictname=? COLLATE NOCASE",
            (clean_name,),
        )
        try:
            result = cursor.fetchone()
            if result:
                duplicateHeader, termHeader = result
                return duplicateHeader, json.loads(termHeader)
            return None
        except:
            return None

    def getDefEx(self, sT: str) -> bool:
        """Check if search type is definition or example."""
        if sT in ["Definition", "Example"]:
            return True
        return False

    def applySearchType(self, terms: List[str], sT: str) -> List[str]:
        """Apply search type modifications to terms."""
        for idx, term in enumerate(terms):
            if sT in ["Forward", "Pronunciation"]:
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
        """Deconjugate terms using provided conjugation rules."""
        deconjugations: List[str] = []
        for term in terms:
            for c in conjugations:
                if term.endswith(c["inflected"]):
                    for x in c["dict"]:
                        deinflected = self.rreplace(term, c["inflected"], x, 1)
                        if "prefix" in c:
                            prefix = c["prefix"]
                            if deinflected.startswith(prefix):
                                deprefixedDeinflected = deinflected[len(prefix) :]
                                if deprefixedDeinflected not in deconjugations:
                                    deconjugations.append(deprefixedDeinflected)
                        if deinflected not in deconjugations:
                            deconjugations.append(deinflected)
        deconjugations = list(filter(lambda x: len(x) > 1, deconjugations))
        deconjugations = list(set(deconjugations))
        return terms + deconjugations

    def get_term_frequency_info(
        self, term: str, lang: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get frequency and level info for a specific term and language."""
        if not lang:
            return {"term": term, "starCount": "", "hskLevel": ""}

        providers = self._get_extra_data(lang)
        if not providers:
            return {"term": term, "starCount": "", "hskLevel": ""}

        # Create a dummy entry for _apply_frequency_info
        entry = {
            "term": term,
            "altterm": "",
            "pronunciation": "",
            "starCount": "",
            "hskLevel": "",
        }
        self._apply_frequency_info(entry, providers, config)
        return entry

    def rreplace(self, s: str, old: str, new: str, occurrence: int) -> str:
        """Replace from right side."""
        li = s.rsplit(old, occurrence)
        return new.join(li)

    def searchTerm(
        self, term, selectedGroup, conjugations, sT, deinflect, dictLimit, maxDefs
    ):
        alreadyConjTyped = {}
        results = {}
        group = selectedGroup["dictionaries"]
        totalDefs = 0
        defEx = self.getDefEx(sT)
        op = "LIKE"
        if defEx:
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

        # Get dictionary to table mapping for all dictionaries
        dict_mapping = self.getDictToTable()
        logger.debug(
            f"Search: Term='{term}', Group='{selectedGroup.get('name', 'unknown')}', Type='{sT}'"
        )

        # Pre-load frequency lists for all unique languages in the group
        langs = set()
        for dic in group:
            d_name = dic["dict"]
            if d_name in ["Images", "LLM", "Forvo"]:
                continue

            info = dict_mapping.get(d_name) or dict_mapping.get(
                self.cleanDictName(d_name)
            )
            if info:
                langs.add(info["lang"])
            elif "lang" in dic:
                langs.add(dic["lang"])

        extra_data = {lang: self._get_extra_data(lang) for lang in langs}
        config = get_addon_config()

        for dic in group:
            d_name = dic["dict"]
            if d_name == "Images":
                results["Images"] = True
                continue
            if d_name == "LLM":
                results["LLM"] = True
                continue
            if d_name == "Forvo":
                results["Forvo"] = True
                continue

            # Resolve table name and language
            # Try original name, then clean name, then normalized name (all case-insensitive)
            info = (
                dict_mapping.get(d_name)
                or dict_mapping.get(d_name.lower())
                or dict_mapping.get(self.cleanDictName(d_name))
                or dict_mapping.get(self.cleanDictName(d_name).lower())
                or dict_mapping.get(self.normalize_dict_name(d_name))
                or dict_mapping.get(self.normalize_dict_name(d_name).lower())
            )
            if info:
                table_name = info["dict"]
                lang = info["lang"]
            else:
                table_name = d_name
                lang = dic.get("lang", "")

            providers = extra_data.get(lang, [])

            if deinflect:
                if lang in alreadyConjTyped:
                    current_terms = alreadyConjTyped[lang]
                elif lang in conjugations:
                    # Start from a fresh copy of base_terms
                    current_terms = self.deconjugate(
                        list(base_terms), conjugations[lang]
                    )
                    current_terms = self.applySearchType(current_terms, sT)
                    alreadyConjTyped[lang] = current_terms
                else:
                    # Start from a fresh copy of base_terms
                    current_terms = self.applySearchType(list(base_terms), sT)
                    alreadyConjTyped[lang] = current_terms
            else:
                # Key by search type since that affects the terms
                cache_key = f"{lang}_{sT}"
                if cache_key in alreadyConjTyped:
                    current_terms = alreadyConjTyped[cache_key]
                else:
                    current_terms = self.applySearchType(list(base_terms), sT)
                    alreadyConjTyped[cache_key] = current_terms

            toQuery = self.getQueryCriteria(column, current_terms, op)
            termTuple = tuple(current_terms)
            allRs = self.executeSearch(table_name, toQuery, dictLimit, termTuple)

            if len(allRs) > 0:
                dictRes = []
                for r in allRs:
                    totalDefs += 1
                    entry = self.resultToDict(r)

                    self._apply_frequency_info(entry, providers, config)

                    dictRes.append(entry)
                    if totalDefs >= maxDefs:
                        results[d_name] = dictRes
                        return results
                results[d_name] = dictRes
            elif not defEx and not sT == "Pronunciation":
                columns = ["altterm", "pronunciation"]
                for col in columns:
                    toQuery = self.getQueryCriteria(col, current_terms, op)
                    termTuple = tuple(current_terms)
                    allRs = self.executeSearch(
                        table_name, toQuery, dictLimit, termTuple
                    )
                    if len(allRs) > 0:
                        dictRes = []
                        for r in allRs:
                            totalDefs += 1
                            entry = self.resultToDict(r)

                            self._apply_frequency_info(entry, providers, config)

                            dictRes.append(entry)
                            if totalDefs >= maxDefs:
                                results[d_name] = dictRes
                                return results
                        results[d_name] = dictRes
                        break
        return results

    def processDefinitionHTML(self, text):
        """Process HTML tags in dictionary definitions for proper display."""
        if not isinstance(text, str):
            text = str(text) if text is not None else ""

        # Strip leading/trailing whitespace first
        text = text.strip()

        # First convert any newlines to <br> tags
        text = text.replace("\n", "<br>")

        # Handle <br> tags that might already be in definitions
        # Convert any existing <br> or <br/> or <BR> tags to proper HTML line breaks
        text = re.sub(r"<br\s*/?>", "<br>", text, flags=re.IGNORECASE)

        # Handle other common HTML entities that might appear in definitions
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

        # Ensure proper line spacing for better readability
        # Replace multiple consecutive <br> tags with proper spacing
        text = re.sub(r"(<br>\s*){2,}", "<br><br>", text)

        # Strip leading and trailing <br> tags that might have been created or were already there
        text = re.sub(r"^(<br>\s*)+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(<br>\s*)+$", "", text, flags=re.IGNORECASE)

        # Remove leading [?] placeholder markers from definition text
        text = re.sub(r"^\[\?\]\s*", "", text)

        return text.strip()

    def resultToDict(self, r):
        # Create the output dictionary
        output = {
            "term": r[0],
            "altterm": r[1],
            "pronunciation": r[2],
            "pos": r[3],
            "definition": self.processDefinitionHTML(r[4]),
            "examples": r[5],
            "audio": r[6],
            "starCount": r[7],
            "hskLevel": "",
        }

        return output

    def executeSearch(
        self, dictName: str, toQuery: str, dictLimit: str, termTuple: Tuple[Any, ...]
    ) -> List[Tuple[Any, ...]]:
        """Execute database search with given parameters."""
        if not self._ensure_connection():
            return []
        try:
            cursor = self._get_cursor()
            # Quote table name to handle spaces and special characters
            query = (
                'SELECT term, altterm, pronunciation, pos, definition, examples, audio, starCount FROM "'
                + dictName
                + '" WHERE '
                + toQuery
                + " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT "
                + dictLimit
                + " ;"
            )
            cursor.execute(query, termTuple)
            out = cursor.fetchall()
            return out
        except sqlite3.Error as e:
            logger.error(f"Search error in dictionary '{dictName}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching dictionary '{dictName}': {e}")
            return []

    def getQueryCriteria(self, col, terms, op="LIKE"):

        toQuery = ""
        for idx, item in enumerate(terms):
            if idx == 0:
                toQuery += " " + col + " " + op + " ? "
            else:
                toQuery += " OR " + col + " " + op + " ? "
        return toQuery

    def getDefForMassExp(self, term, dN, limit, rN):
        duplicateHeader, termHeader = self.getDuplicateSetting(rN)
        results = []
        columns = ["term", "altterm", "pronunciation"]
        for col in columns:
            terms = [term]
            toQuery = " " + col + " = ? "
            termTuple = tuple(terms)
            allRs = self.executeSearch(dN, toQuery, limit, termTuple)
            if len(allRs) > 0:
                for r in allRs:
                    results.append(self.resultToDict(r))
                break
        return results, duplicateHeader, termHeader

    def cleanLT(self, text):
        return re.sub(r"<((?:[^b][^r])|(?:[b][^r]))", r"&lt;\1", str(text))

    def createDB(self, text: str) -> None:
        """Create a new dictionary table with indexes."""
        cursor = self._get_cursor()
        # Quote table name to handle spaces and special characters
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS "'
            + text
            + '" (term CHAR(40) NOT NULL, altterm CHAR(40), pronunciation CHAR(100), pos CHAR(40), definition TEXT, examples TEXT, audio TEXT, frequency MEDIUMINT, starCount TEXT);'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "it' + text + '" ON "' + text + '" (term);'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "itp'
            + text
            + '" ON "'
            + text
            + '" ( term, pronunciation );'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "ia' + text + '" ON "' + text + '" (altterm);'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "iap'
            + text
            + '" ON "'
            + text
            + '" ( altterm, pronunciation );'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS "ip'
            + text
            + '" ON "'
            + text
            + '" (pronunciation);'
        )

    def importToDict(
        self, dictName: str, dictionaryData: List[Tuple[Any, ...]]
    ) -> None:
        """Import dictionary data to specified dictionary table."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        # Quote table name to handle spaces and special characters
        cursor.executemany(
            'INSERT INTO "'
            + dictName
            + '" (term, altterm, pronunciation, pos, definition, examples, audio, frequency, starCount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
            dictionaryData,
        )

    def dropTables(self, text: str) -> None:
        """Drop all tables matching the given pattern."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;",
            (text,),
        )
        dicts = cursor.fetchall()
        for name in dicts:
            # Quote table name to handle spaces and special characters
            cursor.execute('DROP TABLE IF EXISTS "' + name[0] + '" ;')

    def setFieldsSetting(self, name: str, fields: str) -> None:
        """Set the fields setting for a dictionary."""
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        logger.debug(f"DB: Setting fields for {clean_name} to {fields}")
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET fields = ? WHERE dictname=? COLLATE NOCASE",
            (fields, clean_name),
        )
        self.commitChanges()

    def setAddType(self, name: str, addType: str) -> None:
        """Set add type for a dictionary."""
        if not self._ensure_connection():
            return
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET addtype = ? WHERE dictname=? COLLATE NOCASE",
            (addType, clean_name),
        )
        self.commitChanges()

    def getFieldsSetting(self, name: str) -> Optional[Dict[str, Any]]:
        """Get fields setting for a dictionary."""
        if not self._ensure_connection():
            return None
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT fields FROM dictnames WHERE dictname=? COLLATE NOCASE",
            (clean_name,),
        )
        try:
            result = cursor.fetchone()
            if result:
                logger.debug(f"DB: Retrieved fields for {clean_name}: {result[0]}")
                return json.loads(result[0])
            logger.debug(f"DB: No fields found for {clean_name}")
            return None
        except:
            return None

    def getAddTypeAndFields(
        self, dictName: str
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get add type and fields for a dictionary."""
        if not self._ensure_connection():
            return None
        clean_name = self.normalize_dict_name(self.cleanDictName(dictName))
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT fields, addtype FROM dictnames WHERE dictname=? COLLATE NOCASE",
            (clean_name,),
        )
        try:
            result = cursor.fetchone()
            if result:
                fields, addType = result
                return json.loads(fields), addType
            return None
        except:
            return None

    def getDupHeaders(self) -> Optional[Dict[str, int]]:
        """Get duplicate headers for all dictionaries."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, duplicateHeader FROM dictnames")
        try:
            dictHeaders = cursor.fetchall()
            results: Dict[str, int] = {}
            for r in dictHeaders:
                results[r[0]] = r[1]
            return results
        except:
            return None

    def setDupHeader(self, duplicateHeader: int, name: str) -> None:
        """Set duplicate header for a dictionary."""
        if not self._ensure_connection():
            return
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET duplicateHeader = ? WHERE dictname=? COLLATE NOCASE",
            (duplicateHeader, clean_name),
        )
        self.commitChanges()

    def getTermHeaders(self) -> Optional[Dict[str, List[str]]]:
        """Get term headers for all dictionaries."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, termHeader FROM dictnames")
        try:
            dictHeaders = cursor.fetchall()
            results: Dict[str, List[str]] = {}
            for r in dictHeaders:
                results[r[0]] = json.loads(r[1])
            return results
        except:
            return None

    def getAddType(self, name: str) -> Optional[str]:
        """Get add type for a dictionary."""
        if not self._ensure_connection():
            return None
        clean_name = self.normalize_dict_name(self.cleanDictName(name))
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT addtype FROM dictnames WHERE dictname=? COLLATE NOCASE",
            (clean_name,),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def getDictTermHeader(self, dictname: str) -> Optional[str]:
        """Get term header for a specific dictionary."""
        if not self._ensure_connection():
            return None
        clean_name = self.normalize_dict_name(self.cleanDictName(dictname))
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT termHeader FROM dictnames WHERE dictname=? COLLATE NOCASE",
            (clean_name,),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def setDictTermHeader(self, dictname: str, termheader: str) -> None:
        """Set term header for a dictionary."""
        if not self._ensure_connection():
            return
        clean_name = self.normalize_dict_name(self.cleanDictName(dictname))
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET termHeader = ? WHERE dictname=? COLLATE NOCASE",
            (termheader, clean_name),
        )
        self.commitChanges()

    def commitChanges(self) -> None:
        """Commit changes to the database."""
        conn = self._get_connection()
        conn.commit()
