"""
Release notes dialog for the Anki Dictionary Addon.

Shows a popup with the latest release notes from GitHub when a new version
is detected. Includes a checkbox to suppress future popups.
"""

import re

import requests
from aqt.qt import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    Qt,
    QTextBrowser,
    QThread,
    QVBoxLayout,
    pyqtSignal,
)

from ...utils.config import get_addon_config, save_addon_config
from ...utils.logger import get_logger

log = get_logger("release_notes")

GITHUB_REPO = "Alexander-Nilsson/Anki-Dictionary-Addon"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 5


def _markdown_to_html(md: str) -> str:
    """Convert GitHub-flavored markdown release body to simple HTML."""
    html = md
    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Links
    html = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        html,
    )
    # Unordered list items
    html = re.sub(r"^\* (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    # Wrap consecutive <li> in <ul>
    html = re.sub(
        r"((?:<li>.*</li>\n?)+)",
        r"<ul>\1</ul>",
        html,
    )
    # Line breaks → <br> for remaining newlines
    html = html.replace("\n", "<br>")
    return html


class _ReleaseFetcher(QThread):
    """Background thread that fetches release info from GitHub."""

    finished = pyqtSignal(dict | None)

    def run(self) -> None:
        try:
            resp = requests.get(GITHUB_API_URL, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            self.finished.emit(
                {
                    "tag_name": data.get("tag_name", ""),
                    "name": data.get("name", ""),
                    "body": data.get("body", ""),
                }
            )
        except Exception as e:
            log.warning(f"Failed to fetch release notes: {e}")
            self.finished.emit(None)


class ReleaseNotesDialog(QDialog):
    """Popup dialog displaying latest release notes."""

    def __init__(self, version: str, parent=None) -> None:
        super().__init__(parent)
        self._version = version
        self._dont_show_again = False
        self._fetcher: _ReleaseFetcher | None = None
        self._setup_ui()
        self._start_fetch()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"Anki Dictionary — v{self._version}")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"<h2>What's New in v{self._version}</h2>")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Release notes browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setPlaceholderText("Loading release notes...")
        self._browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._browser)

        # Checkbox + Close button row
        bottom_layout = QHBoxLayout()

        self._checkbox = QCheckBox("Don't show release notes again")
        self._checkbox.stateChanged.connect(self._on_checkbox_changed)
        bottom_layout.addWidget(self._checkbox)

        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self._on_close)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

    def _start_fetch(self) -> None:
        self._fetcher = _ReleaseFetcher()
        self._fetcher.finished.connect(self._on_fetch_done)
        self._fetcher.start()

    def _on_fetch_done(self, data: dict | None) -> None:
        if data is None:
            self._browser.setHtml(
                "<p style='color:gray'>Could not load release notes.</p>"
            )
            return

        tag = data["tag_name"].lstrip("v")
        body_html = _markdown_to_html(data["body"])

        self._browser.setHtml(
            f"<h3>{data['name']}</h3>"
            if data["name"]
            else f"<div style='font-size:12px;'>{body_html}</div>"
        )

        # Update title if tag differs from bundled version
        if tag and tag != self._version:
            self.setWindowTitle(f"Anki Dictionary — v{tag}")

    def _on_checkbox_changed(self, state: int) -> None:
        self._dont_show_again = state == Qt.CheckState.Checked.value

    def _on_close(self) -> None:
        config = get_addon_config()
        if self._dont_show_again:
            config["hide_release_notes"] = True
        config["last_seen_version"] = self._version
        save_addon_config(config)
        self.accept()


def check_and_show_release_notes(mw) -> None:
    """Check if release notes should be shown and display the dialog.

    Called on profileLoaded. Compares the bundled version against the
    last-seen version stored in config and respects the user's opt-out.
    """
    from ... import __version__

    config = get_addon_config()

    if config.get("hide_release_notes", False):
        return

    last_seen = config.get("last_seen_version", "")
    if last_seen == __version__:
        return

    dialog = ReleaseNotesDialog(__version__, parent=mw)
    dialog.exec()
