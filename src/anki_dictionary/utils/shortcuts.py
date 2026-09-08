"""Platform-adaptive shortcut labels.

The same physical shortcuts use different modifier names per OS: macOS
shows ``⌘`` (Command) while Linux and Windows show ``Ctrl``. This module
is the single source of truth so the Qt menu text, the welcome-screen
``key__button`` badges and the Svelte chrome stay in sync.

Kept dependency-free (takes ``is_mac`` as a parameter) so both
``ui.main_window`` and ``core.dictionary`` can use it without import cycles.
"""

MOD_KEY_MAC = "\u2318"
MOD_KEY_DEFAULT = "Ctrl"


def get_mod_key(is_mac: bool) -> str:
    """Return the modifier label for the current platform."""
    return MOD_KEY_MAC if is_mac else MOD_KEY_DEFAULT


def format_menu_shortcut(key: str, is_mac: bool) -> str:
    """Format a menu shortcut suffix, e.g. ``⌘W`` on macOS vs ``(Ctrl+W)`` elsewhere."""
    if is_mac:
        return f"{MOD_KEY_MAC}{key}"
    return f"(Ctrl+{key})"


def render_shortcut_badges(html: str, is_mac: bool) -> str:
    """Replace ``{{MOD_KEY}}`` placeholders in welcome-screen HTML."""
    return html.replace("{{MOD_KEY}}", get_mod_key(is_mac))
