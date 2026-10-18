"""Regression tests for the search index, row cache, and import parser."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anki_dictionary.core.database import DictDB
from anki_dictionary.core.search.query import SearchQueryBuilder
from anki_dictionary.ui.dialogs.dict_import import _loads_dictionary_json
from scripts.create_empty_db import create_empty_database

CONFIG = {
    "star_char": "★",
    "star_thresholds": [1501, 5001, 15001, 30001, 60001],
    "show_stars": True,
    "show_rank": False,
    "show_hsk": True,
}


class CountingCursor:
    """Cursor proxy that records executed SQL statements."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.statements = []

    def execute(self, sql, params=()):
        self.statements.append(sql)
        return self._cursor.execute(sql, params)

    def executemany(self, sql, params):
        self.statements.append(sql)
        return self._cursor.executemany(sql, params)

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()


@pytest.fixture
def db_and_table(tmp_path):
    db_path = os.path.join(str(tmp_path), "dictionaries.sqlite")
    create_empty_database(db_path)

    with (
        patch("anki_dictionary.core.database.get_db_dir", return_value=str(tmp_path)),
        patch("anki_dictionary.core.database.get_addon_config", return_value=CONFIG),
    ):
        db = DictDB()
        db.addLanguages(["Japanese"])
        success, _, dict_name = db.addDict("TestDict", "Japanese", "[]")
        assert success
        lid = db.getLangId("Japanese")
        table = db.formatDictName(lid, dict_name)
        db.importToDict(
            table,
            [
                ("食べる", "たべる", "taberu", "verb", "To eat", "", "", 1, ""),
                ("飲む", "のむ", "nomu", "verb", "To drink", "", "", 500, ""),
            ],
        )
        db.commitChanges()

    yield db, table
    db.closeConnection()


def _search(db, table, term, limit=10, covering_column=None):
    builder = SearchQueryBuilder(db)
    return builder.execute_search(
        table, " term LIKE ? ", limit, (f"%{term}%",), covering_column
    )


def test_frequency_index_is_created_lazily(db_and_table):
    db, table = db_and_table
    cursor = db._get_cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?;",
        ("itf" + table,),
    )
    assert cursor.fetchone() is None

    _search(db, table, "食", covering_column="term")

    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?;",
        ("itf" + table,),
    )
    assert cursor.fetchone() is not None


def test_covering_search_matches_table_scan_and_orders(db_and_table):
    db, table = db_and_table
    db.importToDict(
        table,
        [
            ("食", "", "", "", "food", "", "", 500, ""),
            ("食品", "", "", "", "food product", "", "", 10, ""),
            ("食堂", "", "", "", "canteen", "", "", 2, ""),
        ],
    )
    db.commitChanges()

    covered = _search(db, table, "食", covering_column="term")
    plain = _search(db, table, "食")

    assert covered == plain
    # Shortest first, then ascending frequency (食堂=2 before 食品=10).
    assert [row[0] for row in covered] == ["食", "食堂", "食品", "食べる"]


def test_repeated_search_is_served_from_cache(db_and_table, monkeypatch):
    db, table = db_and_table
    builder = SearchQueryBuilder(db)
    real_get_cursor = db._get_cursor
    counting = CountingCursor(real_get_cursor())
    monkeypatch.setattr(db, "_get_cursor", lambda: counting)

    first = builder.execute_search(table, " term LIKE ? ", 10, ("%食%",))
    second = builder.execute_search(table, " term LIKE ? ", 10, ("%食%",))

    assert first == second
    assert len(counting.statements) == 1

    monkeypatch.setattr(db, "_get_cursor", real_get_cursor)
    db.importToDict(
        table,
        [("食料", "", "", "", "foodstuff", "", "", 3, "")],
    )
    db.commitChanges()

    counting_after_import = CountingCursor(real_get_cursor())
    monkeypatch.setattr(db, "_get_cursor", lambda: counting_after_import)
    third = builder.execute_search(table, " term LIKE ? ", 10, ("%食%",))

    assert len(counting_after_import.statements) == 1
    assert "食料" in [row[0] for row in third]


def test_empty_results_are_cached(db_and_table, monkeypatch):
    db, table = db_and_table
    builder = SearchQueryBuilder(db)
    real_get_cursor = db._get_cursor
    counting = CountingCursor(real_get_cursor())
    monkeypatch.setattr(db, "_get_cursor", lambda: counting)

    assert builder.execute_search(table, " term LIKE ? ", 10, ("%none%",)) == []
    assert builder.execute_search(table, " term LIKE ? ", 10, ("%none%",)) == []
    assert len(counting.statements) == 1


def test_covering_column_is_only_used_for_leading_wildcards():
    assert SearchQueryBuilder._covering_column("term", "LIKE", ["%x%"]) == "term"
    assert SearchQueryBuilder._covering_column("term", "LIKE", ["x%"]) is None
    assert SearchQueryBuilder._covering_column("term", "=", ["%x%"]) is None
    assert SearchQueryBuilder._covering_column("definition", "LIKE", ["%x%"]) is None


def test_orjson_parser_handles_utf8_and_fallbacks():
    payload = [["食べる", "", {"definition": "To eat"}]]

    assert _loads_dictionary_json(json.dumps(payload).encode()) == payload
    assert (
        _loads_dictionary_json(b"\xef\xbb\xbf" + json.dumps(payload).encode())
        == payload
    )
    assert _loads_dictionary_json(json.dumps(payload).encode("utf-16")) == payload


def test_import_parser_still_rejects_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        _loads_dictionary_json(b"{not json")
