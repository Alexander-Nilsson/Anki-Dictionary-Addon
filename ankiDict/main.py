# -*- coding: utf-8 -*-
# 
from os.path import dirname, join, basename, exists, join
import sys, os, platform, re, subprocess, aqt.utils
from anki.utils import strip_html, is_win, is_mac, is_lin

# from anki.utils import strip_html, is_win, is_mac, is_lin

from .midict import DictInterface, ClipThread
from .themes import *
from .themeEditor import *
import re
import unicodedata
import urllib.parse
from shutil import copyfile
from anki.hooks import addHook, wrap, runHook, runFilter
from aqt.utils import shortcut, saveGeom, saveSplitter, showInfo, askUser
import aqt.editor
import json
from aqt import mw
from aqt.qt import *
from . import dictdb
from aqt.webview import AnkiWebView
from .miutils import miInfo, miAsk
from .addonSettings import SettingsGui
import codecs
from operator import itemgetter
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.reviewer import Reviewer
from . import googleimages
from .forvodl import Forvo
from urllib.request import Request, urlopen
from aqt.previewer import Previewer
import requests
import time
import os


mw.MisoDictConfig = mw.addonManager.getConfig(__name__)
mw.MisoExportingDefinitions = False
mw.dictSettings = False
mw.miDictDB = dictdb.DictDB()
progressBar = False
addon_path = dirname(__file__)
currentNote = False 
currentField = False
currentKey = False
wrapperDict = False
tmpdir = join(addon_path, 'temp')
mw.misoEditorLoadedAfterDictionary = False
mw.MisoBulkMediaExportWasCancelled = False


def refreshMisoDictConfig(config = False):
    if config:
        mw.MisoDictConfig = config
        return
    mw.MisoDictConfig = mw.addonManager.getConfig(__name__)

mw.refreshMisoDictConfig = refreshMisoDictConfig

def removeTempFiles():
    filelist = [ f for f in os.listdir(tmpdir)]
    for f in filelist:
        path = os.path.join(tmpdir, f)
        try:
            os.remove(path)
        except:
            innerDirFiles = [ df for df in os.listdir(path)]
            for df in innerDirFiles:
                innerPath = os.path.join(path, df)
                os.remove(innerPath)
            os.rmdir(path)

removeTempFiles()

def miso(text):
    showInfo(text ,False,"", "info", "Miso Dictionary Add-on")

def showA(ar):
    showInfo(json.dumps(ar, ensure_ascii=False))


dictWidget  = False

js = QFile(':/qtwebchannel/qwebchannel.js')
assert js.open(QIODevice.ReadOnly)
js = bytes(js.readAll()).decode('utf-8')


def searchCol(self):
    text = selectedText(self)
    performColSearch(text)


def performColSearch(text):
    if text:
        text = text.strip()
        browser = aqt.DialogManager._dialogs["Browser"][1]
        if not browser:
            mw.onBrowse()
            browser = aqt.DialogManager._dialogs["Browser"][1]
        if browser:
            browser.form.searchEdit.lineEdit().setText(text)
            browser.onSearchActivated()
            browser.activateWindow()
            if not is_win:
                browser.setWindowState(browser.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
                browser.raise_()  
            else:
                browser.setWindowFlags(browser.windowFlags() | Qt.WindowState.WindowStaysOnTopHint)
                browser.show()
                browser.setWindowFlags(browser.windowFlags() & ~Qt.WindowState.WindowStaysOnTopHint)
                browser.show()


mw.currentlyPressed = []

def captureKey(keyList):
    key = keyList[0]
    char = str(key)
    if char not in mw.currentlyPressed:
            mw.currentlyPressed.append(char)
    if is_win:
        if 'Key.ctrl_l' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and'Key.space'  in mw.currentlyPressed:
            mw.hkThread.handleSystemSearch()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and "'b'"  in mw.currentlyPressed:
            mw.hkThread.handleColSearch()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and 'Key.alt_l' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []
    elif is_lin:
        if 'Key.ctrl' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and'Key.space'  in mw.currentlyPressed:
            mw.hkThread.handleSystemSearch()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and 'Key.alt' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []
    else:
        if ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed)  and "'c'" in mw.currentlyPressed and "'b'"  in mw.currentlyPressed:
            mw.hkThread.handleColSearch()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and "'c'" in mw.currentlyPressed and 'Key.ctrl' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []

   
