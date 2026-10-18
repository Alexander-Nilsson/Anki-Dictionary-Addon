"""Prepare an isolated Anki base for generating docs-site media.

Creates a throwaway Anki profile (``TempCapture``) under a base directory with:

* the dictionary addon symlinked from this repo (so the real ``user_files``
  dictionaries/themes are used), and
* a driver addon (``driver_addon/``) that scripts the UI for capture.

The profile is local-only: no AnkiWeb account is configured, so nothing ever
signs in or syncs, and the developer's real Anki profiles are untouched.

Usage::

    uv run python scripts/docs_media/setup_env.py [BASE_DIR]
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from aqt.profiles import ProfileManager

REPO = Path(__file__).resolve().parents[2]
DEFAULT_BASE = str(Path(tempfile.gettempdir()) / "anki-docs-capture")
PROFILE = "TempCapture"
DRIVER_DIR = Path(__file__).resolve().parent / "driver_addon"

# Per-profile override of the addon's shipped defaults for capture runs:
# no global keyboard/mouse grabbing, no LLM calls (no local endpoint), and
# dictionary opens on startup.
ADDON_CONFIG = {
    "llm_enabled": False,
    "dictOnStart": False,
    "onetab": True,
}


def main() -> int:
    base = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE)
    (base / "addons21").mkdir(parents=True, exist_ok=True)

    link = base / "addons21" / REPO.name
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(REPO)

    driver_link = base / "addons21" / "zz_docs_capture_driver"
    if driver_link.is_symlink() or driver_link.exists():
        driver_link.unlink()
    driver_link.symlink_to(DRIVER_DIR)

    pm = ProfileManager(base)
    pm.setupMeta()
    pm.create(PROFILE)
    pm.meta["lastLoadedProfileName"] = PROFILE
    pm.meta["firstRun"] = False  # skip the language-chooser on first launch
    pm.meta["defaultLang"] = "en"
    pm.db.execute(
        "update profiles set data = ? where name = '_global'",
        pm._pickle(pm.meta),  # noqa: SLF001
    )
    pm.db.commit()

    addons_cfg_dir = base / PROFILE / "addons"
    addons_cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = addons_cfg_dir / f"{REPO.name}.json"
    cfg_path.write_text(json.dumps(ADDON_CONFIG, indent=2), encoding="utf-8")

    print(f"base={base}")
    print(f"profile={PROFILE}")
    print(f"addon link: {link} -> {REPO}")
    print(f"driver link: {driver_link} -> {DRIVER_DIR}")
    print(f"addon config override: {cfg_path}")
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
