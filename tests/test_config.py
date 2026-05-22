from __future__ import annotations

import os
import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

import sys

_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from anki_dictionary.utils.config import (
    get_addon_config,
    save_addon_config,
    refresh_anki_dict_config,
)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    @patch("anki_dictionary.utils.config.mw")
    @patch("anki_dictionary.utils.config.get_addon_root")
    def test_get_addon_config_fallback_defaults(self, mock_root, mock_mw):
        mock_root.return_value = "/fake/addon"
        mock_mw.addonManager.getConfig.return_value = None

        with patch("anki_dictionary.utils.config.json.load") as mock_json_load:
            mock_json_load.side_effect = FileNotFoundError
            result = get_addon_config()

        self.assertIn("DictionaryGroups", result)
        self.assertEqual(result["maxWidth"], 1500)
        self.assertEqual(result["maxHeight"], 400)
        self.assertEqual(result["currentGroup"], "All")
        self.assertEqual(result["forvo_enabled"], True)

    @patch("anki_dictionary.utils.config.mw")
    @patch("anki_dictionary.utils.config.get_addon_root")
    def test_save_and_refresh_config(self, mock_root, mock_mw):
        mock_root.return_value = "/fake/addon"
        mock_mw.addonManager.writeConfig.return_value = None

        config = {"test_key": "test_value", "maxWidth": 1000}
        result = save_addon_config(config)
        self.assertTrue(result)

    @patch("anki_dictionary.utils.config.mw")
    def test_refresh_config_with_dict(self, mock_mw):
        mock_mw.ankiDictionary = MagicMock()
        mock_mw.ankiDictionary.isVisible.return_value = True

        config = {"key": "value"}
        refresh_anki_dict_config(config)
        mock_mw.ankiDictionary.resetConfiguration.assert_called_once()

    @patch("anki_dictionary.utils.config.mw")
    def test_get_addon_config_from_state(self, mock_mw):
        from __init__ import get_addon_state

        state_config = {"from_state": True, "maxSearch": 500}
        get_addon_state.return_value.config = state_config

        with patch(
            "anki_dictionary.utils.config.get_addon_root", return_value="/fake/addon"
        ):
            result = get_addon_config()

        self.assertEqual(result, state_config)


if __name__ == "__main__":
    unittest.main()
