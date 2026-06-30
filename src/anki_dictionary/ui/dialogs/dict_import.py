from __future__ import annotations

import json
import re
import zipfile
from typing import Any

import aqt
from aqt.qt import QMessageBox, QWidget

from ...utils.logger import get_logger

log = get_logger("dict_import")


def importDict(
    lang_name: str, file: str, dict_name: str, parent: QWidget | None = None
) -> None:
    db = aqt.mw.miDictDB  # ty:ignore[unresolved-attribute]

    if parent is None:
        parent = aqt.mw.app.activeWindow() or aqt.mw

    try:
        zfile = zipfile.ZipFile(file)
    except zipfile.BadZipFile as e:
        raise ValueError("Dictionary archive is invalid.") from e

    has_term_bank = any(fn.startswith("term_bank_") for fn in zfile.namelist())
    has_index = any(fn == "index.json" for fn in zfile.namelist())

    is_pitch_dict = False
    if has_index:
        for fn in zfile.namelist():
            if fn.endswith(".json") and (
                "pitch" in fn.lower() or "accent" in fn.lower()
            ):
                try:
                    content = zfile.read(fn)
                    try:
                        decoded = content.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            decoded = content.decode("utf-16")
                        except UnicodeDecodeError:
                            decoded = content.decode("latin-1")

                    if "pitches" in decoded:
                        is_pitch_dict = True
                        break
                except Exception:
                    continue

    is_yomichan = has_term_bank or (has_index and is_pitch_dict)

    log.info("Importing dict")
    term_header = json.dumps(["term", "altterm", "pronunciation"])

    success, message, final_name = db.addDict(dict_name, lang_name, term_header)

    if not success and message == "duplicate":
        dlg = QMessageBox(
            QMessageBox.Icon.Question,
            "Duplicate Dictionary",
            f'A dictionary with the name "{final_name}" already exists.\n\nDo you want to overwrite it?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            parent,
        )
        if dlg.exec() == QMessageBox.StandardButton.Yes:
            db.deleteDict(final_name)
            success, message, final_name = db.addDict(dict_name, lang_name, term_header)

    if not success:
        raise ValueError(
            f"Creating dictionary failed.\nOriginal name: {dict_name}\nError: {message}"
        )

    dict_files = []
    for fn in zfile.namelist():
        if not fn.endswith(".json") or fn == "index.json":
            continue
        if is_yomichan:
            if not (
                fn.startswith("term_bank_")
                or "pitch" in fn.lower()
                or "accent" in fn.lower()
            ):
                continue
        dict_files.append(fn)
    dict_files = natural_sort(dict_files)

    loadDict(zfile, dict_files, lang_name, final_name, not is_yomichan)
    return final_name


def natural_sort(l: list[str]) -> list[str]:
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


def loadDict(
    zfile: zipfile.ZipFile,
    filenames: list[str],
    lang: str,
    dictName: str,
    miDict: bool = False,
) -> None:
    tableName = "l" + str(aqt.mw.miDictDB.getLangId(lang)) + "name" + dictName  # ty:ignore[unresolved-attribute]
    jsonDict = []
    for filename in filenames:
        with zfile.open(filename, "r") as jsonDictFile:
            content = jsonDictFile.read()
            try:
                decoded = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    decoded = content.decode("utf-16")
                except UnicodeDecodeError:
                    decoded = content.decode("latin-1")
            jsonDict += json.loads(decoded)
    for count, entry in enumerate(jsonDict):
        if (
            isinstance(entry, list)
            and len(entry) >= 3
            and isinstance(entry[2], dict)
            and "pitches" in entry[2]
        ):
            handlePitchDictEntry(jsonDict, count, entry)
        elif miDict:
            handleMiDictEntry(jsonDict, count, entry)
        else:
            handleYomiDictEntry(jsonDict, count, entry)
    aqt.mw.miDictDB.importToDict(tableName, jsonDict)  # ty:ignore[unresolved-attribute]
    aqt.mw.miDictDB.commitChanges()  # ty:ignore[unresolved-attribute]


def getAdjustedTerm(term: str) -> str:
    term = term.replace("\n", "")
    if len(term) > 1:
        term = term.replace("=", "")
    return term


def getAdjustedPronunciation(pronunciation: str) -> str:
    return pronunciation.replace("\n", "")


