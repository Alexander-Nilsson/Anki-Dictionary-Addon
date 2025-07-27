# -*- coding: utf-8 -*-
# 

import aqt
from aqt.qt import *
from os.path import dirname, join
from aqt.webview import AnkiWebView


addon_path = dirname(dirname(dirname(dirname(__file__))))

def miInfo(text, parent=False, level = 'msg', day = True):
    if level == 'wrn':
        title = "Anki Dictionary Warning"
    elif level == 'not':
        title = "Anki Dictionary Notice"
    elif level == 'err':
        title = "Anki Dictionary Error"
    else:
        title = "Anki Dictionary"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(join(addon_path, 'assets', 'icons', 'miso.png'))
    mb = QMessageBox(parent)
    if not day:
        mb.setStyleSheet(" QMessageBox {background-color: #272828;}")
    mb.setText(text)
    mb.setWindowIcon(icon)
    mb.setWindowTitle(title)
    b = mb.addButton(QMessageBox.StandardButton.Ok)
    b.setFixedSize(100, 30)
    b.setDefault(True)

    return mb.exec()

def miAsk(text, parent=None, day=True, customText = False):

    msg = QMessageBox(parent)
    msg.setWindowTitle("Anki Dictionary")
    msg.setText(text)
    icon = QIcon(join(addon_path, 'assets', 'icons', 'miso.png'))
    b = msg.addButton(QMessageBox.StandardButton.Yes)
    
    b.setFixedSize(100, 30)
    b.setDefault(True)
    c = msg.addButton(QMessageBox.StandardButton.No)
    c.setFixedSize(100, 30)
    if customText:
        b.setText(customText[0])
        c.setText(customText[1])
        b.setFixedSize(120, 40)
        c.setFixedSize(120, 40)

    
    if not day:
        msg.setStyleSheet(" QMessageBox {background-color: #272828;}")
    msg.setWindowIcon(icon)
    msg.exec()
    if msg.clickedButton() == b:
        return True
    else:
        return False
