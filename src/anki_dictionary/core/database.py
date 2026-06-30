import json
import os
import re
import sqlite3
from typing import Any

from aqt import mw

from ..utils.common import miInfo
from ..utils.config import get_addon_config
from ..utils.logger import get_logger
from ..utils.paths import (
    get_addon_name,
    get_addon_root,
    get_db_dir,
)
from .frequency import FrequencyEngine
from .search.query import SearchQueryBuilder
from .word_list_registry import WordListRegistry

# Initialize logger
logger = get_logger("database")


class DictDB:
    """Database interface for dictionary management."""

    def __init__(self) -> None:
        """Initialize the database connection."""
        self.conn: sqlite3.Connection | None = None
        self.c: sqlite3.Cursor | None = None
        self.oldConnection: sqlite3.Cursor | None = None
        self._extra_data_cache: dict[str, list[Any]] = {}
        self._registry: WordListRegistry | None = None
        self._frequency_engine: FrequencyEngine | None = None
        self.search_query_builder = SearchQueryBuilder(self)

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

        self._registry = WordListRegistry(get_db_dir())
        self._frequency_engine = FrequencyEngine(self._registry)

    @staticmethod
    def _quote_identifier(name: str) -> str:
        """Safely quote a SQLite identifier (table/index name) to prevent injection."""
        return '"' + name.replace('"', '""') + '"'

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

    def _get_extra_data(self, lang: str) -> list[Any]:
        """Load all frequency and level data for a language via WordListRegistry."""
        if lang in self._extra_data_cache:
            return self._extra_data_cache[lang]

        if self._registry is None:
            self._extra_data_cache[lang] = []
            return []

        providers = self._registry.get_providers(lang)
        self._extra_data_cache[lang] = providers
        return providers

    def getStarCount(self, freq: int) -> str:
        config = get_addon_config()
        star_char = config.get("star_char", "\u2605")
        thresholds = config.get("star_thresholds", [1501, 5001, 15001, 30001, 60001])
        from .frequency import get_star_count

        return get_star_count(freq, star_char, thresholds)

    def _apply_frequency_info(
        self,
        entry: dict[str, Any],
        providers: list[Any],
        config: dict[str, Any],
    ) -> None:
        if self._frequency_engine is not None:
            self._frequency_engine.apply(entry, providers, config)

    def kana_converter(self, to_translate: str, hiraganer: bool = False) -> str:
        from .frequency import kana_converter as _kc

        return _kc(to_translate, hiraganer)

    def adjustReading(self, reading: str) -> str:
        from .frequency import adjust_reading

        return adjust_reading(reading)

    def getLangId(self, lang: str) -> int | None:
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

    def getLangIdFromDict(self, dictname: str) -> int | None:
        """Get language ID for a given dictionary name."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT lid FROM dictnames WHERE dictname = ? COLLATE NOCASE;", (dictname,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def getDictsByLanguage(self, lang: str) -> list[str]:
        """Get all dictionary names for a given language."""
        if not self._ensure_connection():
            return []
        lid = self.getLangId(lang)
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname FROM dictnames WHERE lid = ?;", (lid,))
        try:
            langs: list[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except Exception:
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
    ) -> tuple[bool, str, str | None]:
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

    def formatDictName(self, lid: int | None, name: str) -> str:
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

    def addLanguages(self, list: list[str]) -> None:
        """Add multiple languages to the database."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        for l in list:
            cursor.execute("INSERT INTO langnames (langname) VALUES (?);", (l,))
        self.commitChanges()

    def getCurrentDbLangs(self) -> list[str]:
        """Get all languages currently in the database."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT langname FROM langnames;")
        try:
            langs: list[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except Exception:
            return []

    def getUserGroups(self, dicts: list[str]) -> list[dict[str, str]]:
        """Get user dictionary groups based on provided dictionary names."""
        currentDicts = self.getDictToTable()
        foundDicts: list[dict[str, str]] = []
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

    def getDictToTable(self) -> dict[str, dict[str, str]]:
        """Get dictionary to table mapping."""
        if not self._ensure_connection():
            return {}
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;"
        )
        try:
            dicts: dict[str, dict[str, str]] = {}
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

    def fetchDefs(self) -> list[str]:
        """Fetch definitions from dictname table."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT definition FROM dictname LIMIT 10;")
        try:
            langs: list[str] = []
            allLs = cursor.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except Exception:
            return []

    def getAllDicts(self) -> list[str]:
        """Get all dictionary names formatted with language prefix."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, lid FROM dictnames;")
        try:
            dicts: list[str] = []
            allDs = cursor.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append(self.formatDictName(d[1], d[0]))
            return dicts
        except Exception:
            return []

    def getAllDictsWithLang(self) -> list[dict[str, str]]:
        """Get all dictionaries with their languages."""
        if not self._ensure_connection():
            return []
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;"
        )
        try:
            dicts: list[dict[str, str]] = []
            allDs = cursor.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append(
                        {"dict": self.formatDictName(d[1], d[0]), "lang": d[2]}
                    )
            return dicts
        except Exception:
            return []

    def getDefaultGroups(self) -> dict[str, dict[str, Any]]:
        """Get default dictionary groups by language."""
        langs = self.getCurrentDbLangs()
        dictsByLang: dict[str, dict[str, Any]] = {}
        cursor = self._get_cursor()
        for lang in langs:
            cursor.execute(
                "SELECT dictname, lid FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid WHERE langname = ?;",
                (lang,),
            )
            allDs = cursor.fetchall()
            dicts: dict[str, Any] = {}
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

    def getDuplicateSetting(self, name: str) -> tuple[int, list[str]] | None:
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
        except Exception:
            return None

    def get_term_frequency_info(
        self, term: str, lang: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        return self.search_query_builder.get_term_frequency_info(term, lang, config)

    def searchTerm(
        self, term, selectedGroup, conjugations, sT, deinflect, dictLimit, maxDefs
    ):
        return self.search_query_builder.search(
            term, selectedGroup, conjugations, sT, deinflect, int(dictLimit), maxDefs
        )

    def createDB(self, text: str) -> None:
        """Create a new dictionary table with indexes."""
        cursor = self._get_cursor()
        safe_table = self._quote_identifier(text)
        safe_idx_it = self._quote_identifier("it" + text)
        safe_idx_itp = self._quote_identifier("itp" + text)
        safe_idx_ia = self._quote_identifier("ia" + text)
        safe_idx_iap = self._quote_identifier("iap" + text)
        safe_idx_ip = self._quote_identifier("ip" + text)
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS "
            + safe_table
            + " (term CHAR(40) NOT NULL, altterm CHAR(40), pronunciation CHAR(100), pos CHAR(40), definition TEXT, examples TEXT, audio TEXT, frequency MEDIUMINT, starCount TEXT);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            + safe_idx_it
            + " ON "
            + safe_table
            + " (term);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            + safe_idx_itp
            + " ON "
            + safe_table
            + " ( term, pronunciation );"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            + safe_idx_ia
            + " ON "
            + safe_table
            + " (altterm);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            + safe_idx_iap
            + " ON "
            + safe_table
            + " ( altterm, pronunciation );"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            + safe_idx_ip
            + " ON "
            + safe_table
            + " (pronunciation);"
        )

    def importToDict(
        self, dictName: str, dictionaryData: list[tuple[Any, ...]]
    ) -> None:
        """Import dictionary data to specified dictionary table."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        safe_table = self._quote_identifier(dictName)
        cursor.executemany(
            "INSERT INTO "
            + safe_table
            + " (term, altterm, pronunciation, pos, definition, examples, audio, frequency, starCount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
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
            safe_table = self._quote_identifier(name[0])
            cursor.execute("DROP TABLE IF EXISTS " + safe_table + " ;")

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

    def getFieldsSetting(self, name: str) -> dict[str, Any] | None:
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
        except Exception:
            return None

    def getAddTypeAndFields(self, dictName: str) -> tuple[dict[str, Any], str] | None:
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
        except Exception:
            return None

    def getDupHeaders(self) -> dict[str, int] | None:
        """Get duplicate headers for all dictionaries."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, duplicateHeader FROM dictnames")
        try:
            dictHeaders = cursor.fetchall()
            results: dict[str, int] = {}
            for r in dictHeaders:
                results[r[0]] = r[1]
            return results
        except Exception:
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

    def getTermHeaders(self) -> dict[str, list[str]] | None:
        """Get term headers for all dictionaries."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT dictname, termHeader FROM dictnames")
        try:
            dictHeaders = cursor.fetchall()
            results: dict[str, list[str]] = {}
            for r in dictHeaders:
                results[r[0]] = json.loads(r[1])
            return results
        except Exception:
            return None

    def getAddType(self, name: str) -> str | None:
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

    def getDictTermHeader(self, dictname: str) -> str | None:
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
