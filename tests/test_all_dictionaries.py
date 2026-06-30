import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.network

# Add src and root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import aqt

from anki_dictionary.core.database import DictDB
from anki_dictionary.ui.dialogs.dictionary_manager import importDict
from scripts.create_empty_db import create_empty_database

aqt.mw = MagicMock()

INDEX_URL = "https://github.com/Alexander-Nilsson/dictionaries/raw/main/index.json"
SERVER_ROOT = "https://github.com/Alexander-Nilsson/dictionaries/raw/main"


def get_all_dictionaries():
    resp = requests.get(INDEX_URL)
    index = resp.json()
    dicts = []
    for lang in index.get("languages", []):
        lang_name = lang["name_en"]
        # Direct dictionaries
        for d in lang.get("dictionaries", []):
            url = d["url"]
            if not url.startswith("http"):
                url = SERVER_ROOT + url
            dicts.append({"lang": lang_name, "name": d["name"], "url": url})

        # To-languages
        for to_lang in lang.get("to_languages", []):
            to_name = to_lang["name_en"]
            for d in to_lang.get("dictionaries", []):
                url = d["url"]
                if not url.startswith("http"):
                    url = SERVER_ROOT + url
                dicts.append(
                    {"lang": lang_name, "name": f"{d['name']} ({to_name})", "url": url}
                )
    return dicts


def test_all():
    dictionaries = get_all_dictionaries()
    print(f"Found {len(dictionaries)} dictionaries to test.")

    test_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(test_dir.name, "dictionaries.sqlite")

    with patch("anki_dictionary.core.database.get_db_dir", return_value=test_dir.name):
        create_empty_database(db_path)
        db = DictDB()
        aqt.mw.miDictDB = db

        results = []
        for i, d in enumerate(dictionaries):
            lang = d["lang"]
            name = d["name"]
            url = d["url"]

            print(f"[{i + 1}/{len(dictionaries)}] Testing {name} ({lang})...")

            try:
                if lang not in db.getCurrentDbLangs():
                    db.addLanguages([lang])

                # Use stream to check headers first
                resp = requests.get(url, timeout=60)
                if resp.status_code != 200:
                    results.append(
                        {
                            "name": name,
                            "status": "FAIL",
                            "error": f"HTTP {resp.status_code}",
                        }
                    )
                    continue

                final_name = importDict(lang, io.BytesIO(resp.content), name)

                lid = db.getLangId(lang)
                table_name = db.formatDictName(lid, final_name)
                cursor = db._get_cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]

                if count > 0:
                    print(f"  SUCCESS: {count} entries.")
                    results.append({"name": name, "status": "OK", "count": count})
                else:
                    print("  FAIL: No entries.")
                    results.append(
                        {"name": name, "status": "FAIL", "error": "No entries imported"}
                    )

                # Cleanup: Delete the dictionary to keep DB size manageable
                db.deleteDict(final_name)

            except Exception as e:
                print(f"  ERROR: {str(e)}")
                results.append({"name": name, "status": "ERROR", "error": str(e)})

        db.closeConnection()

    test_dir.cleanup()

    print("\n" + "=" * 50)
    print("FINAL REPORT")
    print("=" * 50)
    success_count = sum(1 for r in results if r["status"] == "OK")
    for r in results:
        if r["status"] == "OK":
            print(f"[OK]    {r['name']} ({r['count']} entries)")
        else:
            print(f"[FAIL]  {r['name']}: {r.get('error', 'Unknown error')}")

    print("=" * 50)
    print(f"Summary: {success_count}/{len(dictionaries)} passed.")

    if success_count < len(dictionaries):
        sys.exit(1)


if __name__ == "__main__":
    test_all()