def getAdjustedDefinition(definition: str) -> str:
    definition = definition.replace("\n", "<br>")
    definition = definition.replace("◟", "<br>")

    definition = re.sub(r"<br\s*/?>", "<br>", definition, flags=re.IGNORECASE)

    definition = definition.replace("<", "&lt;").replace(">", "&gt;")

    definition = definition.replace("&lt;br&gt;", "<br>")

    definition = re.sub(r"<br>$", "", definition)
    return definition


def handlePitchDictEntry(jsonDict: list, count: int, entry: Any) -> None:
    term = ""
    altterm = ""
    reading = ""
    pos = ""
    definition = ""
    examples = ""
    audio = ""
    frequency = ""
    starCount = ""

    term = entry[0]
    reading = entry[2].get("reading", entry[0])

    jsonDict[count] = (
        term,
        altterm,
        reading,
        pos,
        definition,
        examples,
        audio,
        frequency,
        starCount,
    )


def handleMiDictEntry(jsonDict: list, count: int, entry: Any) -> None:
    if isinstance(entry, list):
        term = entry[0] if len(entry) > 0 else ""
        altterm = entry[1] if len(entry) > 1 else ""
        details = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

        pronunciation = details.get("pronunciation", altterm)
        pos = details.get("pos", "")
        definition = details.get("definition", "")
        frequency = ""
        starCount = ""
    elif isinstance(entry, dict):
        term = entry.get("term", "")
        altterm = entry.get("altterm", "")
        pronunciation = entry.get("pronunciation", "")
        pos = entry.get("pos", "")
        definition = entry.get("definition", "")
        frequency = ""
        starCount = ""
    else:
        return

    if pronunciation == "":
        pronunciation = term

    term = getAdjustedTerm(term)
    altTerm = getAdjustedTerm(altterm)
    pronunciation = getAdjustedPronunciation(pronunciation)
    definition = getAdjustedDefinition(definition)

    jsonDict[count] = (
        term,
        altTerm,
        pronunciation,
        pos,
        definition,
        "",
        "",
        frequency,
        starCount,
    )


def handleYomiDictEntry(jsonDict: list, count: int, entry: Any) -> None:
    def extract_definition(items: Any) -> str:
        def recursive_extract(item):
            if isinstance(item, str):
                return item.strip()
            elif isinstance(item, dict):
                if "text" in item:
                    return item["text"].strip()

                content = item.get("content", "")
                if "name" in item.get("data", {}) and item["data"]["name"] == "語釈":
                    return recursive_extract(content)
                return recursive_extract(content)
            elif isinstance(item, list):
                return " ".join(
                    recursive_extract(x) for x in item if recursive_extract(x)
                )
            return ""

        if isinstance(items, str):
            return getAdjustedDefinition(items)

        definitions = []
        for item in items:
            text = recursive_extract(item)
            if text:
                text = text.replace("\n", "<br/>")
                definitions.append(text)
        return "<br/>".join(definitions)

    def find_header_section(items: Any) -> list:
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    if item.get("type") == "structured-content":
                        return find_header_section(item.get("content", []))
                    if item.get("data", {}).get("name") == "見出部":
                        return item.get("content", [])
        return []

    def extract_pitch(content: Any) -> list[int]:
        accents: list[int] = []

        def recursive_search(item: Any) -> None:
            if isinstance(item, dict) and "data" in item:
                name = item.get("data", {}).get("name", "")

            if not isinstance(item, (dict, list)):
                return

            if isinstance(item, dict):
                name = item.get("data", {}).get("name", "")
                if name.startswith("accent"):
                    try:
                        accent_num = int(name.replace("accent", ""))
                        accents.append(accent_num)
                    except ValueError:
                        pass

                if "content" in item:
                    recursive_search(item["content"])

            elif isinstance(item, list):
                for sub_item in item:
                    recursive_search(sub_item)

        accents.clear()
        recursive_search(content)
        accents.sort()
        return accents

    term = entry[0]
    reading = entry[1] if entry[1] else term
    pos = entry[2] if len(entry) > 2 else ""
    frequency = ""
    starCount = ""
    definition = ""
    pitch_accents = []

    if len(entry) > 5:
        definition = extract_definition(entry[5])

        if isinstance(entry[5], list):
            header_section = find_header_section(entry[5])
            if header_section:
                pitch_accents = extract_pitch(header_section)

    jsonDict[count] = (
        term,
        (" ".join(str(p) for p in pitch_accents) if pitch_accents else ""),
        reading,
        pos,
        definition,
        "",
        "",
        frequency,
        starCount,
    )
