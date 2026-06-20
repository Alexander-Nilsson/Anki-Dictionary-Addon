from __future__ import annotations

from typing import Any, Dict, List, Tuple

from anki.notes import Note
from anki.collection import Collection


def add_note(note: Note, did: int, collection: Collection) -> None:
    collection.add_note(note, did)  # ty:ignore[invalid-argument-type]


def get_decks(collection: Collection) -> List[Tuple[int, str]]:
    decks = collection.decks.all_names_and_ids()
    return [(d.id, d.name) for d in decks]


def get_fields_values(
    config: Dict[str, Any], db: Any, note: Note, template: str
) -> Dict[str, str]:
    field_map = config.get("fieldNameToValue", {})
    fields_config = config.get("fieldConfig", {})
    values: Dict[str, str] = {}
    nt = note.note_type()
    if nt is None:
        return values
    for field in nt["flds"]:
        name = field["name"]
        mapped = field_map.get(name, name)
        if mapped in fields_config:
            val = fields_config[mapped].get("default", "")
        else:
            val = ""
        if val:
            values[name] = val
    return values


def automatically_add_definitions(
    note: Note, word: str, template: str, db: Any
) -> None:
    nt = note.note_type()
    if nt is None:
        return
    for field in nt["flds"]:
        name = field["name"]
        if name.lower() in ("word", "term", "vocabulary"):
            if not note[name]:
                note[name] = word


def extract_freq_info(entry: Dict[str, Any], config: Dict[str, Any]) -> Tuple[str, str]:
    star_count = entry.get("starCount", "")
    level_labels = entry.get("levelLabels", "")
    return star_count, level_labels
