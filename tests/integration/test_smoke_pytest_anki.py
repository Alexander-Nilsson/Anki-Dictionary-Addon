"""Smoketest using pytest-anki2.

These tests verify that the addon can be loaded into a real Anki session
provided by the pytest-anki2 plugin, and that opening the dictionary
triggers the expected error from HistoryBrowser.setColors() calling
dictInt.load_theme_color() which doesn't exist on DictInterface.
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


@pytest.mark.parametrize(
    "anki_session",
    [
        dict(
            load_profile=False,
        )
    ],
    indirect=True,
)
def test_history_browser_set_colors_uses_theme_manager(
    anki_session: AnkiSession,
) -> None:
    """HistoryBrowser.setColors() must use theme_manager, not a non-existent
    load_theme_color() method.  Regression test: the parent (DictInterface)
    has theme_manager but not load_theme_color."""
    from unittest.mock import MagicMock
    from PyQt6.QtWidgets import QWidget
    from anki_dictionary.ui.themes import ThemeColors
    from anki_dictionary.utils.history import HistoryBrowser, HistoryModel

    parent = QWidget()
    parent.theme_manager = MagicMock()
    parent.theme_manager.get_active_theme.return_value = ThemeColors(
        header_background="#ffffff",
        selector="#f8f9fa",
        header_text="#212529",
        search_term="#007bff",
        border="#dee2e6",
        anki_button_background="#f8f9fa",
        anki_button_text="#212529",
        tab_hover="#e9ecef",
        current_tab_gradient_top="#ffffff",
        current_tab_gradient_bottom="#e9ecef",
        example_highlight="#fff3cd",
        definition_background="#ffffff",
        definition_text="#212529",
        pitch_accent_color="#dc3545",
    )
    parent.theme_manager.get_qt_styles.return_value = ""

    model = HistoryModel([], parent)
    browser = HistoryBrowser(model, parent)

    assert browser is not None
    assert isinstance(browser, HistoryBrowser)