def releaseKey(keyList):
    key = keyList[0]
    try:
        mw.currentlyPressed.remove(str(key))
    except:
        return
    

def exportSentence(sentence):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        mw.misoDictionary.dict.exportSentence(sentence)
        showCardExporterWindow()

def exportImage(img):
    print("exportImage")
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        if img[1].startswith('[sound:'):
            mw.misoDictionary.dict.exportAudio(img)
        else:
            mw.misoDictionary.dict.exportImage(img)
        showCardExporterWindow()

def extensionBulkTextExport(cards):
    if not mw.misoDictionary or not mw.misoDictionary.isVisible(): 
        mw.dictionaryInit()
    mw.misoDictionary.dict.bulkTextExport(cards)


def extensionBulkMediaExport(card):
    if not mw.misoDictionary or not mw.misoDictionary.isVisible(): 
        mw.dictionaryInit()
    mw.misoDictionary.dict.bulkMediaExport(card)


def cancelBulkMediaExport():
    if mw.misoDictionary and mw.misoDictionary.isVisible(): 
        mw.misoDictionary.dict.cancelBulkMediaExport()


def extensionCardExport(card):
    primary = card["primary"]
    secondary = card["secondary"]
    image = card["image"]
    audio = card["audio"]
    unknownsToSearch = mw.MisoDictConfig.get("unknownsToSearch", 3)
    autoExportCards = mw.MisoDictConfig.get("autoAddCards", False)
    unknownWords = card["unknownWords"][:unknownsToSearch]
    if len(unknownWords) > 0:
        if not autoExportCards:
            searchTermList(unknownWords)
        elif not mw.misoDictionary or not mw.misoDictionary.isVisible(): 
            mw.dictionaryInit()
        mw.misoDictionary.dict.exportWord(unknownWords[0])
    else:
        if not mw.misoDictionary or not mw.misoDictionary.isVisible(): 
                mw.dictionaryInit()
        mw.misoDictionary.dict.exportWord('')
    if audio:
        mw.misoDictionary.dict.exportAudio([join(mw.col.media.dir(), audio), '[sound:' + audio +']', audio]) 
    if image:
        mw.misoDictionary.dict.exportImage([join(mw.col.media.dir(), image), image]) 
    mw.misoDictionary.dict.exportSentence(primary, secondary)
    mw.misoDictionary.dict.addWindow.focusWindow()
    mw.misoDictionary.dict.attemptAutoAdd(False)
    showCardExporterWindow()
      
