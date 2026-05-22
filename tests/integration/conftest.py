import os
import sys
from pathlib import Path

import pytest

src_path = str(Path(__file__).parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Check if a real anki is available; skip all tests if not.
_anki_available = False
try:
    import anki.collection  # noqa: F401

    _anki_available = True
except ImportError:
    pass


def pytest_collection_modifyitems(items):
    conftest_dir = Path(__file__).parent.resolve()
    for item in items:
        fspath = getattr(item, "fspath", None)
        if fspath:
            try:
                item_path = Path(fspath).resolve()
                if (
                    conftest_dir in item_path.parents
                    or item_path.parent == conftest_dir
                ):
                    item.add_marker(pytest.mark.integration)
                    if not _anki_available:
                        item.add_marker(
                            pytest.mark.skip(
                                reason="anki package not available in this environment"
                            )
                        )
            except Exception:
                pass


@pytest.fixture(scope="session")
def qapp():
    """Create or reuse a QApplication for widget tests that need one.

    Sets ``AA_ShareOpenGLContexts`` before creation to allow the
    ``aqt.qt`` → ``PyQt6.QtWebEngineWidgets`` import chain to succeed
    when a QCoreApplication already exists.

    Uses a session scope so all widget tests share a single instance.
    pytest-qt's built-in ``qapp`` fixture is function-scoped; we need
    session scope for tests that construct widgets outside the test
    function's lifetime.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        app = QApplication([])
    yield app


@pytest.fixture(scope="function")
def anki_session():
    """Create a headless real Anki collection for integration testing.

    Uses the installed ``anki`` package directly (no Qt GUI needed).
    Yields a namespace with:
      .collection -- ``anki.collection.Collection`` backed by a temp DB
      .base       -- temporary Anki base directory path
    """
    import shutil
    import tempfile
    from anki.collection import Collection

    base_dir = tempfile.mkdtemp(prefix="anki_dict_int_")
    col_path = os.path.join(base_dir, "collection.anki2")
    col = Collection(col_path)

    class Session:
        collection = col
        base = base_dir

        def cleanup(self):
            try:
                self.collection.close()
            except Exception:
                pass
            try:
                shutil.rmtree(self.base, ignore_errors=True)
            except Exception:
                pass

    session = Session()
    try:
        yield session
    finally:
        session.cleanup()
