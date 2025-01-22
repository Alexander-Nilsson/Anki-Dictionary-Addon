import aqt
import json
import zipfile
import re
import operator
import shutil
import logging
from aqt.qt import *
from aqt import mw 
from .dictionaryWebInstallWizard import DictionaryWebInstallWizard
from .freqConjWebWindow import FreqConjWebWindow
logger = logging.getLogger(__name__)

class DictionaryManagerWidget(QWidget):
    
    def __init__(self, parent=None):
        super(DictionaryManagerWidget, self).__init__(parent)
        lyt = QVBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        lyt.addWidget(splitter)


        left_side = QWidget()
        splitter.addWidget(left_side)
        left_lyt = QVBoxLayout()
        left_side.setLayout(left_lyt)

        self.dict_tree = QTreeWidget()
        self.dict_tree.setHeaderHidden(True)
        self.dict_tree.currentItemChanged.connect(self.on_current_item_change)
        left_lyt.addWidget(self.dict_tree)

        add_lang_btn = QPushButton('Add a Language')
        add_lang_btn.clicked.connect(self.add_lang)
        left_lyt.addWidget(add_lang_btn)

        web_installer_btn = QPushButton('Install Languages in Wizard')
        web_installer_btn.clicked.connect(self.web_installer)
        left_lyt.addWidget(web_installer_btn)


        right_side = QWidget()
        splitter.addWidget(right_side)
        right_lyt = QVBoxLayout()
        right_side.setLayout(right_lyt)


        self.lang_grp = QGroupBox('Language Options')
        right_lyt.addWidget(self.lang_grp)

        lang_lyt = QVBoxLayout()
        self.lang_grp.setLayout(lang_lyt)

        lang_lyt1 = QHBoxLayout()
        lang_lyt2 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt2)
        lang_lyt3 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt3)
        lang_lyt4 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt4)
        lang_lyt.addLayout(lang_lyt1)

        remove_lang_btn = QPushButton('Remove Language')
        remove_lang_btn.clicked.connect(self.remove_lang)
        lang_lyt1.addWidget(remove_lang_btn)

        web_installer_lang_btn = QPushButton('Install Dictionary in Wizard')
        web_installer_lang_btn.clicked.connect(self.web_installer_lang)
        lang_lyt2.addWidget(web_installer_lang_btn)

        import_dict_btn = QPushButton('Install Dictionary From File')
        import_dict_btn.clicked.connect(self.import_dict)
        lang_lyt2.addWidget(import_dict_btn)

        import_dicts_btn = QPushButton('Install Dictionaries From File')
        import_dicts_btn.clicked.connect(self.import_dicts)
        lang_lyt2.addWidget(import_dicts_btn)

        web_freq_data_btn = QPushButton('Install Frequency Data in Wizard')
        web_freq_data_btn.clicked.connect(self.web_freq_data)
        lang_lyt3.addWidget(web_freq_data_btn)

        set_freq_data_btn = QPushButton('Install Frequency Data From File')
        set_freq_data_btn.clicked.connect(self.set_freq_data)
        lang_lyt3.addWidget(set_freq_data_btn)

        web_conj_data_btn = QPushButton('Install Conjugation Data in Wizard')
        web_conj_data_btn.clicked.connect(self.web_conj_data)
        lang_lyt4.addWidget(web_conj_data_btn)

        set_conj_data_btn = QPushButton('Install Conjugation Data From File')
        set_conj_data_btn.clicked.connect(self.set_conj_data)
        lang_lyt4.addWidget(set_conj_data_btn)

        lang_lyt1.addStretch()
        lang_lyt2.addStretch()
        lang_lyt3.addStretch()
        lang_lyt4.addStretch()


        self.dict_grp = QGroupBox('Dictionary Options')
        right_lyt.addWidget(self.dict_grp)

        dict_lyt = QHBoxLayout()
        self.dict_grp.setLayout(dict_lyt)

        remove_dict_btn = QPushButton('Remove Dictionary')
        remove_dict_btn.clicked.connect(self.remove_dict)
        dict_lyt.addWidget(remove_dict_btn)

        set_term_headers_btn = QPushButton('Edit Definition Header')
        set_term_headers_btn.clicked.connect(self.set_term_header)
        dict_lyt.addWidget(set_term_headers_btn)

        dict_lyt.addStretch()

    
        right_lyt.addStretch()


        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)


        self.reload_tree_widget()

        self.on_current_item_change(None, None)
    def info(self, text):
        dlg = QMessageBox(QMessageBox.Icon.Information, 'Miso Dictionary', text, QMessageBox.StandardButton.Ok, self)
        return dlg.exec()
    def get_string(self, text, default_text=''):
        dlg = QInputDialog(self)
        dlg.setWindowTitle('Miso Dictionary')
        dlg.setLabelText(text + ':')
        dlg.setTextValue(default_text)
        dlg.resize(350, dlg.sizeHint().height())
        ok = dlg.exec()
        txt = dlg.textValue()
        return txt, ok


    def reload_tree_widget(self):
        db = aqt.mw.miDictDB

        langs = db.getCurrentDbLangs()
        dicts_by_langs = {}

        for info in db.getAllDictsWithLang():
            lang = info['lang']

            dict_list = dicts_by_langs.get(lang, [])
            dict_list.append(info['dict'])
            dicts_by_langs[lang] = dict_list

        self.dict_tree.clear()

        for lang in langs:
            lang_item = QTreeWidgetItem([lang])
            lang_item.setData(0, Qt.ItemDataRole.UserRole+0, lang)
            lang_item.setData(0, Qt.ItemDataRole.UserRole+1, None)
            
            self.dict_tree.addTopLevelItem(lang_item)

            for d in dicts_by_langs.get(lang, []):
                dict_name = db.cleanDictName(d)
                dict_name = dict_name.replace('_', ' ')
                dict_item = QTreeWidgetItem([dict_name])
                dict_item.setData(0, Qt.ItemDataRole.UserRole+0, lang)
                dict_item.setData(0, Qt.ItemDataRole.UserRole+1, d)
                lang_item.addChild(dict_item)

            lang_item.setExpanded(True)


    def on_current_item_change(self, new_sel, old_sel):

        lang, dict_ = self.get_current_lang_dict()

        self.lang_grp.setEnabled(lang is not None)
        self.dict_grp.setEnabled(dict_ is not None)


    def get_current_lang_dict(self):

        curr_item = self.dict_tree.currentItem()

        lang = None
        dict_ = None

        if curr_item:
            lang = curr_item.data(0, Qt.ItemDataRole.UserRole+0)
            dict_ = curr_item.data(0, Qt.ItemDataRole.UserRole+1)

        return lang, dict_


    def get_current_lang_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent:
                return curr_item_parent
        
        return curr_item


    def get_current_dict_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent is None:
                return None
        
        return curr_item


    def web_installer(self):

        DictionaryWebInstallWizard.execute_modal()
        self.reload_tree_widget()


    def add_lang(self):
        db = aqt.mw.miDictDB

        text, ok = self.get_string('Select name of new language')
        if not ok:
            return

        name = text.strip()
        if not name:
            self.info('Language names may not be empty.')
            return

        try:
            db.addLanguages([name])
        except Exception as e:
            self.info('Adding language failed.')
            return

        lang_item = QTreeWidgetItem([name])
        lang_item.setData(0, Qt.ItemDataRole.UserRole+0, name)
        lang_item.setData(0, Qt.ItemDataRole.UserRole+1, None)

        self.dict_tree.addTopLevelItem(lang_item)
        self.dict_tree.setCurrentItem(lang_item)


    def remove_lang(self):
        db = aqt.mw.miDictDB

        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole+0)

        dlg = QMessageBox(QMessageBox.Icon.Question, 'Miso Dictionary',
                          'Do you really want to remove the language "%s"?\n\nAll settings and dictionaries for it will be removed.' % lang_name,
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        # Remove language from db
        db.deleteLanguage(lang_name)

        # Remove frequency data
        try:
            path = os.path.join(addon_path, 'user_files', 'db', 'frequency', '%s.json' % lang_name)
            os.remove(path)
        except OSError:
            pass

        # Remove conjugation data
        try:
            path = os.path.join(addon_path, 'user_files', 'db', 'conjugation', '%s.json' % lang_name)
            os.remove(path)
        except OSError:
            pass

        aqt.qt.sip.delete(lang_item)


    def set_freq_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(self, 'Select the frequency list you want to import', os.path.expanduser('~'), 'JSON Files (*.json);;All Files (*.*)')[0]
        if not path:
            return

        freq_path = os.path.join(addon_path, 'user_files', 'db', 'frequency')
        os.makedirs(freq_path, exist_ok=True)

        dst_path = os.path.join(freq_path, '%s.json' % lang_name)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.info('Importing frequency data failed.')
            return

        self.info('Imported frequency data for "%s".\n\nNote that the frequency data is only applied to newly imported dictionaries for this language.' % lang_name)


    def web_freq_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole+0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Freq)


    def set_conj_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(self, 'Select the conjugation data you want to import', os.path.expanduser('~'), 'JSON Files (*.json);;All Files (*.*)')[0]
        if not path:
            return

        conj_path = os.path.join(addon_path, 'user_files', 'db', 'conjugation')
        os.makedirs(conj_path, exist_ok=True)

        dst_path = os.path.join(conj_path, '%s.json' % lang_name)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.info('Importing conjugation data failed.')
            return

        self.info('Imported conjugation data for "%s".' % lang_name)


    def web_conj_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole+0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Conj)


    def import_dict(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole+0)

        path = QFileDialog.getOpenFileName(self, 'Select the dictionary you want to import',
                                           os.path.expanduser('~'), 'ZIP Files (*.zip);;All Files (*.*)')[0]
        if not path:
            return
        
        dict_name = os.path.splitext(os.path.basename(path))[0]
        dict_name, ok = self.get_string('Set name of dictionary', dict_name)

        try:
            importDict(lang_name, path, dict_name)
        except ValueError as e:
            self.info(str(e))
            return

        dict_item = QTreeWidgetItem([dict_name.replace('_', ' ')])
        dict_item.setData(0, Qt.ItemDataRole.UserRole+0, lang_name)
        dict_item.setData(0, Qt.ItemDataRole.UserRole+1, dict_name)

        lang_item.addChild(dict_item)
        self.dict_tree.setCurrentItem(dict_item)

    def import_dicts(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole + 0)

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            'Select the dictionaries you want to import',
            os.path.expanduser('~'),
            'ZIP Files (*.zip);;All Files (*.*)'
        )
        if not paths:
            return

        use_default_names = QMessageBox.question(
            self,
            "Use Default Names?",
            "Do you want to use default names for the imported dictionaries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

        progress = QProgressDialog("Importing dictionaries...", "Cancel", 0, len(paths), self)
        progress.setWindowTitle("Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)

        for i, path in enumerate(paths):
            if progress.wasCanceled():
                break

            dict_name = os.path.splitext(os.path.basename(path))[0]

            if not use_default_names:
                dict_name, ok = self.get_string('Set name of dictionary', dict_name)
                if not ok:
                    continue

            try:
                importDict(lang_name, path, dict_name)
            except ValueError as e:
                self.info(str(e))
                continue

            dict_item = QTreeWidgetItem([dict_name.replace('_', ' ')])
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 0, lang_name)
            dict_item.setData(0, Qt.ItemDataRole.UserRole + 1, dict_name)

            lang_item.addChild(dict_item)

            # Update progress
            progress.setValue(i + 1)

        progress.close()

        if paths:
            self.dict_tree.setCurrentItem(lang_item.child(lang_item.childCount() - 1))


    def web_installer_lang(self):
            lang_item = self.get_current_lang_item()
            if lang_item is None:
                return
            lang_name = lang_item.data(0, Qt.ItemDataRole.UserRole+0)

            DictionaryWebInstallWizard.execute_modal(lang_name)
            self.reload_tree_widget()


    def remove_dict(self):
        db = aqt.mw.miDictDB
        
        dict_item = self.get_current_dict_item()
        if dict_item is None:
            return
        dict_name = dict_item.data(0, Qt.ItemDataRole.UserRole+1)
        dict_display = dict_item.data(0, Qt.ItemDataRole.DisplayRole)

        dlg = QMessageBox(QMessageBox.Icon.Question, 'Miso Dictionary',
                          'Do you really want to remove the dictionary "%s"?' % dict_display,
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        r = dlg.exec()

        if r != QMessageBox.StandardButton.Yes:
            return

        db.deleteDict(dict_name)
        aqt.qt.sip.delete(dict_item)


    def set_term_header(self):
        db = aqt.mw.miDictDB

        dict_name = self.get_current_lang_dict()[1]
        if dict_name is None:
            return

        dict_clean = db.cleanDictName(dict_name)

        term_txt = ', '.join(json.loads(db.getDictTermHeader(dict_clean)))

        term_txt, ok = self.get_string('Set term header for dictionary "%s"' % dict_clean.replace('_', ' '), term_txt)

        if not ok:
            return

        parts_txt = term_txt.split(',')
        parts = []
        valid_parts = ['term', 'altterm', 'pronunciation']

        for part_txt in parts_txt:
            part = part_txt.strip().lower()
            if part not in valid_parts:
                self.info('The term header part "%s" is not valid.' % part_txt)
                return
            parts.append(part)

        db.setDictTermHeader(dict_clean, json.dumps(parts))

addon_path = os.path.dirname(__file__)

def importDict(lang_name, file, dict_name):
    db = aqt.mw.miDictDB
    
    try:
        zfile = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        raise ValueError('Dictionary archive is invalid.')

    is_pitch_dict = any(
        fn.endswith('.json') and "pitches" in zfile.read(fn).decode(errors='ignore')
        for fn in zfile.namelist()
    )
    is_yomichan = any(fn.startswith('term_bank_') for fn in zfile.namelist()) or is_pitch_dict

    has_index = any(fn == 'index.json' for fn in zfile.namelist())

    print("Importing dict")
    frequency_dict = getFrequencyList(lang_name)
    term_header = json.dumps(['term', 'altterm', 'pronunciation'])
    
    success, message, final_name = db.addDict(dict_name, lang_name, term_header)
    
    if not success:
        raise ValueError(
            f'Creating dictionary failed.\n'
            f'Original name: {dict_name}\n'
            f'Error: {message}'
        )
    
    dict_files = []
    for fn in zfile.namelist():
        if not fn.endswith('.json'):
            continue
        if is_yomichan and not fn.startswith('term_bank_'):
            continue
        dict_files.append(fn)
    dict_files = natural_sort(dict_files)
    
    loadDict(zfile, dict_files, lang_name, final_name, frequency_dict, not is_yomichan)
     
def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
    return sorted(l, key=alphanum_key)

def loadDict(zfile, filenames, lang, dictName, frequencyDict, miDict=False):
    tableName = 'l' + str(mw.miDictDB.getLangId(lang)) + 'name' + dictName
    jsonDict = []
    for filename in filenames:
        with zfile.open(filename, 'r') as jsonDictFile:
            jsonDict += json.loads(jsonDictFile.read())
    if frequencyDict:
        print("FreqDICT!")
        if miDict:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang, True)
        else:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang)
    for count, entry in enumerate(jsonDict):
        if isinstance(entry, list) and len(entry) == 3 and isinstance(entry[2], dict) and "pitches" in entry[2]:
            handlePitchDictEntry(jsonDict, count, entry)
        elif miDict:
            handleMiDictEntry(jsonDict, count, entry, frequencyDict is not None)
        else:
            handleYomiDictEntry(jsonDict, count, entry, frequencyDict is not None)
    mw.miDictDB.importToDict(tableName, jsonDict)
    mw.miDictDB.commitChanges()