def showCardExporterWindow():
    adder = mw.misoDictionary.dict.addWindow
    cardWindow = adder.scrollArea
    if not is_win:
        cardWindow.setWindowState(cardWindow.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        cardWindow.raise_()  
    else:
        cardWindow.setWindowFlags(cardWindow.windowFlags() | Qt.WindowState.WindowStaysOnTopHint)
        cardWindow.show()
        if not adder.alwaysOnTop:
            cardWindow.setWindowFlags(cardWindow.windowFlags() & ~Qt.WindowState.WindowStaysOnTopHint)
            cardWindow.show()

def trySearch(term):    
    if mw.misoDictionary and mw.misoDictionary.isVisible(): 
        mw.misoDictionary.initSearch(term)    
        showAfterGlobalSearch() 
    elif mw.MisoDictConfig['openOnGlobal'] and (not mw.misoDictionary or not mw.misoDictionary.isVisible()):  
        mw.dictionaryInit([term])   


def showAfterGlobalSearch():
    mw.misoDictionary.activateWindow()
    if not is_win:
        mw.misoDictionary.setWindowState(mw.misoDictionary.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        mw.misoDictionary.raise_()  
    else:
        mw.misoDictionary.setWindowFlags(mw.misoDictionary.windowFlags() | Qt.WindowState.WindowStaysOnTopHint)
        mw.misoDictionary.show()
        if not mw.misoDictionary.alwaysOnTop:
            mw.misoDictionary.setWindowFlags(mw.misoDictionary.windowFlags() & ~Qt.WindowState.WindowStaysOnTopHint)
            mw.misoDictionary.show()

def attemptAddCard(add):
    if mw.misoDictionary and mw.misoDictionary.isVisible() and mw.misoDictionary.dict.addWindow and mw.misoDictionary.dict.addWindow.scrollArea.isVisible():
        time.sleep(.3)
        mw.misoDictionary.dict.addWindow.addCard()


def openDictionarySettings():
    if not mw.dictSettings:
        mw.dictSettings = SettingsGui(mw, addon_path, openDictionarySettings)
    mw.dictSettings.show()
    if mw.dictSettings.windowState() == Qt.WindowState.WindowMinimized:
           mw.dictSettings.setWindowState(Qt.WindowState.WindowNoState)
    mw.dictSettings.setFocus()
    mw.dictSettings.activateWindow()


def getWelcomeScreen():
    htmlPath = join(addon_path, 'welcome.html')
    with open(htmlPath,'r', encoding="utf-8") as fh:
        file =  fh.read()
    return file
           
def getMacWelcomeScreen():
    htmlPath = join(addon_path, 'macwelcome.html')
    with open(htmlPath,'r', encoding="utf-8") as fh:
        file =  fh.read()
    return file

if is_mac:
    welcomeScreen = getMacWelcomeScreen()
else:
    welcomeScreen = getWelcomeScreen()

def dictionaryInit(terms = False):
    if terms and isinstance(terms, str):
        terms = [terms]
    shortcut = '(Ctrl+W)'
    if is_mac:
        shortcut = '⌘W'
    if not mw.misoDictionary:
        mw.misoDictionary = DictInterface(mw.miDictDB, mw, addon_path, welcomeScreen, terms = terms)
        mw.openMiDict.setText("Close Dictionary " + shortcut)
        showAfterGlobalSearch()
    elif not mw.misoDictionary.isVisible():
        mw.misoDictionary.show()
        mw.misoDictionary.resetConfiguration(terms)
        mw.openMiDict.setText("Close Dictionary " + shortcut)
        showAfterGlobalSearch()
    else:
        mw.misoDictionary.hide()

mw.dictionaryInit = dictionaryInit

def setupGuiMenu():
    addMenu = False
    if not hasattr(mw, 'MisoMainMenu'):
        mw.MisoMainMenu = QMenu('Miso',  mw)
        addMenu = True
    if not hasattr(mw, 'MisoMenuSettings'):
        mw.MisoMenuSettings = []
    if not hasattr(mw, 'MisoMenuActions'):
        mw.MisoMenuActions = []

    setting = QAction("Dictionary Settings", mw)
    setting.triggered.connect(openDictionarySettings)
    mw.MisoMenuSettings.append(setting)

    mw.openMiDict = QAction("Open Dictionary (Ctrl+W)", mw)
    mw.openMiDict.triggered.connect(dictionaryInit)
    mw.MisoMenuActions.append(mw.openMiDict)

    mw.MisoMainMenu.clear()
    for act in mw.MisoMenuSettings:
        mw.MisoMainMenu.addAction(act)
    mw.MisoMainMenu.addSeparator()
    for act in mw.MisoMenuActions:
        mw.MisoMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.MisoMainMenu)  

setupGuiMenu()

mw.misoDictionary = False

def searchTermList(terms):
    limit = mw.MisoDictConfig.get("unknownsToSearch", 3)
    terms = terms[:limit]
    if not mw.misoDictionary or not mw.misoDictionary.isVisible():
        mw.dictionaryInit(terms)
    else:
        for term in terms:
            mw.misoDictionary.initSearch(term)
        showAfterGlobalSearch()

def extensionFileNotFound():
    miInfo("The media files were not found in your \"Download Directory\", please make sure you have selected the correct directory.")

def initGlobalHotkeys():
    mw.hkThread = ClipThread(mw, addon_path)
    mw.hkThread.sentence.connect(exportSentence)
    mw.hkThread.search.connect(trySearch)
    mw.hkThread.colSearch.connect(performColSearch)
    mw.hkThread.image.connect(exportImage)
    mw.hkThread.bulkTextExport.connect(extensionBulkTextExport)
    mw.hkThread.add.connect(attemptAddCard)
    mw.hkThread.test.connect(captureKey)
    mw.hkThread.release.connect(releaseKey)
    mw.hkThread.pageRefreshDuringBulkMediaImport.connect(cancelBulkMediaExport)
    mw.hkThread.bulkMediaExport.connect(extensionBulkMediaExport)
    mw.hkThread.extensionCardExport.connect(extensionCardExport)
    mw.hkThread.searchFromExtension.connect(searchTermList)
    mw.hkThread.extensionFileNotFound.connect(extensionFileNotFound)
    mw.hkThread.run()

if mw.addonManager.getConfig(__name__)['globalHotkeys']:
    initGlobalHotkeys()

mw.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), mw)
mw.hotkeyW.activated.connect(dictionaryInit)


