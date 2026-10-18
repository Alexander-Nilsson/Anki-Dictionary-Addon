"""Dump real search documents from the dictionary DB for the mock preview.

``web/src/dev-mock.ts`` serves ``docs/<term>.json`` from the same origin as
``dictionary.html?mock=1`` when present, so the browser preview (and the docs
site media pipeline) shows REAL entries from the installed dictionaries
instead of the placeholder text. Run this from the repo root with the real
``user_files/db/dictionaries.sqlite`` present.

Usage::

    uv run python scripts/docs_media/dump_docs.py [TERM ...]

Writes web/dist/docs/<term>.json. Default terms cover the zh dictionaries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import types as _types

_init_stub = _types.ModuleType("__init__")
_init_stub.get_addon_state = MagicMock(return_value=MagicMock(config={}))
sys.modules["__init__"] = _init_stub

DEFAULT_TERMS = ["电脑", "水", "你好", "时间", "经济", "文化", "能源", "网络"]

# Pseudo-dictionary blocks that only fill via async loaders in the real app.
LOADER_BLOCK_TYPES = {"llmLoader", "imageLoader", "forvoLoader"}


def _make_midict(config: dict[str, Any]) -> MagicMock:
    from anki_dictionary.core.database import DictDB

    midict = MagicMock()
    midict.db = DictDB()
    midict.config = config
    midict.conjugations = False
    midict.deinflect = False
    midict.sType.currentText.return_value = "Forward"
    midict.termHeaders = None
    midict.dictInt.theme_manager.is_dark = False
    midict.threadpool = MagicMock()
    return midict


def _selected_group(cfg: dict[str, Any], db: Any) -> dict[str, Any]:
    """The config's current group with real per-dict metadata (lang/font)."""
    name = cfg.get("currentGroup", "All")
    raw = cfg["DictionaryGroups"].get(name)
    if raw is None:
        raw = {"dictionaries": [], "font": False, "customFont": False}
    meta = {d["dict"]: d for d in db.getAllDictsWithLang()}
    dicts = [dict(meta.get(n, {"dict": n, "lang": ""})) for n in raw["dictionaries"]]
    group = {k: v for k, v in raw.items() if k != "dictionaries"}
    group["name"] = name
    group["dictionaries"] = dicts
    return group


def dump_term(term: str, out_dir: Path) -> str | None:
    with open(REPO / "config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    from anki_dictionary.core.search.pipeline import SearchPipeline

    midict = _make_midict(cfg)
    midict.dictInt.getSelectedDictGroup.return_value = _selected_group(cfg, midict.db)
    group = midict.dictInt.getSelectedDictGroup()

    pl = SearchPipeline(midict)
    doc, _cleaned, _single = pl.getStructuredResult(term, group, "")

    blocks = doc.get("blocks", [])
    before = len(blocks)
    doc["blocks"] = [b for b in blocks if b.get("type") not in LOADER_BLOCK_TYPES]
    sidebar = [
        d
        for d in doc.get("sidebar", [])
        if d.get("displayName") not in ("Images", "LLM", "Forvo")
    ]
    doc["sidebar"] = sidebar
    removed = before - len(doc["blocks"])
    if not doc["blocks"]:
        print(f"  {term}: no results (skipped)")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{term}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(
        f"  {term}: {len(doc['blocks'])} blocks ({removed} loader blocks stripped) -> {path.relative_to(REPO)}"
    )
    return str(path)


def main() -> int:
    terms = sys.argv[1:] or DEFAULT_TERMS
    out_dir = REPO / "web" / "dist" / "docs"
    written = 0
    for term in terms:
        if dump_term(term, out_dir):
            written += 1
    print(f"{written}/{len(terms)} docs dumped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