def getAdjustedTerm(term):
    term = term.replace('\n', '')
    if len(term) > 1:
        term = term.replace('=', '')
    return term

def getAdjustedPronunciation(pronunciation):
    return pronunciation.replace('\n', '')


def getAdjustedDefinition(definition):
    definition = definition.replace('\n', '<br>')
    definition = definition.replace('◟', '<br>')
    definition = definition.replace('<', '&lt;').replace('>', '&gt;')
    definition = re.sub(r'<br>$', '', definition)
    return definition

def handlePitchDictEntry(jsonDict, count, entry):
    # Initialize default values
    term = ""
    altterm = ""
    reading = ""
    pos = ""
    definition = ""
    examples = ""
    audio = ""
    frequency = ""
    starCount = ""
    pitch_accent = ""

    # Extract pitch dictionary data
    term = entry[0]
    reading = entry[2].get("reading", entry[0])
    pitch_accent = entry[2]["pitches"][0].get("position") if entry[2]["pitches"] else None
    # altterm = str(pitch_accent) if pitch_accent is not None else ""

    # Create a 9-element tuple
    jsonDict[count] = (
        term,         # term
        altterm,      # altterm (pitch accent position)
        reading,      # pronunciation
        pos,          # part of speech
        definition,   # definition
        examples,     # examples
        audio,        # audio
        frequency,    # frequency
        starCount     # star count
    )