def selectedText(page):    
    text = page.selectedText()
    if not text:
        return False
    else:
        return text

def searchTerm(self):
    text = selectedText(self)
    if text:
        text = re.sub(r'\[[^\]]+?\]', '', text)
        text = text.strip()
        if not mw.misoDictionary or not mw.misoDictionary.isVisible():
            dictionaryInit([text])
        mw.misoDictionary.ensureVisible()
        mw.misoDictionary.initSearch(text)
        if self.title == 'main webview':
            if mw.state == 'review':
                mw.misoDictionary.dict.setReviewer(mw.reviewer)
        elif self.title == 'editor':
            target = getTarget(type(self.parentEditor.parentWindow).__name__)
            mw.misoDictionary.dict.setCurrentEditor(self.parentEditor, target)
        showAfterGlobalSearch()





mw.searchTerm = searchTerm
mw.searchCol = searchCol

        
 
mw.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), mw)  
mw.hotkeyS.activated.connect(lambda: searchTerm(mw.web))    
mw.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), mw)  
mw.hotkeyS.activated.connect(lambda: searchCol(mw.web)) 


def addToContextMenu(self, m):
    a = m.addAction("Search (Ctrl+S)")
    a.triggered.connect(self.searchTerm)
    b = m.addAction("Search Collection (Ctrl/⌘+Shift+B)")
    b.triggered.connect(self.searchCol)

def exportDefinitionsWidget(browser):
    import anki.find
    notes = browser.selectedNotes()
    if notes:
        fields = anki.find.fieldNamesForNotes(mw.col, notes)
        generateWidget = QDialog(None, Qt.WindowType.Window)
        layout = QHBoxLayout()
        origin = QComboBox()
        origin.addItems(fields)
        addType = QComboBox()
        addType.addItems(['Add','Overwrite', 'If Empty'])
        dicts = QComboBox()
        dict2 = QComboBox()
        dict3 = QComboBox()
        dictDict = {}
        tempdicts = []
        for d in mw.miDictDB.getAllDicts():
            dictName = mw.miDictDB.cleanDictName(d)
            dictDict[dictName] = d;
            tempdicts.append(dictName)
        tempdicts.append('Google Images')
        tempdicts.append('Forvo')
        dicts.addItems(sorted(tempdicts))
        dict2.addItem('None')
        dict2.addItems(sorted(tempdicts))
        dict3.addItem('None')
        dict3.addItems(sorted(tempdicts))
        dictDict['Google Images'] = 'Google Images'
        dictDict['Forvo'] = 'Forvo'
        dictDict['None'] = 'None'
        ex =  QPushButton('Execute')
        ex.clicked.connect(lambda: exportDefinitions(origin.currentText(), destination.currentText(), addType.currentText(), 
            [dictDict[dicts.currentText()], dictDict[dict2.currentText()] , 
            dictDict[dict3.currentText()]], howMany.value(), notes, generateWidget, 
            [dicts.currentText(),dict2.currentText(), dict3.currentText()]))
        destination = QComboBox()
        destination.addItems(fields)
        howMany = QSpinBox()
        howMany.setValue(1)
        howMany.setMinimum(1)
        howMany.setMaximum(20)
        oLayout = QVBoxLayout()
        oh1 = QHBoxLayout()
        oh2 = QHBoxLayout()
        oh1.addWidget(QLabel('Input Field:'))
        oh1.addWidget(origin)
        oh2.addWidget(QLabel('Output Field:'))
        oh2.addWidget(destination)
        oLayout.addStretch()
        oLayout.addLayout(oh1)
        oLayout.addLayout(oh2)
        oLayout.addStretch()
        oLayout.setContentsMargins(6,0, 6, 0)
        layout.addLayout(oLayout)
        dlay = QHBoxLayout()
        dlay.addWidget(QLabel('Dictionaries:'))
        dictLay = QVBoxLayout()
        dictLay.addWidget(dicts)
        dictLay.addWidget(dict2)
        dictLay.addWidget(dict3)
        dlay.addLayout(dictLay)
        dlay.setContentsMargins(6,0, 6, 0)
        layout.addLayout(dlay)
        bLayout = QVBoxLayout()
        bh1 = QHBoxLayout()
        bh2 = QHBoxLayout()
        bh1.addWidget(QLabel('Output Mode:'))
        bh1.addWidget(addType)
        bh2.addWidget(QLabel('Max Per Dict:'))
        bh2.addWidget(howMany)
        bLayout.addStretch()
        bLayout.addLayout(bh1)
        bLayout.addLayout(bh2)
        bLayout.addStretch()
        bLayout.setContentsMargins(6,0, 6, 0)
        layout.addLayout(bLayout)
        layout.addWidget(ex)
        layout.setContentsMargins(10,6, 10, 6)
        generateWidget.setWindowFlags(generateWidget.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        generateWidget.setWindowTitle("Miso Dictionary: Export Definitions")
        generateWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'miso.png')))
        generateWidget.setLayout(layout)
        config = mw.addonManager.getConfig(__name__)
        savedPreferences = config.get("massGenerationPreferences", False)
        if savedPreferences:
            if dicts.findText(savedPreferences["dict1"]) != -1:
                dicts.setCurrentText(savedPreferences["dict1"])
            if dict2.findText(savedPreferences["dict2"]) != -1:
                dict2.setCurrentText(savedPreferences["dict2"])
            if dict3.findText(savedPreferences["dict3"]) != -1:
                dict3.setCurrentText(savedPreferences["dict3"])
            if origin.findText(savedPreferences["origin"]) != -1:
                origin.setCurrentText(savedPreferences["origin"])
            if destination.findText(savedPreferences["destination"])  != -1:
                destination.setCurrentText(savedPreferences["destination"])
            addType.setCurrentText(savedPreferences["addType"])
            howMany.setValue(savedPreferences["limit"])
        generateWidget.exec()
    else:
        miInfo('Please select some cards before attempting to export definitions.', level='not')

