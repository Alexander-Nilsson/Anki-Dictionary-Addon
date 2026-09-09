"""Headless web-install workers for the settings window's install modals.

The dictionary server exposes an index (``index.json``) describing per-language
dictionaries, frequency/word lists and conjugation data. The settings web UI
browses that index and ships a selection back over the bridge; this module
downloads and installs it on a background ``QThread``, streaming log lines and
progress back to the page (``SETTINGS.setWebInstall``) so the modal can show
live progress.

Mirrors the flow of the old ``DictionaryWebInstallWizard``/``FreqConjWebWindow``
(Qt dialogs) they replace.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from collections.abc import Callable
from typing import Any

import aqt
from anki.httpclient import HttpClient
from aqt.qt import QThread, pyqtSignal

from ..utils.common import prefer_ipv4
from ..utils.logger import get_logger
from ..utils.paths import get_conjugation_dir, get_word_lists_dir
from . import config as webConfig

logger = get_logger(__name__.split(".")[-1])

# Known metadata-only keys in format-3 word list headers (no actual word data).
_METADATA_ONLY_KEYS = {
    "title",
    "revision",
    "format",
    "url",
    "description",
    "author",
    "attribution",
    "frequencyMode",
    "readingDictionaryType",
}

# Payload keys the worker understands; everything else is ignored.
_WORKER_KEYS = frozenset(
    {
        "server",
        "install_dictionaries",
        "install_word_lists",
        "install_conjugation",
        "languages",
    }
)


def sanitize_json_bytes(
    raw: bytes, name: str, log: Callable[[str], None]
) -> bytes | None:
    """Validate downloaded word-list data before saving.

    Returns the raw bytes if valid, or None to skip saving (after logging a
    descriptive error). Rejects Git LFS pointer files, unparseable JSON and
    metadata-only format-3 envelopes (``{"title":...,"format":3,...}`` with no
    actual term→rank/level data).
    """
    if raw.startswith(b"version https://git-lfs"):
        log(
            f" ERROR: {name} is a Git LFS pointer (not the actual word data). "
            "Skipping. Try a different word list."
        )
        return None

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        log(f" ERROR: {name} is not valid UTF-8 text. Skipping.")
        return None

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        log(f" ERROR: {name} is not valid JSON. Skipping.")
        return None

    if isinstance(parsed, dict):
        word_keys = [k for k in parsed if k not in _METADATA_ONLY_KEYS]
        if len(parsed) >= 3 and len(word_keys) == 0:
            log(
                f" ERROR: {name} is a metadata-only header (keys: "
                f"{list(parsed.keys())}). No word data found. Skipping."
            )
            return None

    return raw


def extract_zipped_json(data: bytes, log: Callable[[str], None]) -> bytes:
    """If `data` is a ZIP archive, return its first .json entry; else data."""
    if data[:4] != b"PK\x03\x04":
        return data
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            json_files = [n for n in z.namelist() if n.endswith(".json")]
            if json_files:
                return z.read(json_files[0])
    except Exception as e:
        log(f" ERROR: Failed to unzip: {str(e)}")
    return data


class WebInstallWorker(QThread):
    """Download + install a selection made in the settings install modal.

    Selection payload (the web UI builds it from the fetched index)::

        {
          "server": "https://…",
          "install_dictionaries": true,
          "install_word_lists": true,
          "install_conjugation": true,
          "languages": [
            { "name": "Japanese",
              "dictionaries": [{"name": "JMdict", "url": "/ja/JMdict.zip"}],
              "frequency_lists": [{"name": "…", "url": "/ja/….json"}],
              "word_lists": [{"name": "…", "url": "/ja/….json"}],
              "conjugation_url": "/ja/conjugation.json" }
          ]
        }

    Only known keys are read, so the raw index language objects may be passed
    through as-is.
    """

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int)
    done = pyqtSignal(bool)  # True when nothing was cancelled

    def __init__(self, selection: dict[str, Any]) -> None:
        super().__init__()
        self.selection = {k: v for k, v in selection.items() if k in _WORKER_KEYS}
        self.cancel_requested = False

    # ── helpers ────────────────────────────────────────────

    def _server_root(self) -> str:
        return webConfig.normalize_url(
            str(self.selection.get("server") or webConfig.DEFAULT_SERVER)
        )

    def construct_url(self, url: str) -> str:
        if url.startswith("http"):
            return url
        return self._server_root() + url

    def fetch_data(self, client: HttpClient, url: str):
        """Fetch data from URL with standard quoting."""
        import urllib.parse

        parts = url.split("://")
        if len(parts) > 1:
            quoted_url = parts[0] + "://" + urllib.parse.quote(parts[1], safe="/")
        else:
            quoted_url = urllib.parse.quote(url, safe="/")

        with prefer_ipv4():
            return client.session.get(quoted_url, timeout=60, stream=True)  # ty:ignore[unresolved-attribute]

    def _download(self, client: HttpClient, url: str, name: str) -> bytes | None:
        self.log_line.emit(f" Downloading {url}...")
        try:
            resp = self.fetch_data(client, url)
        except Exception as e:
            self.log_line.emit(f" ERROR: Download failed ({e}).")
            return None
        if resp.status_code != 200:
            self.log_line.emit(f" ERROR: Download failed ({resp.status_code}).")
            return None
        chunks = []
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                chunks.append(chunk)
        data = b"".join(chunks)
        if not data:
            self.log_line.emit(f" ERROR: {name} downloaded an empty file. Skipping.")
            return None
        return data

    # ── installers ─────────────────────────────────────────

    def _install_word_lists(
        self, client: HttpClient, lang: str, sources: list[tuple[dict[str, Any], str]]
    ) -> None:
        wl_dir = get_word_lists_dir()
        os.makedirs(wl_dir, exist_ok=True)
        lang_part = lang.replace(" ", "_")
        for wl_info, wl_type in sources:
            if self.cancel_requested:
                return
            wl_name = str(wl_info.get("name") or "word list")
            type_label = "frequency list" if wl_type == "frequency" else "word list"
            self.log_line.emit(f"Installing {lang} {wl_name} ({type_label})...")
            data = self._download(
                client, self.construct_url(str(wl_info.get("url", ""))), wl_name
            )
            if data is None:
                continue
            data = extract_zipped_json(data, self.log_line.emit)
            validated = sanitize_json_bytes(data, wl_name, self.log_line.emit)
            if validated is None:
                continue
            slug = "".join(
                c for c in wl_name.lower().replace(" ", "_") if c.isalnum() or c == "_"
            )
            type_tag = ".freq" if wl_type == "frequency" else ".level"
            filename = f"{lang_part}_{slug}{type_tag}.json"
            with open(os.path.join(wl_dir, filename), "wb") as f:
                f.write(validated)
            self.log_line.emit(f" Installed as {filename}")

    def _install_conjugation(
        self, client: HttpClient, lang: str, conj: dict[str, Any]
    ) -> None:
        conj_dir = get_conjugation_dir()
        os.makedirs(conj_dir, exist_ok=True)
        self.log_line.emit(f"Installing {lang} conjugation data...")
        data = self._download(
            client, self.construct_url(str(conj.get("url", ""))), "conjugation"
        )
        if data is None:
            return
        dst_path = os.path.join(conj_dir, f"{lang}.json")
        with open(dst_path, "wb") as f:
            f.write(data)

    def _install_dictionaries(
        self,
        client: HttpClient,
        lang: str,
        dictionaries: list[dict[str, Any]],
        total: int,
    ) -> None:
        from ..ui.dialogs.dict_import import importDict

        done = 0
        for d in dictionaries:
            if self.cancel_requested:
                return
            dname = str(d.get("name") or "dictionary")
            if aqt.mw.miDictDB.dictExists(dname, lang):  # ty:ignore[unresolved-attribute]
                self.log_line.emit(f"Skipping {dname} (already installed).")
                done += 1
                self.progress.emit(round(done * 100 / max(total, 1)))
                continue

            self.log_line.emit(f"Installing {dname}...")
            data = self._download(
                client, self.construct_url(str(d.get("url", ""))), dname
            )
            if data is None:
                done += 1
                self.progress.emit(round(done * 100 / max(total, 1)))
                continue

            self.log_line.emit(" Importing...")
            try:
                importDict(lang, io.BytesIO(data), dname, overwrite=True)
                self.log_line.emit(f" Installed {dname}.")
            except ValueError as e:
                self.log_line.emit(f" ERROR: {str(e)}")
            done += 1
            self.progress.emit(round(done * 100 / max(total, 1)))

    # ── thread body ────────────────────────────────────────

    def run(self) -> None:
        languages = self.selection.get("languages")
        if not isinstance(languages, list):
            self.done.emit(True)
            return
        languages = [l for l in languages if isinstance(l, dict)]

        install_dicts = bool(self.selection.get("install_dictionaries", True))
        install_wl = bool(self.selection.get("install_word_lists", True))
        install_conj = bool(self.selection.get("install_conjugation", False))

        total_dicts = sum(
            len(l.get("dictionaries") or []) for l in languages if install_dicts
        )
        self.log_line.emit(f"Installing {total_dicts} dictionaries...")

        client = HttpClient()
        try:
            for l in languages:
                if self.cancel_requested:
                    self.done.emit(False)
                    return
                lang = str(l.get("name") or l.get("name_en") or "").strip()
                if not lang:
                    continue

                if install_wl:
                    sources: list[tuple[dict[str, Any], str]] = [
                        (fl, "frequency") for fl in (l.get("frequency_lists") or [])
                    ]
                    sources += [(wl, "level") for wl in (l.get("word_lists") or [])]
                    self._install_word_lists(client, lang, sources)

                if install_conj and l.get("conjugation_url"):
                    self._install_conjugation(client, lang, l)

                if install_dicts:
                    dicts = l.get("dictionaries") or []
                    if dicts:
                        self._install_dictionaries(client, lang, dicts, total_dicts)
        except Exception as e:  # noqa: BLE001 - surface any crash as a log line
            logger.exception("Web install failed")
            self.log_line.emit(f" ERROR: {e}")

        if self.cancel_requested:
            self.log_line.emit("Cancelled.")
            self.done.emit(False)
            return
        self.progress.emit(100)
        self.log_line.emit("All done.")
        self.done.emit(True)