def handleYomiDictEntry(jsonDict, count, entry, freq=False):
    def extract_definition(items):
        """Extracts definition text from deeply nested dictionary structure."""

        def recursive_extract(item):
            if isinstance(item, str):
                return item.strip()
            elif isinstance(item, dict):
                if "name" in item.get("data", {}) and item["data"]["name"] == "語釈":
                    return recursive_extract(item.get("content", ""))
                return recursive_extract(item.get("content", ""))
            elif isinstance(item, list):
                return " ".join(recursive_extract(x) for x in item if recursive_extract(x))
            return ""

        definitions = []
        for item in items:
            text = recursive_extract(item)
            if text:
                # Replace any newline characters with <br/> to preserve line breaks
                text = text.replace("\n", "<br/>")
                definitions.append(text)
        return "<br/>".join(definitions)  # Join definitions with <br/>

    def find_header_section(items):
        """Find the header section in the content."""
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    if item.get("type") == "structured-content":
                        return find_header_section(item.get("content", []))
                    if item.get("data", {}).get("name") == "見出部":
                        return item.get("content", [])
        return []

    def extract_pitch(content):
        """
        Extract pitch accents from content by recursively searching through nested structures.
        Returns a list of integer accent positions.
        """
        accents = []

        def recursive_search(item):
            if isinstance(item, dict) and 'data' in item:
                name = item.get('data', {}).get('name', '')

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

    if len(entry) > 5 and isinstance(entry[5], list):
        definition = extract_definition(entry[5])

        header_section = find_header_section(entry[5])
        if header_section:
            pitch_accents = extract_pitch(header_section)

    # Always create a 9-element tuple
    jsonDict[count] = (
        term,  # term
        " ".join(str(p) for p in pitch_accents) if pitch_accents else "",  # altterm (pitch accent)
        reading,  # pronunciation
        pos,  # part of speech
        definition,  # definition
        "",  # examples
        "",  # audio
        frequency,  # frequency
        starCount  # star count
    )