def getProgressWidgetDefs():
    progressWidget = QWidget(None)
    layout = QVBoxLayout()
    progressWidget.setFixedSize(400, 70)
    progressWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'miso.png')))
    progressWidget.setWindowTitle("Generating Definitions...")
    progressWidget.setWindowModality(Qt.WindowModality.ApplicationModal)
    bar = QProgressBar(progressWidget)
    if is_mac:
        bar.setFixedSize(380, 50)
    else:
        bar.setFixedSize(390, 50)
    bar.move(10,10)
    per = QLabel(bar)
    per.setAlignment(Qt.AlignmentFlag.AlignCenter)
    progressWidget.show()
    return progressWidget, bar;

def getTermHeaderText(th, entry, fb, bb):
    headerList = []
    term = entry['term']
    altterm = entry['altterm']
    if altterm == term:
        altterm == ''
    pron = entry['pronunciation']
    if pron == term:
        pron = ''

    termHeader = ''
    for header in th:
        if header == 'term':
            termHeader += fb + term + bb
        elif header == 'altterm':
            if altterm != '':
                termHeader += fb + altterm + bb
        elif header == 'pronunciation':
            if pron != '':
                if termHeader != '':
                    termHeader += ' '
                termHeader  += pron + ' '
    termHeader += entry['starCount']
    return termHeader

def formatDefinitions(results, th,dh, fb, bb):
    definitions = []
    for idx, r in enumerate(results):
        text = ''
        if dh == 0:
           
            text = getTermHeaderText(th, r, fb, bb) + '<br>' + r['definition']
        else:
            stars = r['starCount']
            text =  r['definition'] 
            if '】' in text:
                text = text.replace('】',  '】' + stars + ' ', 1)
            elif '<br>' in text:
                text = text.replace('<br>', stars+ '<br>', 1);
            else:
                text = stars + '<br>' + text
        definitions.append(text)
    return '<br><br>'.join(definitions).replace('<br><br><br>', '<br><br>')

googleImager = None

def initImager():
    global googleImager
    googleImager = googleimages.Google()
    config = mw.addonManager.getConfig(__name__)
    googleImager.setSearchRegion(config['googleSearchRegion'])
    googleImager.setSafeSearch(config["safeSearch"])

