"""Throwaway driver addon: scripts the dictionary UI to generate docs media.

Loaded ONLY inside the isolated capture base created by ``setup_env.py``
(see ``scripts/docs_media/``). It opens the real dictionary/settings/exporter
windows, runs searches against the real dictionary database, and captures
screens (grim) and clips (wf-recorder) on a live Wayland session.

Environment:
    DOCS_SCENARIO  shots | video-search | video-themes | video-exporter
    DOCS_OUT_DIR   output directory (PNGs / MP4s)
    DOCS_GEOM      grim/wf-recorder geometry, default "0,0 1920x1080"
"""

import json
import os
import signal
import subprocess
import tempfile
import time

from aqt import gui_hooks, mw
from aqt.qt import QApplication, QTimer

SCENARIO = os.environ.get("DOCS_SCENARIO", "shots")
OUT_DIR = os.environ.get(
    "DOCS_OUT_DIR", os.path.join(tempfile.gettempdir(), "anki-docs-media")
)
GEOM = os.environ.get("DOCS_GEOM", "0,0 1920x1080")

TERM_A = "\u7535\u8111"  # 电脑
TERM_B = "\u6c34"  # 水
TERM_C = "\u4f60\u597d"  # 你好

_state = {"orig_theme": "light", "rec": None}


def log(msg: str) -> None:
    print(f"[docs-capture] {msg}", flush=True)


def dic():
    return getattr(mw, "ankiDictionary", False) or None


def fullscreen(widget) -> None:
    widget.showFullScreen()
    widget.raise_()
    widget.activateWindow()
    QApplication.processEvents()


def webview_of(widget):
    from aqt.webview import AnkiWebView

    return widget.findChild(AnkiWebView)


def js(widget, expr, callback=None):
    wv = webview_of(widget)
    if wv is None:
        if callback:
            callback(None)
        return
    wv.page().runJavaScript(expr, callback if callback else lambda _v: None)


def snap(name: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    subprocess.run(["grim", "-g", GEOM, path], check=False)
    log(f"snap {path}")


def set_theme(name: str) -> None:
    d = dic()
    d.theme_manager.set_active_theme(name)
    d.refresh_application_theme()


def search(term: str) -> None:
    dic().initSearch(term, source="manual")


# ── step engine ──────────────────────────────────────────────────────────────
# A step is a callable ``step(done)``; it must call ``done()`` when finished.


def sleep(ms: int):
    def step(done):
        QTimer.singleShot(ms, done)

    return step


def act(fn):
    def step(done):
        fn()
        done()

    return step


def poll(widget_expr_getter, expr, timeout=20000):
    """Wait until ``expr`` is truthy inside the widget's webview."""

    def step(done):
        t0 = time.monotonic()

        def check():
            widget = widget_expr_getter()
            if widget is None:
                QTimer.singleShot(300, check)
                return

            def cb(v):
                if v:
                    done()
                    return
                if time.monotonic() - t0 > timeout / 1000:
                    log(f"poll timeout: {expr[:60]}")
                    done()
                    return
                QTimer.singleShot(250, check)

            js(widget, expr, cb)

        check()

    return step


def dic_getter():
    return dic()


def type_term(term: str, delay=170):
    js_tpl = (
        "(function(v){const el=document.querySelector("
        "'input[aria-label^=\"Search\"]');if(!el)return false;"
        "el.focus();el.value=v;"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "return true})("
    )

    def step(done):
        chars = list(term)
        acc = ""

        def tick():
            nonlocal acc
            if not chars:
                QTimer.singleShot(400, done)
                return
            acc += chars.pop(0)
            js(dic(), js_tpl + json.dumps(acc) + ")", None)
            QTimer.singleShot(delay, tick)

        tick()

    return step


def rec(name: str):
    def step(done):
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"{name}.mp4")
        _state["rec"] = subprocess.Popen(  # noqa: S603
            ["wf-recorder", "-g", GEOM, "-f", path],  # noqa: S607
            stderr=subprocess.DEVNULL,
        )
        log(f"recording {path}")
        done()

    return step


def rec_stop():
    def step(done):
        p = _state.pop("rec", None)
        if p is None:
            done()
            return
        p.send_signal(signal.SIGINT)

        def reaper():
            if p.poll() is None:
                QTimer.singleShot(200, reaper)
                return
            log("recording stopped")
            done()

        reaper()

    return step


def run_steps(steps, i=0):
    if i >= len(steps):
        finish()
        return

    def nxt():
        run_steps(steps, i + 1)

    step = steps[i]
    try:
        step(nxt)
    except Exception as exc:  # noqa: BLE001 - keep capturing past one bad step
        import traceback

        traceback.print_exc()
        log(f"step failed: {exc}")
        QTimer.singleShot(300, nxt)


def finish() -> None:
    try:
        set_theme(_state["orig_theme"])
    except Exception:  # noqa: BLE001, S110
        pass
    log("DONE")
    time.sleep(0.4)
    os._exit(0)


# ── scenarios ────────────────────────────────────────────────────────────────

APP_READY = (
    "!!(document.getElementById('app')"
    " && document.getElementById('app').childElementCount>1)"
)
DEFS_READY = "document.querySelectorAll('.definitionBlock').length>0"

