"""Smoketest using pytest-anki2.

This test verifies that the addon can be loaded into a real Anki session
provided by the pytest-anki2 plugin.
"""

import atexit
import shutil
import tempfile
from pathlib import Path

import pytest
from pytest_anki import AnkiSession

# Build a minimal addon source directory once at import time so the path is
# stable for pytest-anki2's parametrized ``anki_session`` fixture.
_ADDON_SOURCE_DIR = Path(tempfile.mkdtemp(prefix="anki_dict_addon_"))
_REPO_ROOT = Path(__file__).parent.parent.parent

for _name in ("__init__.py", "config.json", "src", "assets", "vendor", "user_files"):
    _src = _REPO_ROOT / _name
    if _src.exists():
        _dst = _ADDON_SOURCE_DIR / _name
        if _src.is_dir():
            shutil.copytree(
                _src, _dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        else:
            shutil.copy2(_src, _dst)


def _cleanup_addon_source() -> None:
    shutil.rmtree(_ADDON_SOURCE_DIR, ignore_errors=True)


atexit.register(_cleanup_addon_source)


@pytest.mark.parametrize(
    "anki_session",
    [
        dict(
            unpacked_addons=[
                (
                    # Use a numeric addon ID so the addon directory name
                    # does not clash with the anki_dictionary package inside
                    # src/anki_dictionary.
                    "12345678",
                    str(_ADDON_SOURCE_DIR),
                )
            ],
            load_profile=True,
        )
    ],
    indirect=True,
)
def test_addon_loads_with_pytest_anki(anki_session: AnkiSession) -> None:
    """Verify the addon loads and initializes in a real Anki runtime."""
    # load_profile=True already loads the profile, so we don't need
    # the profile_loaded() context manager here.
    anki_session.load_addon("12345678")
    # The addon's __init__.py sets mw.ankiDictionary on initialization
    assert hasattr(anki_session.mw, "ankiDictionary")
    # Config should also be attached
    assert hasattr(anki_session.mw, "AnkiDictConfig")