def exportGoogleImages(term, howMany):
    config = mw.addonManager.getConfig(__name__)
    maxW = config['maxWidth']
    maxH = config['maxHeight']
    if not googleImager:
        initImager()
    imgSeparator = ''
    imgs = []
    urls = googleImager.search(term, 80)
    if len(urls) < 1:
        time.sleep(.1)
        urls = googleImager.search(term, 80, 'countryUS')
    for url in urls:
        time.sleep(.1)
        img = downloadImage(url, maxW, maxH)
        if img:
            imgs.append(img)
        if len(imgs) == howMany:
            break
    return imgSeparator.join(imgs)

def downloadImage(url, maxW, maxH):
    try:
        filename = str(time.time()).replace('.', '') + '.png'
        req = Request(url , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
        file = urlopen(req).read()
        image = QImage()
        image.loadFromData(file)
        image = image.scaled(QSize(maxW,maxH), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image.save(filename)
        return '<img ankiDict="' + filename + '">'
    except:
        return False

forvoDler = False;
def initForvo():
    global forvoDler
    forvoDler= Forvo(mw.addonManager.getConfig(__name__)['ForvoLanguage'])


import base64
def decodeURL(url1, url2, protocol, audiohost, server):
    url2 = protocol + "//" + server + "/player-mp3-highHandler.php?path=" + url2;
    url1 = protocol + "//" + audiohost + "/mp3/" + base64.b64decode(url1).decode("utf-8", "strict")
    return url1, url2

    

def generateURLS(results, language):
    audio = re.findall(r'var pronunciations = \[([\w\W\n]*?)\];', results)
    if not audio:
        return []
    audio = audio[0]
    data = re.findall(language + r'.*?Pronunciation by (?:<a.*?>)?(\w+).*?class="lang_xx"\>(.*?)\<.*?,.*?,.*?,.*?,\'(.+?)\',.*?,.*?,.*?\'(.+?)\'', audio)     
    if data:
        server = re.search(r"var _SERVER_HOST=\'(.+?)\';", results).group(1)
        audiohost = re.search(r'var _AUDIO_HTTP_HOST=\'(.+?)\';', results).group(1)
        protocol = 'https:'
        urls = []
        for datum in data:
            urls.append(decodeURL(datum[2],datum[3],protocol, audiohost, server))
        return urls
        


def exportForvoAudio(term, howMany, lang):
    if not forvoDler:
        initForvo()
    audioSeparator = ''
    urls = forvoDler.search(term, lang)
    if len(urls) < 1:
        time.sleep(.1)
        urls = forvoDler.search(term)
    tags = downloadForvoAudio(urls, howMany)
    return audioSeparator.join(tags)

def downloadForvoAudio( urls, howMany):
    tags = []
    for url in urls:
        if len(tags) == howMany:
            break
        try:
            req = Request(url[3] , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            file = urlopen(req).read()
            filename = str(time.time()) + '.mp3'
            open(join(mw.col.media.dir(), filename), 'wb').write(file)
            tags.append('[sound:' + filename + ']')
            success = True
        except: 
            success = True
        if success:
            continue
        else:
            try:
                req = Request(url[2] , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                file = urlopen(req).read()
                filename = str(time.time()) + '.mp3'
                open(join(mw.col.media.dir(), filename), 'wb').write(file)
                tags.append('[sound:' + filename + ']')
            except:
                continue
    return tags



def closeBar(event):
    mw.MisoExportingDefinitions = False
    event.accept()


def addDefinitionsToCardExporterNote(note, term, dictionaryConfigurations):
    config = mw.addonManager.getConfig(__name__)
    fb = config['frontBracket']
    bb = config['backBracket']
    lang = config['ForvoLanguage']
    fields = mw.col.models.field_names(note.note_type())
    for dictionary in dictionaryConfigurations:
        tableName = dictionary["tableName"]
        dictName  = dictionary["dictName"]
        limit = dictionary["limit"]
        targetField = dictionary["field"]
        if targetField in fields:
            term = re.sub(r'<[^>]+>', '', term) 
            term = re.sub(r'\[[^\]]+?\]', '', term)
            if term == '':
                continue
            tresults = []
            if tableName == 'Google Images':
                tresults.append(exportGoogleImages(term, limit))
            elif tableName == 'Forvo':
                tresults.append(exportForvoAudio(term, limit, lang))
            elif tableName != 'None':
                dresults, dh, th = mw.miDictDB.getDefForMassExp(term, tableName, str(limit), dictName)
                tresults.append(formatDefinitions(dresults, th, dh, fb, bb))
            results = '<br><br>'.join([i for i in tresults if i != ''])
            if results != "":
                if note[targetField] == '' or note[targetField] == '<br>':
                    note[targetField] = results
                else:
                    note[targetField] += '<br><br>' + results
    return note    

mw.addDefinitionsToCardExporterNote = addDefinitionsToCardExporterNote

def exportDefinitions(og, dest, addType, dictNs, howMany, notes, generateWidget, rawNames):
    config = mw.addonManager.getConfig(__name__)
    config["massGenerationPreferences"] = {
        "dict1" : rawNames[0],
        "dict2" : rawNames[1],
        "dict3" : rawNames[2],
        "origin" : og,
        "destination" : dest,
        "addType" : addType,
        "limit" : howMany
    }
    mw.addonManager.writeConfig(__name__, config)
    # mw.checkpoint('Definition Export')
    if not miAsk('Are you sure you want to export definitions for the "'+ og + '" field into the "' + dest +'" field?'):
        return
    progWid, bar = getProgressWidgetDefs()   
    progWid.closeEvent = closeBar
    bar.setMinimum(0)
    bar.setMaximum(len(notes))
    val = 0;
    fb = config['frontBracket']
    bb = config['backBracket']
    lang = config['ForvoLanguage']
    mw.progress.start()
    mw.MisoExportingDefinitions = True
    for nid in notes:
        if not mw.MisoExportingDefinitions:
            break
        note = mw.col.getNote(nid)
        fields = mw.col.models.field_names(note.model())
        if og in fields and dest in fields:
            term = re.sub(r'<[^>]+>', '', note[og]) 
            term = re.sub(r'\[[^\]]+?\]', '', term)
            if term == '':
                continue
            tresults = []
            dCount = 0
            for dictN in dictNs:
                if dictN == 'Google Images':
                    tresults.append(exportGoogleImages( term, howMany))
                elif dictN == 'Forvo':
                    tresults.append(exportForvoAudio( term, howMany, lang))
                elif dictN != 'None':
                    dresults, dh, th = mw.miDictDB.getDefForMassExp(term, dictN, str(howMany), rawNames[dCount])
                    tresults.append(formatDefinitions(dresults, th, dh, fb, bb))
                dCount+= 1
            results = '<br><br>'.join([i for i in tresults if i != ''])      
            if addType == 'If Empty':
                if note[dest] == '':
                    note[dest] = results
            elif addType == 'Add':
                if note[dest] == '':
                    note[dest] = results
                else:
                    note[dest] += '<br><br>' + results
            else:
                note[dest] = results
            # note.flush()
            mw.col.update_note(note, skip_undo_entry=True);
        val+=1;
        bar.setValue(val)
        mw.app.processEvents()
    # mw.progress.finish()
    try:
        mw.progress.finish()
    except AttributeError as e:
        print("Progress finish error:", e)
    mw.reset()
    generateWidget.hide()
    generateWidget.deleteLater()

def dictOnStart():
    if mw.addonManager.getConfig(__name__)['dictOnStart']:
        mw.dictionaryInit()

def setupMenu(browser):
    a = QAction("Export Definitions", browser)
    a.triggered.connect(lambda: exportDefinitionsWidget(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

def closeDictionary():
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        mw.misoDictionary.saveSizeAndPos()
        mw.misoDictionary.hide()
        mw.openMiDict.setText("Open Dictionary (Ctrl+W)")


addHook("unloadProfile", closeDictionary)
AnkiWebView.searchTerm = searchTerm
AnkiWebView.searchCol = searchCol
addHook("EditorWebView.contextMenuEvent", addToContextMenu)
addHook("AnkiWebView.contextMenuEvent", addToContextMenu)
addHook("profileLoaded", dictOnStart)
addHook("browser.setupMenus", setupMenu)

def bridgeReroute(self, cmd):
    if cmd == "bodyClick":
        if mw.misoDictionary and mw.misoDictionary.isVisible() and self.note:
            widget = type(self.widget.parentWidget()).__name__
            if widget == 'QWidget':
                widget = 'Browser'
            target = getTarget(widget)
            mw.misoDictionary.dict.setCurrentEditor(self, target)
        if hasattr(mw, "MisoEditorLoaded"):
                ogReroute(self, cmd)
    else:
        if cmd.startswith("focus"):
            
            if mw.misoDictionary and mw.misoDictionary.isVisible() and self.note:
                widget = type(self.widget.parentWidget()).__name__
                if widget == 'QWidget':
                    widget = 'Browser'
                target = getTarget(widget)
                mw.misoDictionary.dict.setCurrentEditor(self, target)
        ogReroute(self, cmd)
    
ogReroute = aqt.editor.Editor.onBridgeCmd 
aqt.editor.Editor.onBridgeCmd = bridgeReroute

# def setBrowserEditor(browser, c , p):
#     if mw.misoDictionary and mw.misoDictionary.isVisible():
#         if browser.editor.note:
#             mw.misoDictionary.dict.setCurrentEditor(browser.editor, 'Browser')
#         else:
#             mw.misoDictionary.dict.closeEditor()

def setBrowserEditor(browser):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        if browser.editor.note:
            mw.misoDictionary.dict.setCurrentEditor(browser.editor, 'Browser')
        else:
            mw.misoDictionary.dict.closeEditor()

def checkCurrentEditor(self):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        mw.misoDictionary.dict.checkEditorClose(self.editor)

Browser.on_current_row_changed = wrap(Browser.on_current_row_changed, setBrowserEditor)

AddCards._close = wrap(AddCards._close, checkCurrentEditor)

EditCurrent._saveAndClose = wrap(EditCurrent._saveAndClose, checkCurrentEditor)
Browser._closeWindow = wrap(Browser._closeWindow, checkCurrentEditor)

def addEditActivated(self, event = False):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        mw.misoDictionary.dict.setCurrentEditor(self.editor, getTarget(type(self).__name__))

bodyClick = '''document.addEventListener("click", function (ev) {
        pycmd("bodyClick")
    }, false);'''

def addBodyClick(self):
    self.web.eval(bodyClick)

def addClickEvent(self):
    self.historyButton.clicked.connect(lambda: attention(self))

AddCards.addCards = wrap(AddCards.addCards, addEditActivated)
AddCards.onHistory = wrap(AddCards.onHistory, addEditActivated)


def addHotkeys(self):   
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self.parentWindow)    
    self.parentWindow.hotkeyS.activated.connect(lambda: searchTerm(self.web))   
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), self.parentWindow)    
    self.parentWindow.hotkeyS.activated.connect(lambda: searchCol(self.web))    
    self.parentWindow.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self.parentWindow)    
    self.parentWindow.hotkeyW.activated.connect(dictionaryInit)


def addHotkeysToPreview(self):  
    self._web.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self._web)
    self._web.hotkeyS.activated.connect(lambda: searchTerm(self._web))
    self._web.hotkeyS = QShortcut(QKeySequence("Ctrl+Shift+B"), self._web)
    self._web.hotkeyS.activated.connect(lambda: searchCol(self._web))
    self._web.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self._web)
    self._web.hotkeyW.activated.connect(dictionaryInit)
    
