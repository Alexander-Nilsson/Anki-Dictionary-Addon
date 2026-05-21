"""Integration tests that exercise the addon against the real ``anki`` runtime.

These tests use a headless ``anki.collection.Collection`` (no Qt GUI needed)
and verify that our addon's core modules can work with a live Anki database.
"""

import pytest


class TestCollectionBasics:
    """Verify that we can create and manipulate a real Anki collection."""

    def test_collection_opens_and_closes(self, anki_session):
        assert anki_session.collection is not None
        assert anki_session.collection.path.endswith("collection.anki2")

    def test_deck_operations(self, anki_session):
        col = anki_session.collection
        decks = col.decks.all_names_and_ids()
        assert any(d.name == "Default" for d in decks)

    def test_note_creation(self, anki_session):
        col = anki_session.collection
        notetype = col.models.by_name("Basic")
        assert notetype is not None, "Default Basic notetype should exist"

        note = col.new_note(notetype)
        note.fields[0] = "test field"
        note.fields[1] = "test back"
        cur_deck = col.decks.current()
        deck_id = cur_deck["id"] if isinstance(cur_deck, dict) else cur_deck.id
        col.add_note(note, deck_id)

        assert note.id > 0
        saved = col.get_note(note.id)
        assert saved.fields[0] == "test field"


class TestAddonDatabase:
    """Test DictDB against a real SQLite database (without mocking)."""

    def test_db_creation(self, anki_session):
        from anki_dictionary.core.database import DictDB

        db = DictDB()
        assert db is not None
        db.closeConnection()


class TestAddonImports:
    """Verify addon modules can be imported in an Anki environment."""

    def test_core_modules_importable(self):
        import anki_dictionary.core.database  # noqa: F401
        import anki_dictionary.utils.paths  # noqa: F401
        import anki_dictionary.utils.config  # noqa: F401
        import anki_dictionary.utils.constants  # noqa: F401

    def test_utils_importable(self):
        import anki_dictionary.utils.common  # noqa: F401
        import anki_dictionary.utils.logger  # noqa: F401

    @pytest.mark.skip(reason="lldb/gdb not available in CI")
    def test_themes_importable(self):
        import anki_dictionary.ui.themes  # noqa: F401
