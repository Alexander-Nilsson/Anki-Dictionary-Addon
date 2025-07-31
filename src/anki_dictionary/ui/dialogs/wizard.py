# -*- coding: utf-8 -*-
"""
Consolidated wizard components for the Dictionary Addon.

This module contains:
- MiWizard: Generic wizard dialog framework
- MiWizardPage: Base wizard page class
- Message functions for brand/update messages
- Video content fetching for welcome screens
"""

import os
import re
import requests as req
from typing import Optional, Tuple, List
from os.path import dirname, join

from aqt import mw
import aqt
from aqt.qt import *
from aqt.webview import AnkiWebView
from aqt.utils import openLink
from anki.hooks import addHook

# Import config utilities
from anki_dictionary.utils.config import get_addon_config, save_addon_config


class MiWizardPage(QWidget):
    """Base class for wizard pages."""

    def __init__(self, parent=None):
        super(MiWizardPage, self).__init__(parent)

        self.wizard = None
        self.title = None
        self.subtitle = None
        self.pixmap = None

        self.back_text = "< Back"
        self.back_enabled = True
        self.back_visible = True

        self.next_text = "Next >"
        self.next_enabled = True
        self.next_visible = True

        self.cancel_text = "Cancel"
        self.cancel_enabled = True
        self.cancel_visible = True

    def on_show(self, is_next, is_back):
        """Called when page is shown."""
        pass

    def on_hide(self, is_next, is_back):
        """Called when page is hidden."""
        pass

    def on_back(self):
        """Called when back button is clicked. Return False to prevent navigation."""
        return True

    def on_next(self):
        """Called when next button is clicked. Return False to prevent navigation."""
        return True

    def on_cancel(self):
        """Called when cancel button is clicked. Return False to prevent cancellation."""
        return True

    def refresh_wizard_states(self):
        """Refresh wizard button states."""
        if self.wizard:
            self.wizard.refresh_states()


class MiWizard(QDialog):
    """Generic wizard dialog framework."""

    def __init__(self, parent=None):
        super(MiWizard, self).__init__(parent)

        self._current_page = None
        self._page_back = {}
        self._page_next = {}

        self._setup_ui()

    def _setup_ui(self):
        """Setup the wizard UI."""
        lyt = QVBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        # Main page frame
        page_frame = QFrame()
        page_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        page_frame.setBackgroundRole(QPalette.ColorRole.Base)
        page_frame.setAutoFillBackground(True)
        lyt.addWidget(page_frame)

        page_hlyt = QHBoxLayout(page_frame)

        # Pixmap layout
        pixmap_lyt = QVBoxLayout()
        page_hlyt.addLayout(pixmap_lyt)

        self._pixmap_lbl = QLabel()
        self._pixmap_lbl.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        pixmap_lyt.addWidget(self._pixmap_lbl)
        pixmap_lyt.addStretch()

        # Page content layout
        page_vlyt = QVBoxLayout()
        page_hlyt.addLayout(page_vlyt)

        self._header_lbl = QLabel()
        page_vlyt.addWidget(self._header_lbl)

        self._pages_lyt = QHBoxLayout()
        self._pages_lyt.setSizeConstraint(QLayout.SizeConstraint.SetMaximumSize)
        page_vlyt.addLayout(self._pages_lyt)

        # Button layout
        btn_lyt = QHBoxLayout()
        lyt.addLayout(btn_lyt)
        style = self.style()
        margins = (
            style.pixelMetric(QStyle.PixelMetric.PM_LayoutLeftMargin),
            style.pixelMetric(QStyle.PixelMetric.PM_LayoutTopMargin),
            style.pixelMetric(QStyle.PixelMetric.PM_LayoutRightMargin),
            style.pixelMetric(QStyle.PixelMetric.PM_LayoutBottomMargin),
        )
        btn_lyt.setContentsMargins(*margins)

        btn_lyt.addStretch()

        self._btn_back = QPushButton()
        self._btn_back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_back.clicked.connect(self.back)
        btn_lyt.addWidget(self._btn_back)

        self._btn_next = QPushButton()
        self._btn_next.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_next.clicked.connect(self.next)
        btn_lyt.addWidget(self._btn_next)

        self._btn_cancel = QPushButton()
        self._btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_cancel.clicked.connect(self.cancel)
        btn_lyt.addWidget(self._btn_cancel)

    def add_page(self, page, back_page=None, next_page=None, back_populate=True):
        """Add a page to the wizard."""
        page.wizard = self
        page.hide()
        page_lyt = page.layout()
        if page_lyt:
            page_lyt.setContentsMargins(0, 0, 0, 0)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pages_lyt.addWidget(page)
        self.set_page_back(page, back_page)
        self.set_page_next(page, next_page)

        if self._current_page is None:
            self.set_current_page(page, is_next=True)

        return page

    def set_page_back(self, page, back_page, back_populate=True):
        """Set the back page for a given page."""
        self._page_back[page] = back_page
        if back_populate and back_page:
            self.set_page_next(back_page, page, back_populate=False)

    def set_page_next(self, page, next_page, back_populate=True):
        """Set the next page for a given page."""
        self._page_next[page] = next_page
        if back_populate and next_page:
            self.set_page_back(next_page, page, back_populate=False)

    def set_current_page(self, page, is_next=False, is_back=False):
        """Set the current visible page."""
        if self._current_page:
            self._current_page.on_hide(is_next, is_back)
            self._current_page.hide()
        self._current_page = page

        page.on_show(is_next, is_back)
        self.refresh_states()
        page.show()

    def back(self):
        """Navigate to the previous page."""
        if self._current_page:
            if not self._current_page.on_back():
                return

        back_page = self._page_back.get(self._current_page)
        if back_page:
            self.set_current_page(back_page, is_back=True)

    def next(self):
        """Navigate to the next page."""
        if self._current_page:
            if not self._current_page.on_next():
                return

        next_page = self._page_next.get(self._current_page)
        if next_page:
            self.set_current_page(next_page, is_next=True)
        else:
            self.accept()

    def cancel(self):
        """Cancel the wizard."""
        if self._current_page:
            if not self._current_page.on_cancel():
                return

        if not self.on_cancel():
            return

        self.reject()

    def on_cancel(self):
        """Called when wizard is cancelled. Return False to prevent cancellation."""
        return True

    def refresh_states(self):
        """Refresh the wizard button states and header."""
        if self._current_page:
            header_text = ""

            title = self._current_page.title
            if title:
                header_text += "<h2>%s</h2>" % title

            subtitle = self._current_page.subtitle
            if subtitle:
                header_text += "<h4>%s</h4>" % subtitle

            if header_text:
                self._header_lbl.setText(header_text)
                self._header_lbl.setVisible(True)
            else:
                self._header_lbl.clear()
                self._header_lbl.setVisible(False)

            pixmap = self._current_page.pixmap
            if pixmap:
                self._pixmap_lbl.setPixmap(pixmap)
            else:
                self._pixmap_lbl.clear()
            self._pixmap_lbl.setVisible(bool(pixmap))

            self._btn_back.setText(self._current_page.back_text)
            self._btn_back.setEnabled(self._current_page.back_enabled)
            self._btn_back.setVisible(self._current_page.back_visible)
            self._btn_next.setText(self._current_page.next_text)
            self._btn_next.setEnabled(self._current_page.next_enabled)
            self._btn_next.setVisible(self._current_page.next_visible)
            self._btn_cancel.setText(self._current_page.cancel_text)
            self._btn_cancel.setEnabled(self._current_page.cancel_enabled)
            self._btn_cancel.setVisible(self._current_page.cancel_visible)

    def closeEvent(self, e):
        """Handle close event."""
        self.cancel()
        e.ignore()