Previewer.open = wrap(Previewer.open, addHotkeysToPreview)


def addEditorFunctionality(self):
    self.web.parentEditor = self
    addBodyClick(self)
    addHotkeys(self)
    
def gt(obj):
    return type(obj).__name__

def getTarget(name):
    if name == 'AddCards':
        return 'Add'
    elif name == "EditCurrent" or name == "MisoEditCurrent":
        return 'Edit'
    elif name == 'Browser':
        return name

def announceParent(self, event = False):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        parent = self.parentWidget().parentWidget().parentWidget()
        pName = gt(parent)
        if gt(parent) not in ['AddCards', 'EditCurrent']:
            parent =  aqt.DialogManager._dialogs["Browser"][1]
            pName = 'Browser'
            if not parent:
                return
        mw.misoDictionary.dict.setCurrentEditor(parent.editor, getTarget(pName))
            
def addClickToTags(self):
    self.tags.clicked.connect(lambda: announceParent(self))

TagEdit.focusInEvent = wrap(TagEdit.focusInEvent, announceParent)
aqt.editor.Editor.setupWeb = wrap(aqt.editor.Editor.setupWeb, addEditorFunctionality)
AddCards.mousePressEvent = addEditActivated
EditCurrent.mousePressEvent = addEditActivated

def miLinks(self, cmd):
    if mw.misoDictionary and mw.misoDictionary.isVisible():
        mw.misoDictionary.dict.setReviewer(self)
    return ogLinks(self, cmd)

ogLinks = Reviewer._linkHandler
Reviewer._linkHandler = miLinks
Reviewer.show = wrap(Reviewer.show, addBodyClick)


