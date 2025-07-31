# -*- coding: utf-8 -*-

import sqlite3
import os.path
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from aqt.utils import showInfo
from aqt import mw
from ..utils.common import miInfo

# Get the root addon path (go up from src/anki_dictionary/core to root)
addon_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


class DictDB:
    """Database interface for dictionary management."""

    def __init__(self) -> None:
        """Initialize the database connection."""
        self.conn: Optional[sqlite3.Connection] = None
        self.c: Optional[sqlite3.Cursor] = None
        self.oldConnection: Optional[sqlite3.Cursor] = None

        # Get the root addon directory by going up from this file's location
        current_file = os.path.abspath(__file__)
        # Go up: core -> anki_dictionary -> src -> addon_root
        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        )
        addon_name = os.path.basename(addon_root)

        # First try direct path from addon root
        db_file = os.path.join(addon_root, "user_files", "db", "dictionaries.sqlite")

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
        self.dropTables(d)
        d_clean = self.cleanDictName(d)
        cursor = self._get_cursor()
        cursor.execute("DELETE FROM dictnames WHERE dictname = ?;", (d_clean,))
        self.commitChanges()
        cursor.execute("VACUUM;")

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
            if d in currentDicts or d in ["Google Images", "Forvo"]:
                if d == "Google Images":
                    foundDicts.append({"dict": "Google Images", "lang": ""})
                elif d == "Forvo":
                    foundDicts.append({"dict": "Forvo", "lang": ""})
                else:
                    foundDicts.append(currentDicts[d])
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
                    dicts[d[0]] = {
                        "dict": self.formatDictName(d[1], d[0]),
                        "lang": d[2],
                    }
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
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT duplicateHeader, termHeader  FROM dictnames WHERE dictname=?",
            (name,),
        )
        try:
            result = cursor.fetchone()
            if result:
                (duplicateHeader, termHeader) = result
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
        terms = [term]
        terms.append(term.lower())
        terms.append(term.capitalize())
        terms = list(set(terms))
        for dic in group:
            if dic["dict"] == "Google Images":
                results["Google Images"] = True
                continue
            elif dic["dict"] == "Forvo":
                results["Forvo"] = True
                continue

            if deinflect:
                if dic["lang"] in alreadyConjTyped:
                    terms = alreadyConjTyped[dic["lang"]]
                elif dic["lang"] in conjugations:
                    terms = self.deconjugate(terms, conjugations[dic["lang"]])
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[dic["lang"]] = terms
                else:
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[dic["lang"]] = terms
            else:
                if term in alreadyConjTyped:
                    terms = alreadyConjTyped[term]
                else:
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[term] = terms

            toQuery = self.getQueryCriteria(column, terms, op)
            termTuple = tuple(terms)
            allRs = self.executeSearch(dic["dict"], toQuery, dictLimit, termTuple)
            if len(allRs) > 0:
                dictRes = []
                for r in allRs:
                    totalDefs += 1
                    dictRes.append(self.resultToDict(r))
                    if totalDefs >= maxDefs:
                        results[self.cleanDictName(dic["dict"])] = dictRes
                        return results
                results[self.cleanDictName(dic["dict"])] = dictRes
            elif not defEx and not sT == "Pronunciation":
                columns = ["altterm", "pronunciation"]
                for col in columns:
                    toQuery = self.getQueryCriteria(col, terms, op)
                    termTuple = tuple(terms)
                    allRs = self.executeSearch(
                        dic["dict"], toQuery, dictLimit, termTuple
                    )
                    if len(allRs) > 0:
                        dictRes = []
                        for r in allRs:
                            totalDefs += 1
                            dictRes.append(self.resultToDict(r))
                            if totalDefs >= maxDefs:
                                results[self.cleanDictName(dic["dict"])] = dictRes
                                return results
                        results[self.cleanDictName(dic["dict"])] = dictRes
                        break
        return results

    def resultToDict(self, r):
        # Create the output dictionary
        output = {
            "term": r[0],
            "altterm": r[1],
            "pronunciation": r[2],
            "pos": r[3],
            "definition": r[4].replace("\n", "<br>"),
            "examples": r[5],
            "audio": r[6],
            "starCount": r[7],
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
            cursor.execute(
                "SELECT term, altterm, pronunciation, pos, definition, examples, audio, starCount FROM "
                + dictName
                + " WHERE "
                + toQuery
                + " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT "
                + dictLimit
                + " ;",
                termTuple,
            )
            out = cursor.fetchall()
            # print("executeSearch", out)
            return out
        except:
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
        cursor.execute(
            "CREATE TABLE  IF NOT EXISTS  "
            + text
            + "(term CHAR(40) NOT NULL, altterm CHAR(40), pronunciation CHAR(100), pos CHAR(40), definition TEXT, examples TEXT, audio TEXT, frequency MEDIUMINT, starCount TEXT);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS it" + text + " ON " + text + " (term);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS itp"
            + text
            + " ON "
            + text
            + " ( term, pronunciation );"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ia" + text + " ON " + text + " (altterm);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS iap"
            + text
            + " ON "
            + text
            + " ( altterm, pronunciation );"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ia" + text + " ON " + text + " (pronunciation);"
        )

    def importToDict(
        self, dictName: str, dictionaryData: List[Tuple[Any, ...]]
    ) -> None:
        """Import dictionary data to specified dictionary table."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.executemany(
            "INSERT INTO "
            + dictName
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
            cursor.execute("DROP TABLE " + name[0] + " ;")

    def setFieldsSetting(self, name: str, fields: str) -> None:
        """Set the fields setting for a dictionary."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET fields = ? WHERE dictname=?", (fields, name)
        )
        self.commitChanges()

    def setAddType(self, name: str, addType: str) -> None:
        """Set add type for a dictionary."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET addtype = ? WHERE dictname=?", (addType, name)
        )
        self.commitChanges()

    def getFieldsSetting(self, name: str) -> Optional[Dict[str, Any]]:
        """Get fields setting for a dictionary."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT fields FROM dictnames WHERE dictname=?", (name,))
        try:
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
        except:
            return None

    def getAddTypeAndFields(
        self, dictName: str
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """Get add type and fields for a dictionary."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT fields, addtype FROM dictnames WHERE dictname=?", (dictName,)
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
            if len(dictHeaders) > 0:
                for r in dictHeaders:
                    results[r[0]] = r[1]
                return results
        except:
            return None

    def setDupHeader(self, duplicateHeader: int, name: str) -> None:
        """Set duplicate header for a dictionary."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET duplicateHeader = ? WHERE dictname=?",
            (duplicateHeader, name),
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
            if len(dictHeaders) > 0:
                for r in dictHeaders:
                    results[r[0]] = json.loads(r[1])
                return results
        except:
            return None

    def getAddType(self, name: str) -> Optional[str]:
        """Get add type for a dictionary."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT addtype FROM dictnames WHERE dictname=?", (name,))
        try:
            result = cursor.fetchone()
            return result[0] if result else None
        except:
            return None

    def getDictTermHeader(self, dictname: str) -> Optional[str]:
        """Get term header for a specific dictionary."""
        if not self._ensure_connection():
            return None
        cursor = self._get_cursor()
        cursor.execute("SELECT termHeader FROM dictnames WHERE dictname=?", (dictname,))
        result = cursor.fetchone()
        return result[0] if result else None

    def setDictTermHeader(self, dictname: str, termheader: str) -> None:
        """Set term header for a dictionary."""
        if not self._ensure_connection():
            return
        cursor = self._get_cursor()
        cursor.execute(
            "UPDATE dictnames SET termHeader = ? WHERE dictname=?",
            (termheader, dictname),
        )
        self.commitChanges()

    def commitChanges(self) -> None:
        """Commit changes to the database."""
        conn = self._get_connection()
        conn.commit()
