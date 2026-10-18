"""Browser-driven definition export.

The Card Browser's Edit menu exposes "Export Definitions": it reads a word
from one field of every selected note, looks it up in up to three installed
dictionaries, and writes the definitions into another field.
"""

from __future__ import annotations

import re
from typing import Any

from aqt.qt import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QProgressDialog,
    QSpinBox,
    Qt,
    QVBoxLayout,
)

from ..utils.common import miInfo
from ..utils.config import get_addon_config
from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

MODE_ADD = "Add"
MODE_OVERWRITE = "Overwrite"
MODE_IF_EMPTY = "If Empty"
MODES = (MODE_ADD, MODE_OVERWRITE, MODE_IF_EMPTY)


def strip_field_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\[[^\]]+?\]", "", text)
    return text.strip()


def apply_output_mode(current: str, new: str, mode: str) -> str:
    """Return the field value after writing ``new`` according to ``mode``."""
    if not new:
        return current
    if mode == MODE_OVERWRITE:
        return new
    if mode == MODE_IF_EMPTY:
        return current if current else new
    return current + "<br><br>" + new if current else new


def _term_header(
    entry: dict[str, Any], headers: list[str], front: str, back: str
) -> str:
    term = str(entry.get("term", "") or "")
    altterm = str(entry.get("altterm", "") or "")
    pronunciation = str(entry.get("pronunciation", "") or "")
    if altterm == term:
        altterm = ""
    if pronunciation == term:
        pronunciation = ""

    parts: list[str] = []
    for header in headers or []:
        if header == "term" and term:
            parts.append(f"{front}{term}{back}")
        elif header == "altterm" and altterm:
            parts.append(f"{front}{altterm}{back}")
        elif header == "pronunciation" and pronunciation:
            parts.append(pronunciation)
    header_text = " ".join(parts)
    header_text += str(entry.get("starCount", "") or "")
    return header_text


def format_definitions(
    entries: list[dict[str, Any]],
    term_headers: list[str] | None,
    duplicate_header: int | None,
    front: str = "【",
    back: str = "】",
) -> str:
    """Render mass-export entries the same way the dictionary list does."""
    definitions = []
    for entry in entries or []:
        definition = str(entry.get("definition", "") or "")
        if duplicate_header:
            stars = str(entry.get("starCount", "") or "")
            if "】" in definition:
                definition = definition.replace("】", "】" + stars + " ", 1)
            elif "<br>" in definition:
                definition = definition.replace("<br>", stars + "<br>", 1)
            else:
                definition = stars + "<br>" + definition
        else:
            header = _term_header(entry, term_headers or [], front, back)
            definition = header + "<br>" + definition if header else definition
        definitions.append(definition)
    joined = "<br><br>".join(part for part in definitions if part)
    return re.sub(r"(<br>\s*){3,}", "<br><br>", joined)


def export_definitions(
    mw,
    note_ids: list[int],
    input_field: str,
    output_field: str,
    mode: str,
    dictionary_tables: list[str],
    dictionary_names: list[str],
    max_per_dict: int,
    progress=None,
) -> int:
    """Write definitions into ``output_field`` for every selected note.

    Returns the number of notes whose field changed.
    """
    db = mw.miDictDB
    config = get_addon_config()
    front = config.get("frontBracket", "【")
    back = config.get("backBracket", "】")
    updated = 0

    for index, note_id in enumerate(note_ids):
        if progress is not None:
            if progress.wasCanceled():
                break
            progress.setValue(index)

        note = mw.col.get_note(note_id)
        fields = list(note.keys())
        if input_field not in fields or output_field not in fields:
            continue
        term = strip_field_html(note[input_field])
        if not term:
            continue

        parts = []
        for table, name in zip(dictionary_tables, dictionary_names, strict=False):
            if not table or table == "None":
                continue
            try:
                entries, duplicate_header, term_headers = (
                    db.search_query_builder.get_def_for_mass_exp(
                        term, table, max_per_dict, name
                    )
                )
            except Exception:
                logger.exception("Mass export lookup failed for %s", term)
                continue
            formatted = format_definitions(
                entries, term_headers, duplicate_header, front, back
            )
            if formatted:
                parts.append(formatted)

        new_value = "<br><br>".join(parts)
        current = note[output_field]
        value = apply_output_mode(current, new_value, mode)
        if value != current:
            note[output_field] = value
            note.flush()
            updated += 1

    if progress is not None:
        progress.setValue(len(note_ids))
    return updated


def _dictionary_choices(db) -> tuple[list[str], dict[str, str]]:
    tables = sorted(db.getAllDicts())
    names = {db.cleanDictName(table).replace("_", " "): table for table in tables}
    labels = sorted(names)
    return labels, names


def show_export_definitions_dialog(browser) -> None:
    from aqt import mw

    note_ids = browser.selectedNotes()
    if not note_ids:
        miInfo(
            "Please select some cards before attempting to export definitions.",
            level="not",
        )
        return

    try:
        import anki.find

        fields = anki.find.fieldNamesForNotes(mw.col, note_ids)
    except Exception:
        fields = []
    if not fields:
        miInfo("Could not read the fields of the selected cards.", level="err")
        return

    db = mw.miDictDB  # ty:ignore[unresolved-attribute]
    labels, table_by_label = _dictionary_choices(db)

    dialog = QDialog(browser)
    dialog.setWindowTitle("Export Definitions")
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    layout = QVBoxLayout(dialog)
    form = QFormLayout()

    input_combo = QComboBox()
    input_combo.addItems(fields)
    output_combo = QComboBox()
    output_combo.addItems(fields)
    mode_combo = QComboBox()
    mode_combo.addItems(MODES)
    max_spin = QSpinBox()
    max_spin.setRange(1, 20)
    max_spin.setValue(1)

    dict_combos = []
    for index in range(3):
        combo = QComboBox()
        if index:
            combo.addItem("None")
        combo.addItems(labels)
        dict_combos.append(combo)

    form.addRow(QLabel("Input Field:"), input_combo)
    form.addRow(QLabel("Output Field:"), output_combo)
    form.addRow(QLabel("Dictionaries:"), dict_combos[0])
    form.addRow(QLabel(""), dict_combos[1])
    form.addRow(QLabel(""), dict_combos[2])
    form.addRow(QLabel("Output Mode:"), mode_combo)
    form.addRow(QLabel("Max Per Dict:"), max_spin)
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    if ok_button is not None:
        ok_button.setText("Execute")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    tables = []
    names = []
    for combo in dict_combos:
        label = combo.currentText()
        if label == "None" or not label:
            continue
        table = table_by_label.get(label)
        if table:
            tables.append(table)
            names.append(label)
    if not tables:
        miInfo("Choose at least one dictionary.", level="not")
        return

    progress = QProgressDialog(
        "Exporting definitions…", "Cancel", 0, len(note_ids), dialog
    )
    progress.setWindowTitle("Export Definitions")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)
    QApplication.processEvents()

    updated = export_definitions(
        mw,
        note_ids,
        input_combo.currentText(),
        output_combo.currentText(),
        mode_combo.currentText(),
        tables,
        names,
        max_spin.value(),
        progress,
    )
    progress.close()
    mw.reset()
    miInfo(f"Updated {updated} of {len(note_ids)} notes.")
