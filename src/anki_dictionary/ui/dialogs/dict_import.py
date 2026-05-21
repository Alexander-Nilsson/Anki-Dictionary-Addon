import aqt
import json
import zipfile
import re
import os
from aqt.qt import QMessageBox

from ...utils.paths import get_db_dir


def importDict(lang_name, file, dict_name, parent=None):
    db = aqt.mw.miDictDB

    if parent is None:
        parent = aqt.mw.app.activeWindow() or aqt.mw

    try:
        zfile = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        raise ValueError("Dictionary archive is invalid.")

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

    print("Importing dict")
    frequency_dict = getFrequencyList(lang_name)
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
            f"Creating dictionary failed.\n"
            f"Original name: {dict_name}\n"
            f"Error: {message}"
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

    loadDict(zfile, dict_files, lang_name, final_name, frequency_dict, not is_yomichan)
    return final_name


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


def loadDict(zfile, filenames, lang, dictName, frequencyDict, miDict=False):
    tableName = "l" + str(aqt.mw.miDictDB.getLangId(lang)) + "name" + dictName
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
    if frequencyDict:
        print("FreqDICT!")
        if miDict:
            jsonDict = organizeDictionaryByFrequency(
                jsonDict, frequencyDict, dictName, lang, True
            )
        else:
            jsonDict = organizeDictionaryByFrequency(
                jsonDict, frequencyDict, dictName, lang
            )
    for count, entry in enumerate(jsonDict):
        if (
            isinstance(entry, list)
            and len(entry) >= 3
            and isinstance(entry[2], dict)
            and "pitches" in entry[2]
        ):
            handlePitchDictEntry(jsonDict, count, entry, frequencyDict is not None)
        elif miDict:
            handleMiDictEntry(jsonDict, count, entry, frequencyDict is not None)
        else:
            handleYomiDictEntry(jsonDict, count, entry, frequencyDict is not None)
    aqt.mw.miDictDB.importToDict(tableName, jsonDict)
    aqt.mw.miDictDB.commitChanges()


def getAdjustedTerm(term):
    term = term.replace("\n", "")
    if len(term) > 1:
        term = term.replace("=", "")
    return term


def getAdjustedPronunciation(pronunciation):
    return pronunciation.replace("\n", "")


def getAdjustedDefinition(definition):
    definition = definition.replace("\n", "<br>")
    definition = definition.replace("◟", "<br>")

    definition = re.sub(r"<br\s*/?>", "<br>", definition, flags=re.IGNORECASE)

    definition = definition.replace("<", "&lt;").replace(">", "&gt;")

    definition = definition.replace("&lt;br&gt;", "<br>")

    definition = re.sub(r"<br>$", "", definition)
    return definition


def handlePitchDictEntry(jsonDict, count, entry, freq=False):
    term = ""
    altterm = ""
    reading = ""
    pos = ""
    definition = ""
    examples = ""
    audio = ""
    frequency = entry[8] if freq and len(entry) > 8 else ""
    starCount = entry[9] if freq and len(entry) > 9 else ""
    pitch_accent = ""

    term = entry[0]
    reading = entry[2].get("reading", entry[0])
    pitch_accent = (
        entry[2]["pitches"][0].get("position") if entry[2]["pitches"] else None
    )

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


def handleMiDictEntry(jsonDict, count, entry, freq=False):
    if isinstance(entry, list):
        term = entry[0] if len(entry) > 0 else ""
        altterm = entry[1] if len(entry) > 1 else ""
        details = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

        pronunciation = details.get("pronunciation", altterm)
        pos = details.get("pos", "")
        definition = details.get("definition", "")
        frequency = details.get("frequency", "") if freq else ""
        starCount = details.get("starCount", "") if freq else ""
    elif isinstance(entry, dict):
        term = entry.get("term", "")
        altterm = entry.get("altterm", "")
        pronunciation = entry.get("pronunciation", "")
        pos = entry.get("pos", "")
        definition = entry.get("definition", "")
        frequency = entry.get("frequency", "") if freq else ""
        starCount = entry.get("starCount", "") if freq else ""
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


