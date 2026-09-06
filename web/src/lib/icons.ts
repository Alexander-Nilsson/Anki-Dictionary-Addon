/**
 * Inline SVG action icons shared by the block components.
 *
 * Mirrors `src/anki_dictionary/core/search/icons.py` — Python injects the same
 * markup for the blocks it renders dynamically (LLM results, Images, Forvo),
 * so every section shows identical tool icons. `stroke="currentColor"` keeps
 * them in the theme's text color. Keep the two files in sync when editing.
 */

const OPEN = (width: number): string =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">`;

const icon = (paths: string, width = 2): string => OPEN(width) + paths + "</svg>";

/** Entry tools (copy / send) — legacy glyphs ✂ ➞. */
export const CLIP_ICON = icon(
  '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
);
export const SEND_ICON = icon('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>');

/** Definition + dictionary navigation (legacy ▲ ▼ semantics): up / down. */
export const PREV_DEF_ICON = icon('<path d="M18 15l-6-6-6 6"/>', 2.4);
export const NEXT_DEF_ICON = icon('<path d="M6 9l6 6 6-6"/>', 2.4);
export const PREV_DICT_ICON = icon('<path d="M18 15l-6-6-6 6"/>', 2.4);
export const NEXT_DICT_ICON = icon('<path d="M6 9l6 6 6-6"/>', 2.4);

/** Filled play glyph for Forvo items. */
export const PLAY_ICON =
  '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true"><path d="M8 5.5v13a.6.6 0 0 0 .92.5l10.2-6.5a.6.6 0 0 0 0-1L8.92 5A.6.6 0 0 0 8 5.5z"/></svg>';