def kaner(to_translate, hiraganer = False):
        hiragana = u"がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ" \
                   u"あいうえおかきくけこさしすせそたちつてと" \
                   u"なにぬねのはひふへほまみむめもやゆよらりるれろ" \
                   u"わをんぁぃぅぇぉゃゅょっゐゑ"
        katakana = u"ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ" \
                   u"アイウエオカキクケコサシスセソタチツテト" \
                   u"ナニヌネノハヒフヘホマミムメモヤユヨラリルレロ" \
                   u"ワヲンァィゥェォャュョッヰヱ"
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

def organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang, miDict=False):
    readingHyouki = frequencyDict.get('readingDictionaryType', False)

    for idx, entry in enumerate(jsonDict):
        if isinstance(entry, list):
            term = entry[0] if len(entry) > 0 else ''
            reading = entry[1] if len(entry) > 1 and isinstance(entry[1], str) else ''
            details = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else None

            if readingHyouki:
                if details:
                    reading = details.get('reading', '') or reading or term
                adjusted = adjustReading(reading)
            else:
                adjusted = None

            frequency = 999999
            starCount = ''

            if miDict and details is not None:
                if readingHyouki and term in frequencyDict:
                    if adjusted in frequencyDict[term]:
                        frequency = frequencyDict[term][adjusted]
                elif not readingHyouki and term in frequencyDict:
                    frequency = frequencyDict[term]
                details['frequency'] = frequency
                details['starCount'] = getStarCount(frequency)
            else:
                if readingHyouki and term in frequencyDict:
                    if adjusted in frequencyDict[term]:
                        frequency = frequencyDict[term][adjusted]
                elif not readingHyouki and term in frequencyDict:
                    frequency = frequencyDict[term]

                if len(entry) <= 8:
                    entry.extend([frequency, getStarCount(frequency)])
                else:
                    entry[8] = frequency
                    entry[9] = getStarCount(frequency)

        else:
            continue

    if miDict:
        return sorted(jsonDict, key=lambda i: i[2].get('frequency', 999999) if isinstance(i[2], dict) else 999999)
    else:
        return sorted(jsonDict, key=lambda i: i[8] if len(i) > 8 else 999999)

