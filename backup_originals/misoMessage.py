# -*- coding: utf-8 -*-
# 

import aqt
from aqt.qt import *
from os.path import dirname, join
from aqt.webview import AnkiWebView
import os
from aqt import mw
from os.path import dirname, join, basename, exists, join
from anki.hooks import addHook
import requests as req
import re
from aqt.utils import openLink


def attemptOpenLink(cmd):
    if cmd.startswith('openLink:'):
        openLink(cmd[9:])



addon_path = dirname(__file__)


def getConfig():
        return mw.addonManager.getConfig(__name__)

def saveConfiguration(newConf):
    mw.addonManager.writeConfig(__name__, newConf)

def getLatestVideos(config):
    try:
        resp = req.get("https://www.youtube.com/channel/UCQFe3x4WAgm7joN5daMm5Ew/videos")
        pattern = "\{\"videoId\"\:\"(.*?)\""
        matches = re.findall(pattern ,resp.text)
        videoIds = list(dict.fromkeys(matches))
        
        videoEmbeds = []
        count = 0
        for vid in videoIds:
            if count > 6:
                break
            count+=1
            if (count == 1):
                videoEmbeds.append("<h2>Check Out Our Latest Release:</h2>")
                videoEmbeds.append('<div class="iframe-wrapper"><div class="clickable-video-link" data-vid="'+ vid + '"></div><iframe width="640" height="360" ankiDict="https://www.youtube.com/embed/'+ vid + '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>')
            else:
                if (count == 2):
                    videoEmbeds.append("<h2>Previous Videos:</h2>")
                videoEmbeds.append('<div class="iframe-wrapper" style="display:inline-block"><div class="clickable-video-link" data-vid="'+ vid + '"></div><iframe width="320" height="180" ankiDict="https://www.youtube.com/embed/'+ vid + '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>')
        return "".join(videoEmbeds), videoIds[0]
    except:
        return False, False
    
    



def dict_message(text, parent=False):
    title = "AnkiDictionary"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(join(addon_path, 'icons', 'miso.png'))
    mb = QMessageBox(parent)
    mb.setWindowIcon(icon)
    mb.setWindowTitle(title)
    cb = QCheckBox("Don't show me the welcome screen again.")
    wv = AnkiWebView()
    wv._page._bridge.onCmd = attemptOpenLink
    wv.setFixedSize(680, 450)
    wv.page().setHtml(text)
    wide = QWidget()
    wide.setFixedSize(18,18)
    mb.layout().addWidget(wv, 0, 1)
    mb.layout().addWidget(wide, 0, 2)
    mb.layout().setColumnStretch(0, 3)
    mb.layout().addWidget(cb, 1, 1)
    b = mb.addButton(QMessageBox.Ok)
    b.setFixedSize(100, 30)
    b.setDefault(True)
    mb.exec()
    wv.deleteLater()
    if cb.isChecked():
        return True
    else:
        return False


DictionaryMessage = '''
Eyyy lmao
'''

def disableMessage(config):
    config["displayAgain"] = False
    saveConfiguration(config)
    mw.DictShouldNotShowMessage = True

def displayMessageMaybeDisableMessage(content, config):
    if miMessage(dictMessage%content):
        disableMessage(config)
     
def attemptShowDictBrandUpdateMessage():
    config = getConfig()
    shouldShow = config["displayAgain"]
    if shouldShow and not hasattr(mw, "DictShouldNotShowMessage"):
        videoIds,videoId = getLatestVideos(config)
        if videoIds:
            displayMessageMaybeDisableMessage(videoIds, config)
        else:
            displayMessageMaybeDisableMessage("", config)
    elif shouldShow and hasattr(mw, "DictShouldNotShowMessage"):
        disableMessage(config)
    else:
        mw.DictShouldNotShowMessage = True