def handleYomiDictEntry(jsonDict, count, entry, freq=False):
    def extract_definition(items):
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

    def find_header_section(items):
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    if item.get("type") == "structured-content":
                        return find_header_section(item.get("content", []))
                    if item.get("data", {}).get("name") == "見出部":
                        return item.get("content", [])
        return []

    def extract_pitch(content):
        accents = []

        def recursive_search(item):
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
    frequency = entry[8] if freq and len(entry) > 8 else ""
    starCount = entry[9] if freq and len(entry) > 9 else ""
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


def kaner(to_translate, hiraganer=False):
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
        katakana = [ord(char) for char in katakana]
        translate_table = dict(zip(katakana, hiragana))
        return to_translate.translate(translate_table)
    else:
        hiragana = [ord(char) for char in hiragana]
        translate_table = dict(zip(hiragana, katakana))
        return to_translate.translate(translate_table)


def adjustReading(reading):
    return kaner(reading)


def organizeDictionaryByFrequency(
    jsonDict, frequencyDict, dictName, lang, miDict=False
):
    readingHyouki = frequencyDict.get("readingDictionaryType", False)

    for idx, entry in enumerate(jsonDict):
        if isinstance(entry, list):
            term = entry[0] if len(entry) > 0 else ""
            reading = entry[1] if len(entry) > 1 and isinstance(entry[1], str) else ""
            details = (
                entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else None
            )

            if readingHyouki:
                if details:
                    reading = details.get("reading", "") or reading or term
                adjusted = adjustReading(reading)
            else:
                adjusted = None

            frequency = 999999
            starCount = ""

            if miDict and details is not None:
                if readingHyouki and term in frequencyDict:
                    if adjusted in frequencyDict[term]:
                        frequency = frequencyDict[term][adjusted]
                elif not readingHyouki and term in frequencyDict:
                    frequency = frequencyDict[term]
                details["frequency"] = frequency
                details["starCount"] = getStarCount(frequency)
            else:
                if readingHyouki and term in frequencyDict:
                    if adjusted in frequencyDict[term]:
                        frequency = frequencyDict[term][adjusted]
                elif not readingHyouki and term in frequencyDict:
                    frequency = frequencyDict[term]

                while len(entry) < 10:
                    entry.append("")
                entry[8] = frequency
                entry[9] = getStarCount(frequency)

        else:
            continue

    if miDict:

        def get_frequency(item):
            if isinstance(item, tuple) and len(item) > 7:
                return item[7] if item[7] != "" else 999999
            elif isinstance(item, list) and len(item) > 2 and isinstance(item[2], dict):
                return item[2].get("frequency", 999999)
            else:
                return 999999

        return sorted(jsonDict, key=get_frequency)
    else:
        return sorted(jsonDict, key=lambda i: i[8] if len(i) > 8 else 999999)


def getStarCount(freq):
    if freq < 1501:
        return "★★★★★"
    elif freq < 5001:
        return "★★★★"
    elif freq < 15001:
        return "★★★"
    elif freq < 30001:
        return "★★"
    elif freq < 60001:
        return "★"
    else:
        return ""


def getFrequencyList(lang):
    filePath = os.path.join(get_db_dir(), "frequency", "%s.json" % lang)
    frequencyDict = {}
    if os.path.exists(filePath):
        frequencyList = json.load(open(filePath, "r", encoding="utf-8-sig"))
        if isinstance(frequencyList[0], str):
            yomi = False
            frequencyDict["readingDictionaryType"] = False
        elif (
            isinstance(frequencyList[0], list)
            and len(frequencyList[0]) == 2
            and isinstance(frequencyList[0][0], str)
            and isinstance(frequencyList[0][1], str)
        ):
            yomi = True
            frequencyDict["readingDictionaryType"] = True
        else:
            return False
        for idx, f in enumerate(frequencyList):
            if yomi:
                term = f[0].strip()
                reading = f[1].strip()
                if term in frequencyDict:
                    frequencyDict[term][reading] = idx
                else:
                    frequencyDict[term] = {}
                    frequencyDict[term][reading] = idx
            else:
                term = f.strip()
                if term not in frequencyDict:
                    frequencyDict[term] = idx
        return frequencyDict
    else:
        return False
