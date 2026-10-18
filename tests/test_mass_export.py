from __future__ import annotations

import unittest
from unittest.mock import patch

from anki_dictionary.exporters.mass_export import (
    MODE_ADD,
    MODE_IF_EMPTY,
    MODE_OVERWRITE,
    apply_output_mode,
    export_definitions,
    format_definitions,
    strip_field_html,
)


class _Note:
    def __init__(self, fields):
        self.fields = dict(fields)
        self.flushed = False

    def keys(self):
        return list(self.fields)

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def flush(self):
        self.flushed = True


class _Search:
    def __init__(self, entries):
        self.entries = entries
        self.calls = []

    def get_def_for_mass_exp(self, term, table, limit, name):
        self.calls.append((term, table, limit, name))
        return self.entries, 0, ["term", "altterm", "pronunciation"]


class _Db:
    def __init__(self, entries):
        self.search_query_builder = _Search(entries)


class _Col:
    def __init__(self, notes):
        self.notes = notes

    def get_note(self, note_id):
        return self.notes[note_id]


class _Mw:
    def __init__(self, notes, entries):
        self.col = _Col({nid: _Note(fields) for nid, fields in notes.items()})
        self.miDictDB = _Db(entries)


class TestMassExportFormatting(unittest.TestCase):
    def test_strip_field_html_removes_tags_and_media(self):
        self.assertEqual(strip_field_html("<b>日本</b> [sound:foo.mp3]"), "日本")

    def test_apply_output_mode(self):
        self.assertEqual(apply_output_mode("old", "new", MODE_ADD), "old<br><br>new")
        self.assertEqual(apply_output_mode("", "new", MODE_ADD), "new")
        self.assertEqual(apply_output_mode("old", "new", MODE_OVERWRITE), "new")
        self.assertEqual(apply_output_mode("", "new", MODE_IF_EMPTY), "new")
        self.assertEqual(apply_output_mode("old", "new", MODE_IF_EMPTY), "old")
        self.assertEqual(apply_output_mode("old", "", MODE_OVERWRITE), "old")

    def test_format_definitions_uses_term_header(self):
        entries = [
            {
                "term": "日本",
                "altterm": "",
                "pronunciation": "にほん",
                "definition": "Japan",
                "starCount": "",
            }
        ]
        self.assertEqual(
            format_definitions(entries, ["term", "altterm", "pronunciation"], 0),
            "【日本】 にほん<br>Japan",
        )

    def test_format_definitions_duplicate_header_inserts_stars(self):
        entries = [
            {
                "term": "日本",
                "altterm": "",
                "pronunciation": "",
                "definition": "【日本】 Japan",
                "starCount": "★",
            }
        ]
        result = format_definitions(entries, ["term"], 1)
        self.assertIn("★", result)
        self.assertNotIn("【日本】<br>", result)

    def test_format_definitions_empty(self):
        self.assertEqual(format_definitions([], ["term"], 0), "")


class TestMassExportWrite(unittest.TestCase):
    _entries = [
        {
            "term": "日本",
            "altterm": "",
            "pronunciation": "にほん",
            "definition": "Japan",
            "starCount": "",
        }
    ]

    def _run(self, initial, mode=MODE_ADD):
        mw = _Mw({1: {"Word": "日本", "Definition": initial}}, self._entries)
        with patch(
            "anki_dictionary.exporters.mass_export.get_addon_config",
            return_value={"frontBracket": "【", "backBracket": "】"},
        ):
            updated = export_definitions(
                mw, [1], "Word", "Definition", mode, ["t"], ["dict"], 1
            )
        return mw, updated

    def test_writes_new_definition(self):
        mw, updated = self._run("")
        self.assertEqual(updated, 1)
        self.assertEqual(mw.col.notes[1]["Definition"], "【日本】 にほん<br>Japan")
        self.assertTrue(mw.col.notes[1].flushed)

    def test_add_appends(self):
        mw, updated = self._run("old")
        self.assertEqual(updated, 1)
        self.assertEqual(
            mw.col.notes[1]["Definition"],
            "old<br><br>【日本】 にほん<br>Japan",
        )

    def test_overwrite_replaces(self):
        mw, updated = self._run("old", MODE_OVERWRITE)
        self.assertEqual(updated, 1)
        self.assertTrue(mw.col.notes[1]["Definition"].startswith("【日本】"))

    def test_if_empty_keeps_existing(self):
        mw, updated = self._run("old", MODE_IF_EMPTY)
        self.assertEqual(updated, 0)
        self.assertEqual(mw.col.notes[1]["Definition"], "old")

    def test_skips_notes_without_the_fields(self):
        mw = _Mw({1: {"Word": "日本"}}, self._entries)
        with patch(
            "anki_dictionary.exporters.mass_export.get_addon_config",
            return_value={},
        ):
            updated = export_definitions(
                mw, [1], "Word", "Definition", MODE_ADD, ["t"], ["dict"], 1
            )
        self.assertEqual(updated, 0)
        self.assertFalse(mw.col.notes[1].flushed)


if __name__ == "__main__":
    unittest.main()
