import os
import sys
from pathlib import Path

import pytest

src_path = str(Path(__file__).parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Remove any stubs that the top-level conftest may have installed so the real
# anki / aqt packages are used.
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith(("aqt", "anki")):
        if "unittest.mock" in str(type(sys.modules[mod_name])):
            del sys.modules[mod_name]

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
