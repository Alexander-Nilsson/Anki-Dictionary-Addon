import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

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

# --- Mock aqt/anki modules BEFORE any test file is imported ---
# Many existing test files import addon modules at module level
# (e.g. "from anki_dictionary.core.database import DictDB").
# Those imports chain through utils/common.py, config.py, paths.py
# which all "import aqt" or "from aqt import mw".
#
# We install stubs here so that the imports succeed, then individual
# test functions can use the mock_aqt_mw fixture for more control.

_MODULES_TO_MOCK = [
    "aqt",
    "aqt.qt",
    "aqt.utils",
    "aqt.webview",
    "anki",
    "anki.hooks",
    "anki.utils",
    "anki.httpclient",
    "anki.lang",
]

for _mod in _MODULES_TO_MOCK:
    if _mod not in sys.modules:
        if _mod == "aqt":
            _aqt = types.ModuleType("aqt")
            _aqt.qt = types.ModuleType("aqt.qt")
            _aqt.utils = types.ModuleType("aqt.utils")
            _aqt.webview = types.ModuleType("aqt.webview")
            _aqt.mw = None
            _aqt.utils.showInfo = MagicMock()
            _aqt.utils.tooltip = MagicMock()
            _aqt.utils.askUser = MagicMock()
            _aqt.utils.openLink = MagicMock()
            _aqt.webview.AnkiWebView = MagicMock
            sys.modules["aqt"] = _aqt
            sys.modules["aqt.qt"] = _aqt.qt
            sys.modules["aqt.utils"] = _aqt.utils
            sys.modules["aqt.webview"] = _aqt.webview
        else:
            sys.modules[_mod] = MagicMock()

sys.modules["anki.utils"].is_mac = MagicMock(return_value=False)
sys.modules["anki.utils"].is_win = MagicMock(return_value=False)
sys.modules["anki.utils"].is_lin = MagicMock(return_value=True)
sys.modules["anki.utils"].strip_html = MagicMock(side_effect=lambda x: x if x else "")

# --- Mock the root __init__.py to prevent it from being imported ---
# The root __init__.py is only meant as an Anki addon entry point.
# When test files mock aqt.mw as a MagicMock (non-None), importing
# the root __init__.py triggers initialize_addon(), which calls
# setup_hooks() and fails because there's no real Anki runtime.
# We pre-install a stub so `from __init__ import get_addon_state`
# (used by config.py) resolves here instead.
_init_stub = types.ModuleType("__init__")
_init_stub.get_addon_state = MagicMock()
_init_stub.get_addon_state.return_value.config = {}
sys.modules["__init__"] = _init_stub


import pytest


@pytest.fixture
def mock_aqt_mw():
    """Provide a clean MagicMock for aqt.mw for tests that need it."""
    aqt_mod = sys.modules.get("aqt")
    aqt_mod.mw = MagicMock()
    aqt_mod.mw.pm.addonFolder.return_value = str(
        Path.home() / ".local/share/Anki2/addons21"
    )
    aqt_mod.utils.showInfo = MagicMock()
    aqt_mod.utils.tooltip = MagicMock()
    aqt_mod.utils.askUser = MagicMock()
    return aqt_mod.mw


@pytest.fixture
def temp_db_dir(tmp_path):
    """Provide a temporary directory suitable as a database directory."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    return str(db_dir)
