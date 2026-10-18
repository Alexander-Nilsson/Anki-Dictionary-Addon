"""Run capture scenarios in the isolated Anki base and collect raw media.

Each scenario launches the real Anki binary against the throwaway base, lets
the driver addon (``driver_addon``) script the UI, waits for the ``DONE``
marker, and shuts Anki down. Requires a live Wayland session (grim +
wf-recorder).

Usage::

    uv run python scripts/docs_media/run.py [shots] [video-search] [...]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = os.environ.get(
    "DOCS_CAPTURE_BASE", str(Path(tempfile.gettempdir()) / "anki-docs-capture")
)
PROFILE = "TempCapture"
OUT_DIR = os.environ.get("DOCS_OUT_DIR", str(REPO / "site" / "media" / "raw"))
ALL_SCENARIOS = ["shots", "video-search", "video-themes", "video-exporter"]
TIMEOUT = 240  # seconds per scenario


def run_scenario(name: str) -> None:
    log_dir = Path(BASE) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"capture-{name}.log"
    log_path.unlink(missing_ok=True)
    env = {
        **os.environ,
        "DOCS_SCENARIO": name,
        "DOCS_OUT_DIR": OUT_DIR,
        # Anki's single-instance guard is keyed by getpass.getuser(); spoof it
        # so we never forward to (or hijack) the developer's own Anki.
        "USER": "docs-capture",
        "LOGNAME": "docs-capture",
        "LNAME": "docs-capture",
        "USERNAME": "docs-capture",
    }
    print(f"=== {name} -> {log_path} ===", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(  # noqa: S603
            ["anki", "-b", BASE, "-p", PROFILE],  # noqa: S607
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        deadline = time.monotonic() + TIMEOUT
        ok = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            if "DONE" in text and "docs-capture" in text:
                ok = True
                break
            time.sleep(1)
        if not ok:
            print(f"!! {name} did not finish cleanly (timeout={TIMEOUT}s)", flush=True)
        proc.terminate()
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    tail = [
        line
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if "docs-capture" in line
    ]
    print("\n".join(tail[-30:]), flush=True)


def main() -> int:
    scenarios = sys.argv[1:] or ALL_SCENARIOS
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    setup = REPO / "scripts" / "docs_media" / "setup_env.py"
    subprocess.run(  # noqa: S603
        [sys.executable, str(setup), BASE], check=True
    )
    for name in scenarios:
        run_scenario(name)
        time.sleep(2)
    print(f"raw media in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
