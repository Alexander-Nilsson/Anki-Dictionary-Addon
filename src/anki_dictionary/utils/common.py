# -*- coding: utf-8 -*-
#

import aqt
from aqt.qt import *
import os
from os.path import dirname, join
import contextlib
import urllib3.util.connection as connection
from aqt.webview import AnkiWebView
from .paths import get_addon_root, get_icons_dir


@contextlib.contextmanager
def prefer_ipv4():
    """Context manager to temporarily prefer IPv4 for network operations by disabling IPv6 in urllib3."""
    old_has_ipv6 = connection.HAS_IPV6
    connection.HAS_IPV6 = False
    try:
        yield
    finally:
        connection.HAS_IPV6 = old_has_ipv6


def miInfo(text, parent=False, level="msg", day=True):
    if level == "wrn":
        title = "Anki Dictionary Warning"
    elif level == "not":
        title = "Anki Dictionary Notice"
    elif level == "err":
        title = "Anki Dictionary Error"
    else:
        title = "Anki Dictionary"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(os.path.join(get_icons_dir(), "anki.png"))
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


def miAsk(text, parent=None, day=True, customText=False):

    msg = QMessageBox(parent)
    msg.setWindowTitle("Anki Dictionary")
    msg.setText(text)
    icon = QIcon(os.path.join(get_icons_dir(), "anki.png"))
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


def getTarget(name):
    """Get target window type."""
    if name == "AddCards":
        return "Add"
    elif name == "EditCurrent" or name == "DictEditCurrent":
        return "Edit"
    elif name == "Browser":
        return name
    return name


def gt(obj):
    """Get type name of object."""
    return type(obj).__name__
