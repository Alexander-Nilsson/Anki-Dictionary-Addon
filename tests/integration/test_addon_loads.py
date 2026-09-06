"""Integration tests that exercise the addon against the real ``anki`` runtime.

These tests use a headless ``anki.collection.Collection`` (no Qt GUI needed)
and verify that our addon's core modules can work with a live Anki database.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


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
        from unittest.mock import MagicMock

        import aqt

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
        import anki_dictionary.utils.config  # noqa: F401
        import anki_dictionary.utils.constants  # noqa: F401
        import anki_dictionary.utils.paths  # noqa: F401

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


class TestTrySearchClipboardPause:
    """U2: ``main_window.trySearch`` labels clipboard searches and honours the
    one-click clipboard-monitor pause pill.

    Lives here (not in the unit suite) because importing ``main_window`` pulls
    in ``clip_thread`` → ``aqt.qt`` (``QObject``/``pyqtSignal``), which some
    unit tests stub out of ``sys.modules`` at collection time.
    """

    @staticmethod
    def _main_window():
        import aqt

        aqt.mw = MagicMock()
        import anki_dictionary.ui.main_window as module

        aqt.mw = None  # restore
        return module

    def test_resumes_search_sources_clipboard(self):
        module = self._main_window()
        anki = MagicMock()
        anki.config.get.return_value = True  # clipboard_monitor_enabled
        with patch.object(module, "mw") as mock_mw:
            mock_mw.ankiDictionary = anki
            module.trySearch("\u98df\u3079\u308b")
        anki.initSearch.assert_called_once_with(
            "\u98df\u3079\u308b", source="clipboard"
        )

    def test_skipped_when_clipboard_paused(self):
        module = self._main_window()
        anki = MagicMock()
        anki.config.get.return_value = False  # clipboard_monitor_enabled
        with patch.object(module, "mw") as mock_mw:
            mock_mw.ankiDictionary = anki
            module.trySearch("\u98df\u3079\u308b")
        anki.initSearch.assert_not_called()

    def test_noop_when_dictionary_closed(self):
        module = self._main_window()
        with patch.object(module, "mw") as mock_mw:
            mock_mw.ankiDictionary = None
            module.trySearch("\u98df\u3079\u308b")  # must not raise


class TestDictInterface:
    """DictInterface instantiation tests."""

    def test_dictinterface_instantiation(self, qapp):
        """Verify DictInterface can be constructed with a QApplication.

        Patches heavy dependencies (ThemeManager, startUp) so we only verify
        the QApplication requirement is satisfied, not the full widget tree
        creation.
        """
        from unittest.mock import MagicMock

        import aqt

        import anki_dictionary.core.dictionary as _d

        aqt.mw = MagicMock()  # ensureWidgetInScreenBoundaries accesses aqt.mw.progress

        with (
            patch.object(_d, "ThemeManager", return_value=MagicMock()),
            patch.object(_d.DictInterface, "startUp"),
            patch.object(_d.DictInterface, "setHotkeys"),
        ):
            dictdb = MagicMock()
            mw = MagicMock()
            path = "/tmp"

            instance = _d.DictInterface(dictdb, mw, path, welcome=True)

            assert instance is not None
            assert isinstance(instance, _d.DictInterface)


class TestHistoryAndSessionActions:
    """U3/A4/A5: history prune/delete + session restore on DictInterface.

    ``DictInterface`` is built without ``__init__`` (Qt-free) and given fake
    ``historyModel``/``dict`` handles, so these bridge-facing methods are
    exercised without a full widget tree.
    """

    @staticmethod
    def _dict_interface():
        import anki_dictionary.core.dictionary as _d

        instance = _d.DictInterface.__new__(_d.DictInterface)
        instance.dict = MagicMock()
        instance.config = {}
        instance.writeConfig = MagicMock()
        instance.historyModel = MagicMock()
        instance.historyModel.history = [["a", "2026-01-01"], ["b", "2026-01-02"]]
        instance.historyModel.justTerms = ["a", "b"]
        instance.historyModel.removeRows.side_effect = lambda pos, rows=1: (
            instance.historyModel.history.__delitem__(slice(pos, pos + rows))
        )
        return instance

    def test_delete_history_entry_removes_row_and_pushes(self):
        inst = self._dict_interface()
        inst.deleteHistoryEntry("a")
        assert [row[0] for row in inst.historyModel.history] == ["b"]
        assert inst.historyModel.justTerms == ["b"]
        inst.dict.eval.assert_called_once()
        payload = inst.dict.eval.call_args[0][0]
        assert payload.startswith("setSearchHistory(")
        assert '"b"' in payload

    def test_delete_history_entry_unknown_term_is_noop(self):
        inst = self._dict_interface()
        inst.deleteHistoryEntry("missing")
        assert len(inst.historyModel.history) == 2
        # A refresh is still pushed (idempotent).
        inst.dict.eval.assert_called_once()

    def test_prune_history_caps_rows(self):
        inst = self._dict_interface()
        inst.pruneHistory(limit=1)
        assert [row[0] for row in inst.historyModel.history] == ["b"]

    def test_save_session_caps_and_persists(self):
        inst = self._dict_interface()
        inst.saveSession(["   ", "a", "b", "c"] * 10)
        write_cfg = inst.writeConfig.call_args
        assert write_cfg[0][0] == "session_terms"
        assert len(write_cfg[0][1]) <= 20
        assert write_cfg[0][1][:3] == ["a", "b", "c"]

    def test_restore_session_opt_in(self):
        inst = self._dict_interface()
        assert inst.restoreSession() == []
        inst.config = {"restore_session": True, "session_terms": ["a", "", "b"]}
        assert inst.restoreSession() == ["a", "b"]


class TestDictionaryInitSessionRestore:
    """A5: ``dictionaryInit`` reopens the persisted session when enabled.

    The restore terms are read from ``mw.AnkiDictConfig`` *before* the instance
    exists (a previous version called ``restoreSession`` on the still-``None``
    ``mw.ankiDictionary`` — dead code, always swallowed by the except).
    """

    @staticmethod
    def _run(terms, anki_dict_config):
        import aqt

        aqt.mw = MagicMock()
        import anki_dictionary.ui.main_window as module

        aqt.mw = None  # restore
        with (
            patch.object(module, "mw") as mock_mw,
            patch.object(module, "DictInterface") as mock_cls,
            patch.object(module, "showAfterGlobalSearch"),
            patch.object(module, "getWelcomeScreen", return_value="<welcome>"),
            patch.object(module, "getMacWelcomeScreen", return_value="<welcome>"),
        ):
            mock_mw.ankiDictionary = None
            mock_mw.AnkiDictConfig = anki_dict_config
            module.dictionaryInit(terms)
        return mock_cls

    def test_restore_terms_used_when_enabled(self):
        mock_cls = self._run(
            False, {"restore_session": True, "session_terms": ["cat", "", "dog"]}
        )
        assert mock_cls.call_args.kwargs["terms"] == ["cat", "dog"]

    def test_restore_skipped_when_disabled(self):
        mock_cls = self._run(
            False, {"restore_session": False, "session_terms": ["cat"]}
        )
        assert mock_cls.call_args.kwargs["terms"] is False

    def test_restore_skipped_when_explicit_terms(self):
        mock_cls = self._run(
            ["explicit"], {"restore_session": True, "session_terms": ["cat"]}
        )
        assert mock_cls.call_args.kwargs["terms"] == ["explicit"]
