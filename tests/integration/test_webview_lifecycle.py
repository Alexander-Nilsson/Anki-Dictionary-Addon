"""Lifecycle guards that need the real Qt stack.

Kept in ``tests/integration`` so the unit suite never imports the addon's
full Qt/WebEngine graph during collection (that aborts widget tests).
"""

from unittest.mock import patch

import pytest


def test_bridge_diagnostic_ignores_deleted_midict_wrapper() -> None:
    aqt_qt = pytest.importorskip("aqt.qt")
    if not hasattr(aqt_qt, "QComboBox"):
        pytest.skip("real Anki Qt bindings are required")

    from anki_dictionary.core import dictionary

    class DeletedView:
        def page(self) -> None:
            raise RuntimeError("wrapped C/C++ object of type MIDict has been deleted")

    with patch.object(
        dictionary.QTimer,
        "singleShot",
        side_effect=lambda _delay, callback: callback(),
    ):
        dictionary.MIDict._logBridgeDiagnostics(DeletedView())
