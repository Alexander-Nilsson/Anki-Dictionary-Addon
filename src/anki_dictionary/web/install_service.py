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
import time
import zipfile
from collections.abc import Callable
from typing import Any

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
            names = [
                n
                for n in z.namelist()
                if n.endswith(".json")
                and "__MACOSX" not in n.split("/")
                and not n.rsplit("/", 1)[-1].startswith("._")
            ]
            banks = [
                n for n in names if n.rsplit("/", 1)[-1].startswith("term_meta_bank_")
            ]
            if banks:
                ranks: dict[str, float] = {}
                metadata = next(
                    (n for n in names if n.rsplit("/", 1)[-1] == "index.json"), None
                )
                header = (
                    json.loads(z.read(metadata).decode("utf-8-sig")) if metadata else {}
                )
                occurrence = header.get("frequencyMode") == "occurrence-based"
                for name in banks:
                    for row in json.loads(z.read(name).decode("utf-8-sig")):
                        if (
                            not isinstance(row, list)
                            or len(row) < 3
                            or row[1] != "freq"
                        ):
                            continue
                        value = row[2]
                        if isinstance(value, dict):
                            value = value.get("frequency", value.get("value"))
                        if isinstance(value, dict):
                            value = value.get("value")
                        try:
                            value = float(str(value).replace(",", ""))
                        except (ValueError, TypeError):
                            continue
                        term = str(row[0])
                        if term not in ranks or (
                            value > ranks[term] if occurrence else value < ranks[term]
                        ):
                            ranks[term] = value
                if not ranks:
                    raise ValueError("frequency banks contain no usable word data")
                if occurrence:
                    ranks = {
                        term: rank
                        for rank, term in enumerate(
                            sorted(ranks, key=lambda term: ranks[term], reverse=True), 1
                        )
                    }
                log(f" Read {len(ranks):,} words from {len(banks)} frequency banks.")
                return json.dumps({"index": ranks}, ensure_ascii=False).encode("utf-8")
            # Ignore the archive header; combine every data bank.
            files = [n for n in names if n.rsplit("/", 1)[-1] != "index.json"]
            if len(files) == 1:
                return z.read(files[0])
            if files:
                merged = []
                for name in files:
                    rows = json.loads(z.read(name).decode("utf-8-sig"))
                    if not isinstance(rows, list):
                        raise ValueError("multiple word-list files must contain lists")
                    merged.extend(rows)
                return json.dumps(merged, ensure_ascii=False).encode("utf-8")
            raise ValueError("archive contains no word-data files")
    except Exception as e:
        log(f" ERROR: Failed to unzip word data: {e}")
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
    status = pyqtSignal(str)
    done = pyqtSignal(bool)  # True when nothing was cancelled

    def __init__(self, selection: dict[str, Any]) -> None:
        super().__init__()
        self.selection = {k: v for k, v in selection.items() if k in _WORKER_KEYS}
        self.cancel_requested = False
        self.installed = 0
        self.skipped = 0
        self.failed = 0
        self._db: Any = None
        self._total_items = 1
        self._completed_items = 0
        self._last_percent = -1
        self._last_update = 0.0
        self._item_name = ""

    def _log(self, line: str) -> None:
        logger.info("%s", line)
        self.log_line.emit(line)

    def _update_progress(self, fraction: float, message: str) -> None:
        percent = min(
            99,
            int(100 * (self._completed_items + fraction) / max(self._total_items, 1)),
        )
        if percent > self._last_percent:
            self._last_percent = percent
            self.progress.emit(percent)
        self.status.emit(message)

    def _finish_item(self) -> None:
        self._completed_items += 1
        self._update_progress(
            0, f"Processed {self._completed_items} of {self._total_items} items"
        )

    # ── helpers ────────────────────────────────────────────

    def _server_root(self) -> str:
        return webConfig.normalize_url(
            str(self.selection.get("server") or webConfig.DEFAULT_SERVER)
        )

    def construct_url(self, url: str) -> str:
        if url.startswith("http"):
            return url
        return self._server_root() + "/" + url.lstrip("/")

    def fetch_data(self, client: HttpClient, url: str):
        """Fetch data from URL with standard quoting."""
        import urllib.parse

        parts = url.split("://")
        if len(parts) > 1:
            quoted_url = (
                parts[0] + "://" + urllib.parse.quote(parts[1], safe="/%:@?=&+")
            )
        else:
            quoted_url = urllib.parse.quote(url, safe="/%:@?=&+")

        with prefer_ipv4():
            return client.session.get(quoted_url, timeout=60, stream=True)  # ty:ignore[unresolved-attribute]

    def _download(self, client: HttpClient, url: str, name: str) -> bytes | None:
        self._item_name = name
        self._log(f" Downloading {url}...")
        # Retry transient HTTP/stream errors, closing every response.
        for attempt in range(3):
            if self.cancel_requested:
                return None
            resp = None
            received = 0
            try:
                self._update_progress(0, f"Downloading {name} — connecting…")
                resp = self.fetch_data(client, url)
                if resp.status_code != 200:
                    message = f"HTTP {resp.status_code} for {name}: {url}"
                    if resp.status_code not in (408, 429, 500, 502, 503, 504):
                        self._log(f" ERROR: {message}")
                        return None
                    raise OSError(message)
                try:
                    total = int(resp.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    total = 0
                chunks = []
                for chunk in resp.iter_content(chunk_size=65536):
                    if self.cancel_requested:
                        return None
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if now - self._last_update >= 0.2:
                        self._last_update = now
                        size = f"{received / 1048576:.1f} MB"
                        if total:
                            size += f" / {total / 1048576:.1f} MB"
                        self._update_progress(
                            0.65 * min(received / total, 1) if total else 0,
                            f"Downloading {name} — {size}",
                        )
                data = b"".join(chunks)
                if not data:
                    raise OSError("server returned an empty file")
                if data.startswith(b"version https://git-lfs"):
                    self._log(
                        f" ERROR: {name} is a Git LFS pointer instead of file contents: {url}"
                    )
                    return None
                self._update_progress(
                    0.65, f"Downloaded {name} — {received / 1048576:.1f} MB"
                )
                return data
            except Exception as exc:
                if attempt == 2:
                    self._log(
                        f" ERROR: Download failed for {name} after 3 attempts ({exc}): {url}"
                    )
                else:
                    self._log(
                        f" Retrying {name} after interrupted download ({exc}); attempt {attempt + 2}/3."
                    )
            finally:
                if resp is not None:
                    resp.close()
        return None

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
            self._update_progress(0, f"Preparing {wl_name}")
            type_label = "frequency list" if wl_type == "frequency" else "word list"
            self._log(f"Installing {lang} {wl_name} ({type_label})...")
            data = self._download(
                client, self.construct_url(str(wl_info.get("url", ""))), wl_name
            )
            if data is None:
                if not self.cancel_requested:
                    self.failed += 1
                self._finish_item()
                continue
            data = extract_zipped_json(data, self._log)
            validated = sanitize_json_bytes(data, wl_name, self._log)
            if validated is None:
                self.failed += 1
                self._finish_item()
                continue
            slug = "".join(
                c for c in wl_name.lower().replace(" ", "_") if c.isalnum() or c == "_"
            )
            type_tag = ".freq" if wl_type == "frequency" else ".level"
            filename = f"{lang_part}_{slug}{type_tag}.json"
            with open(os.path.join(wl_dir, filename), "wb") as f:
                f.write(validated)
            self.installed += 1
            self._log(f" Installed as {filename}")
            self._finish_item()

    def _install_conjugation(
        self, client: HttpClient, lang: str, conj: dict[str, Any]
    ) -> None:
        conj_dir = get_conjugation_dir()
        os.makedirs(conj_dir, exist_ok=True)
        self._log(f"Installing {lang} conjugation data...")
        conj_url = str(conj.get("url") or conj.get("conjugation_url") or "").strip()
        if not conj_url:
            self.failed += 1
            self._log(" ERROR: Conjugation data has no URL.")
            self._finish_item()
            return
        data = self._download(client, self.construct_url(conj_url), "conjugation")
        if data is None:
            if not self.cancel_requested:
                self.failed += 1
            self._finish_item()
            return
        dst_path = os.path.join(conj_dir, f"{lang}.json")
        with open(dst_path, "wb") as f:
            f.write(data)
        self.installed += 1
        self._finish_item()

    def _install_dictionaries(
        self,
        client: HttpClient,
        lang: str,
        dictionaries: list[dict[str, Any]],
        total: int,
    ) -> None:
        from ..ui.dialogs.dict_import import importDict

        for d in dictionaries:
            if self.cancel_requested:
                return
            dname = str(d.get("name") or "dictionary")
            exists = self._db.dictExists(dname, lang)
            if exists:
                table = self._db.formatDictName(
                    self._db.getLangId(lang), self._db.normalize_dict_name(dname)
                )
                quoted = self._db._quote_identifier(table)
                # A crashed import can leave its metadata and an empty table.
                exists = (
                    self._db._get_connection()
                    .execute(f"SELECT 1 FROM {quoted} LIMIT 1")
                    .fetchone()
                    is not None
                )
            if exists:
                self._log(f"Skipping {dname} (already installed).")
                self.skipped += 1
                self._finish_item()
                continue

            self._log(f"Installing {dname}...")
            data = self._download(
                client, self.construct_url(str(d.get("url", ""))), dname
            )
            if data is None:
                if not self.cancel_requested:
                    self.failed += 1
                self._finish_item()
                continue

            self._log(" Importing...")
            try:
                importDict(
                    lang,
                    io.BytesIO(data),
                    dname,
                    overwrite=True,
                    db=self._db,
                    progress=lambda fraction, message, name=dname: (
                        self._update_progress(
                            0.65 + 0.35 * fraction, f"Importing {name} — {message}"
                        )
                    ),
                )
                self.installed += 1
                self._log(f" Installed {dname}.")
            except Exception as e:  # noqa: BLE001 - report and continue
                self.failed += 1
                logger.exception("Dictionary import failed: %s", dname)
                self._log(f" ERROR: {str(e)}")
            self._finish_item()

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
        self._total_items = total_dicts + sum(
            (
                len(l.get("frequency_lists") or []) + len(l.get("word_lists") or [])
                if install_wl
                else 0
            )
            + (1 if install_conj and l.get("conjugation_url") else 0)
            for l in languages
        )
        self._log(
            f"Installing {total_dicts} dictionaries and {self._total_items - total_dicts} data files..."
        )
        self._update_progress(0, f"Preparing {self._total_items} items")

        client = HttpClient()
        try:
            if install_dicts:
                from ..core.database import DictDB

                # SQLite connections and cursors must belong to this worker,
                # never to the UI that can query while an import is running.
                self._db = DictDB()
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
            self.failed += 1
            self._log(f" ERROR: {e}")
        finally:
            if self._db is not None:
                self._db.closeConnection()
                self._db = None

        if self.cancel_requested:
            self._log("Cancelled.")
            self.done.emit(False)
            return
        self.progress.emit(100)
        self.status.emit("Installation finished")
        self._log(
            f"Finished: {self.installed} installed, {self.skipped} skipped, "
            f"{self.failed} failed."
        )
        self.done.emit(self.failed == 0)