# Message and video functions
def attemptOpenLink(cmd):
    """Attempt to open a link."""
    if cmd.startswith("openLink:"):
        openLink(cmd[9:])


def getConfig():
    """Get addon configuration."""
    return get_addon_config()


def saveConfiguration(newConf):
    """Save addon configuration."""
    save_addon_config(newConf)


def getLatestVideos(config) -> Tuple[Optional[str], Optional[str]]:
    """Fetch latest videos from YouTube channel."""
    try:
        resp = req.get(
            "https://www.youtube.com/channel/UCQFe3x4WAgm7joN5daMm5Ew/videos"
        )
        pattern = r'\{"videoId":"(.*?)"'
        matches = re.findall(pattern, resp.text)
        videoIds = list(dict.fromkeys(matches))

        videoEmbeds = []
        count = 0
        for vid in videoIds:
            if count > 6:
                break
            count += 1
            if count == 1:
                videoEmbeds.append("<h2>Check Out Our Latest Release:</h2>")
                videoEmbeds.append(
                    f'<div class="iframe-wrapper"><div class="clickable-video-link" data-vid="{vid}"></div><iframe width="640" height="360" src="https://www.youtube.com/embed/{vid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                )
            else:
                if count == 2:
                    videoEmbeds.append("<h2>Previous Videos:</h2>")
                videoEmbeds.append(
                    f'<div class="iframe-wrapper" style="display:inline-block"><div class="clickable-video-link" data-vid="{vid}"></div><iframe width="320" height="180" src="https://www.youtube.com/embed/{vid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                )
        return "".join(videoEmbeds), videoIds[0] if videoIds else None
    except Exception:
        return None, None


def miMessage(text, parent=False):
    """Show Migaku-branded message dialog."""
    title = "Migaku"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw

    # Get addon path
    addon_path = dirname(dirname(dirname(dirname(__file__))))
    icon = QIcon(join(addon_path, "assets", "icons", "dictionary.png"))

    mb = QMessageBox(parent)
    mb.setWindowIcon(icon)
    mb.setWindowTitle(title)
    cb = QCheckBox("Don't show me the welcome screen again.")
    wv = AnkiWebView()

    # Set up bridge for handling link clicks
    # Use a robust approach that works across Anki versions
    try:
        # Modern Anki bridge setup
        if hasattr(wv, "set_bridge_command"):
            # Newest Anki versions
            wv.set_bridge_command(attemptOpenLink, "openLink")
        elif hasattr(wv, "bridge") and hasattr(wv.bridge, "onCmd"):
            # Modern approach
            wv.bridge.onCmd = attemptOpenLink
        elif hasattr(wv.page(), "bridge") and hasattr(wv.page().bridge, "onCmd"):
            # Alternative modern approach
            wv.page().bridge.onCmd = attemptOpenLink
        elif (
            hasattr(wv, "_page")
            and hasattr(wv._page, "_bridge")
            and hasattr(wv._page._bridge, "onCmd")
        ):
            # Legacy approach (keep as fallback)
            wv._page._bridge.onCmd = attemptOpenLink
        else:
            # Last resort - try setting up a simple handler
            pass  # Will work without clickable links
    except (AttributeError, TypeError):
        # If bridge setup fails, continue without it
        # The dialog will still work, just without clickable links
        pass

    wv.setFixedSize(680, 450)
    wv.page().setHtml(text)
    wide = QWidget()
    wide.setFixedSize(18, 18)
    mb.layout().addWidget(wv, 0, 1)
    mb.layout().addWidget(wide, 0, 2)
    mb.layout().setColumnStretch(0, 3)
    mb.layout().addWidget(cb, 1, 1)
    b = mb.addButton(QMessageBox.StandardButton.Ok)
    b.setFixedSize(100, 30)
    b.setDefault(True)
    mb.exec()
    wv.deleteLater()
    return cb.isChecked()


# HTML template for Migaku message
migakuMessage = """
<style>
    body{
    margin:0px;
    padding:0px;
    background-color: white !important;
    }
    h3 {
        margin-top:5px;
        margin-left:15px;
        font-weight: 600;
        font-family: NeueHaas, input mono, sans-serif;
        color: #404040;
    }
    div {
        margin-left:15px;
        line-height: 1.5;
        font-family: Helmet,Freesans,Helvetica,Arial,sans-serif;
        color: #404040;
    }

    span{
        margin-left:15px;
        color:gray;
        font-size:13;
        font-family: Helmet,Freesans,Helvetica,Arial,sans-serif;
    }

    .iframe-wrapper{
        position:relative;
        margin-left:0px;
        line-height: 1;
    }

    .clickable-video-link{
        position:absolute;
        z-index:10;
        width:100%%;
        top:0px;
        left:0px;
        height:20%%;
        margin-left:0px;
        line-height: 1;
        cursor:pointer;
    }
</style>
<body>
<h3><b>Thanks for using the Anki Dictionary Addon!</b></h3>
<div class="center-div">
    This addon helps you learn languages more efficiently by providing instant dictionary lookups within Anki.<br>
    For more information, please visit the project repository on <a href="https://github.com/migaku-official/Anki-Dictionary-Addon">GitHub</a>!
</div>
<div>
%s
</div>
<script>
        const vids = document.getElementsByClassName("clickable-video-link");
        for (var i = 0; i < vids.length; i++) {
            vids[i].addEventListener("click", function (e) {
                const vidId = e.target.dataset.vid;
                pycmd("openLink:https://www.youtube.com/watch?v=" + vidId);
            });
        }
</script>
</body>
"""


def disableMessage(config):
    """Disable welcome message."""
    # The config utility ensures config is never None (returns empty dict)
    config["displayAgain"] = False
    saveConfiguration(config)
    mw.DictShouldNotShowMessage = True


def displayMessageMaybeDisableMessage(content, config):
    """Display message and maybe disable it."""
    if miMessage(migakuMessage % content):
        disableMessage(config)


def attemptShowDictBrandUpdateMessage():
    """Attempt to show Dictionary addon update message."""
    config = getConfig()

    # The config utility returns empty dict if None, so we can safely use get()
    shouldShow = config.get("displayAgain", False)

    if shouldShow and not hasattr(mw, "DictShouldNotShowMessage"):
        videoIds, videoId = getLatestVideos(config)
        if videoIds:
            displayMessageMaybeDisableMessage(videoIds, config)
        else:
            displayMessageMaybeDisableMessage("", config)
    elif shouldShow and hasattr(mw, "DictShouldNotShowMessage"):
        disableMessage(config)
    else:
        mw.DictShouldNotShowMessage = True


# Hook to show message on profile load - DISABLED to remove welcome screen
# addHook("profileLoaded", attemptShowDictBrandUpdateMessage)
