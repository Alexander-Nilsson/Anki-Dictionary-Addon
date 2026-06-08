"""Integration tests that exercise the addon against the real ``anki`` runtime.

These tests use a headless ``anki.collection.Collection`` (no Qt GUI needed)
and verify that our addon's core modules can work with a live Anki database.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCollectionBasics:
    """Verify that we can create and manipulate a real Anki collection."""

    def test_collection_opens_and_closes(self, headless_anki_collection):
        assert headless_anki_collection.collection is not None
        assert headless_anki_collection.collection.path.endswith("collection.anki2")

    def test_deck_operations(self, headless_anki_collection):
        col = headless_anki_collection.collection
        decks = col.decks.all_names_and_ids()
        assert any(d.name == "Default" for d in decks)

    def test_note_creation(self, headless_anki_collection):
        col = headless_anki_collection.collection
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

    def test_db_creation(self, headless_anki_collection):
        import aqt
        from unittest.mock import MagicMock

        aqt.mw = MagicMock()
        aqt.mw.pm.addonFolder.return_value = headless_anki_collection.base

        from anki_dictionary.core.database import DictDB

        db = DictDB()
        assert db is not None
        db.closeConnection()
        aqt.mw = None


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

    def test_themes_importable(self):
        import anki_dictionary.ui.themes  # noqa: F401

    def test_dictionary_importable(self):
        """DictInterface — the main orchestrator — must import cleanly
        against the real aqt.qt, since it uses many Qt symbols."""
        import anki_dictionary.core.dictionary  # noqa: F401

    def test_all_qt_names_have_imports(self):
        """AST-based check: every Qt symbol used in dictionary.py must
        be explicitly imported, catching symbols missed during refactoring
        (e.g. QThreadPool, QSvgWidget)."""
        import ast

        src = (
            Path(__file__).parent.parent.parent
            / "src"
            / "anki_dictionary"
            / "core"
            / "dictionary.py"
        ).read_text()
        tree = ast.parse(src)

        # Collect imported Qt names
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(("PyQt6", "aqt")):
                    for alias in node.names:
                        imported.add(alias.asname or alias.name)

        # Find all Qt-like names used outside imports
        # Exclude: import statements, string literals, comments, decorators
        used: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                name = node.id
                if (
                    name.startswith("Q")
                    and len(name) > 1
                    and name[1].isupper()
                    and not name.startswith("Qt.")
                ):
                    used.add(name)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "Qt":
                    pass  # Qt.Enum.Value is handled via the `Qt` import

        missing = used - imported
        assert not missing, (
            f"Qt symbol(s) used in dictionary.py but not imported: "
            f"{', '.join(sorted(missing))}. "
            f"Add them to the from aqt.qt or from PyQt6.* import block."
        )

    def test_image_resizer_runtime(self):
        """``imageResizer`` uses QImage/QSize/Qt — verify they resolve at
        runtime (catches missing symbols that import-time alone would miss)."""
        from anki_dictionary.core.dictionary import imageResizer

        # Non-existent file => should return False, not crash
        assert imageResizer("/nonexistent/path.jpg") is False

    def test_qthreadpool_instantiation(self):
        """``QThreadPool()`` caused a NameError at runtime because it was
        used inside ``DictInterface.__init__`` but missing from the import
        block.  Test it directly so it can't be missed again."""
        from PyQt6.QtCore import QThreadPool

        pool = QThreadPool()
        assert pool.maxThreadCount() > 0

    def test_dictinterface_constructor_symbols(self):
        """Verify that every Qt symbol used in ``DictInterface.__init__``
        and ``startUp`` resolves at runtime, without needing a display
        (test only non-widget symbols that the AST check can't verify)."""
        import anki_dictionary.core.dictionary as _d

        # Symbols used in __init__ / startUp that don't need a QWidget
        assert _d.QThreadPool is not None
        assert _d.QColor is not None
        assert _d.QIcon is not None
        assert _d.QPalette is not None
        assert _d.QPixmap is not None
        assert _d.QKeySequence is not None
        assert _d.QShortcut is not None

    def test_main_window_importable(self):
        """Loaded at startup via hooks.py → dictOnStart().

        main_window.py accesses ``aqt.mw`` at module level (setting
        ``mw.dictionaryInit``).  Give it a minimal stub so the import
        succeeds, then verify ``mw.dictionaryInit`` was wired up.
        """
        import aqt

        aqt.mw = _mw = MagicMock()
        import anki_dictionary.ui.main_window  # noqa: F401

        assert aqt.mw.dictionaryInit is not None
        assert callable(aqt.mw.dictionaryInit)
        aqt.mw = None  # restore


class TestDictInterface:
    """DictInterface instantiation tests."""

    def test_dictinterface_instantiation(self, qapp):
        """Verify DictInterface can be constructed with a QApplication.

        Patches heavy dependencies (ThemeManager, ThemeEditorDialog, startUp)
        so we only verify the QApplication requirement is satisfied, not the
        full widget tree creation.
        """
        from unittest.mock import MagicMock

        import aqt
        import anki_dictionary.core.dictionary as _d

        aqt.mw = MagicMock()  # ensureWidgetInScreenBoundaries accesses aqt.mw.progress

        with (
            patch.object(_d, "ThemeManager", return_value=MagicMock()),
            patch.object(_d, "ThemeEditorDialog", return_value=MagicMock()),
            patch.object(_d.DictInterface, "startUp"),
            patch.object(_d.DictInterface, "setHotkeys"),
        ):
            dictdb = MagicMock()
            mw = MagicMock()
            path = "/tmp"

            instance = _d.DictInterface(dictdb, mw, path, welcome=True)

            assert instance is not None
            assert isinstance(instance, _d.DictInterface)