def getStarCount(freq):
    if freq < 1501:
        return '★★★★★'
    elif freq < 5001:
        return '★★★★'
    elif freq < 15001:
        return '★★★'
    elif freq < 30001:
        return '★★'
    elif freq < 60001:
        return '★'
    else:
        return ''

def getFrequencyList(lang):
    filePath = os.path.join(addon_path, 'user_files', 'db', 'frequency', '%s.json' % lang)
    frequencyDict = {}
    if os.path.exists(filePath):
        frequencyList = json.load(open(filePath, 'r', encoding='utf-8-sig'))
        if isinstance(frequencyList[0], str):
            yomi = False
            frequencyDict['readingDictionaryType'] = False
        elif isinstance(frequencyList[0], list) and len(frequencyList[0]) == 2 and isinstance(frequencyList[0][0], str) and isinstance(frequencyList[0][1], str):
            yomi = True
            frequencyDict['readingDictionaryType'] = True
        else:
            return False
        for idx, f in enumerate(frequencyList):
            if yomi:
                if f[0] in frequencyDict:
                    frequencyDict[f[0]][f[1]] = idx
                else:
                    frequencyDict[f[0]] = {}
                    frequencyDict[f[0]][f[1]] = idx
            else:
                frequencyDict[f] = idx
        return frequencyDict
    else:
        return False