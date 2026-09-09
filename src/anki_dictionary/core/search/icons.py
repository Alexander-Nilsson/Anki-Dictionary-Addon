"""Inline SVG action icons for Python-rendered result HTML.

Mirrors ``web/src/lib/icons.ts`` — the Svelte components render the same
markup for blocks they own, and these strings keep the blocks that Python
injects dynamically (LLM results, Images, Forvo, legacy page) visually
identical. ``stroke="currentColor"`` means the icons follow the theme's text
color automatically. Keep the two files in sync when editing.
"""

from __future__ import annotations

_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
)

# The filled play glyph used by Forvo items (fill, not stroke).
PLAY = (
    '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">'
    '<path d="M8 5.5v13a.6.6 0 0 0 .92.5l10.2-6.5a.6.6 0 0 0 0-1L8.92 5A.6.6 0 0 0 8 5.5z"/>'
    "</svg>"
)


def _icon(paths: str, width: float = 2) -> str:
    return _SVG_OPEN.format(width=width) + paths + "</svg>"


#: Mirrors the legacy glyph set (✂ ➞ ▲ ▼) per block class.
ACTION_ICONS: dict[str, str] = {
    # Entry tools
    "clip": _icon(
        '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'
    ),
    "send": _icon('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>'),
    # Definition navigation (between entries): up / down
    "prev_def": _icon('<path d="M18 15l-6-6-6 6"/>', 2.4),
    "next_def": _icon('<path d="M6 9l6 6 6-6"/>', 2.4),
    # Dictionary navigation (between sections): up / down (legacy ▲ ▼)
    "prev_dict": _icon('<path d="M18 15l-6-6-6 6"/>', 2.4),
    "next_dict": _icon('<path d="M6 9l6 6 6-6"/>', 2.4),
    # Forvo playback
    "play": PLAY,
}


def action_icon(name: str) -> str:
    return ACTION_ICONS.get(name, "")