CLICK_TAB = (
    "(function(t){const b=[...document.querySelectorAll('button')]"
    ".find(x=>x.textContent.trim().toLowerCase().startsWith(t));"
    "if(b){b.click();return true}return false})('%s')"
)


def base_open_steps():
    def prep(done):
        if dic() is None:
            mw.dictionaryInit()
        _state["orig_theme"] = dic().theme_manager.current_theme
        done()

    return [
        act(prep),
        sleep(1500),
        act(lambda: fullscreen(dic())),
        sleep(1200),
        poll(dic_getter, APP_READY),
        sleep(1500),
    ]


def get_settings():
    return getattr(mw, "dictSettings", None)


def open_settings() -> None:
    from anki_dictionary.ui.main_window import openDictionarySettings

    openDictionarySettings()
    fullscreen(get_settings())


def theme_shots():
    steps = []
    for idx, theme in enumerate(
        ["tokyo_night", "catppuccin_mocha", "gruvbox", "nord", "catppuccin_latte"]
    ):
        steps += [
            act(lambda t=theme: set_theme(t)),
            sleep(900),
            poll(dic_getter, APP_READY),
            act(lambda: search(TERM_A)),
            poll(dic_getter, DEFS_READY),
            sleep(4500),
            act(lambda n=f"s{3 + idx:02d}-search-{theme}": snap(n)),
        ]
    return steps


def shots_steps():
    return (
        base_open_steps()
        + [
            act(lambda: set_theme("light")),
            sleep(900),
            poll(dic_getter, APP_READY),
            sleep(800),
            act(lambda: snap("s01-welcome")),
            act(lambda: search(TERM_A)),
            poll(dic_getter, DEFS_READY),
            sleep(5000),
            act(lambda: snap("s02-search-light")),
        ]
        + theme_shots()
        + [
            act(lambda: dic().setTabMode(False)),
            sleep(600),
            act(lambda: search(TERM_B)),
            poll(dic_getter, DEFS_READY),
            sleep(3000),
            act(lambda: snap("s08-multitab")),
            # settings window
            act(open_settings),
            sleep(2500),
            poll(get_settings, APP_READY),
            act(lambda: snap("s09-settings")),
            act(lambda: js(get_settings(), CLICK_TAB % "appearance")),
            sleep(1800),
            act(lambda: snap("s10-settings-theme")),
            act(lambda: get_settings().hide()),
            sleep(500),
            # card exporter
            act(exporter_open),
            sleep(1800),
            act(lambda: snap("s11-exporter")),
        ]
    )


def exporter_open() -> None:
    d = dic()
    d.card_handler.addDefToExportWindow(
        "Cedict",
        TERM_A,
        f"<span class='wrap'>{TERM_A} [di\u00e0n n\u01ceo]</span>"
        "<br/>electric head<br/>computer<br/>notebook, laptop",
    )
    d.card_handler.addDefToExportWindow(
        "Cedict",
        TERM_C,
        "<span class='wrap'>\u4f60\u597d [n\u01d0 h\u01ceo]</span><br/>hello<br/>hey",
    )
    fullscreen(d.dict.addWindow.window)


def video_search_steps():
    return base_open_steps() + [
        rec("v01-search"),
        sleep(900),
        type_term(TERM_C),
        act(lambda: search(TERM_C)),
        poll(dic_getter, DEFS_READY),
        sleep(5000),
        act(lambda: js(dic(), "window.scrollBy({top:260,behavior:'smooth'})")),
        sleep(1500),
        rec_stop(),
    ]


def video_themes_steps():
    items = []
    for theme in ["catppuccin_mocha", "gruvbox", "nord", "catppuccin_latte", "light"]:
        items += [
            act(lambda t=theme: set_theme(t)),
            sleep(900),
            poll(dic_getter, APP_READY),
            act(lambda: search(TERM_A)),
            poll(dic_getter, DEFS_READY),
            sleep(1400),
        ]
    return (
        base_open_steps()
        + [
            act(lambda: set_theme("tokyo_night")),
            sleep(900),
            poll(dic_getter, APP_READY),
            act(lambda: search(TERM_A)),
            poll(dic_getter, DEFS_READY),
            sleep(2500),
            rec("v02-themes"),
        ]
        + items
        + [rec_stop()]
    )


def video_exporter_steps():
    return base_open_steps() + [
        rec("v03-exporter"),
        sleep(800),
        type_term(TERM_A),
        act(lambda: search(TERM_A)),
        poll(dic_getter, DEFS_READY),
        sleep(4000),
        act(exporter_open),
        sleep(2200),
        rec_stop(),
    ]


SCENARIOS = {
    "shots": shots_steps,
    "video-search": video_search_steps,
    "video-themes": video_themes_steps,
    "video-exporter": video_exporter_steps,
}


def start(_unused=None) -> None:
    log(f"scenario={SCENARIO} out={OUT_DIR}")
    steps = SCENARIOS.get(SCENARIO, shots_steps)()
    QTimer.singleShot(1500, lambda: run_steps(steps))


gui_hooks.profile_did_open.add(start)
