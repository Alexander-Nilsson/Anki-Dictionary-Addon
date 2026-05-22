import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# --- Path setup: ensure src/ can be imported ---
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Prevent the root __init__.py (the addon entry point) from being imported
# as `import __init__` during test collection.  The root file is only meant
# for Anki's addon loader; during tests it would trigger `initialize_addon()`
# and fail because there's no real Anki runtime.
if "" in sys.path:
    sys.path.remove("")

# The addon's __init__.py would trigger initialize_addon() when imported,
# which fails without a real Anki runtime.  Stub it so that
# `from __init__ import get_addon_state` (used by config.py) works.
import types as _types

_init_stub = _types.ModuleType("__init__")
_init_stub.get_addon_state = MagicMock(return_value=MagicMock(config={}))
sys.modules["__init__"] = _init_stub


@pytest.fixture
def mock_aqt_mw():
    """Provide a clean MagicMock for aqt.mw for tests that need it."""
    import aqt

    aqt.mw = MagicMock()
    aqt.mw.pm.addonFolder.return_value = str(
        Path.home() / ".local/share/Anki2/addons21"
    )
    aqt.utils.showInfo = MagicMock()
    aqt.utils.tooltip = MagicMock()
    aqt.utils.askUser = MagicMock()
    return aqt.mw


@pytest.fixture
def temp_db_dir(tmp_path):
    """Provide a temporary directory suitable as a database directory."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    return str(db_dir)
