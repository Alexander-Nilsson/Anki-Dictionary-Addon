/**
 * Theme model shared by the appearance UI.
 *
 * Mirrors `ThemeColors` in `src/anki_dictionary/ui/themes.py`: fourteen hex
 * colors, no more, no less. Python owns persistence (`user_files/themes/
 * themes.json` + `active.json`); this module owns the presentation model —
 * how the keys are grouped for editing, which pairs must stay readable, and
 * the color math the previews and the contrast audit need.
 */

export interface ThemeColors {
  header_background: string;
  selector: string;
  header_text: string;
  search_term: string;
  border: string;
  anki_button_background: string;
  anki_button_text: string;
  tab_hover: string;
  current_tab_gradient_top: string;
  current_tab_gradient_bottom: string;
  example_highlight: string;
  definition_background: string;
  definition_text: string;
  pitch_accent_color: string;
}

export type ThemeKey = keyof ThemeColors;

/** Canonical key order — matches the dataclass field order in Python. */
export const THEME_KEYS: ThemeKey[] = [
  "header_background",
  "selector",
  "header_text",
  "search_term",
  "border",
  "anki_button_background",
  "anki_button_text",
  "tab_hover",
  "current_tab_gradient_top",
  "current_tab_gradient_bottom",
  "example_highlight",
  "definition_background",
  "definition_text",
  "pitch_accent_color",
];

export interface KeyMeta {
  key: ThemeKey;
  label: string;
  hint: string;
}

export interface KeyGroup {
  id: string;
  label: string;
  keys: KeyMeta[];
}

/** Editing groups: colors that are seen together are edited together. */
export const KEY_GROUPS: KeyGroup[] = [
  {
    id: "window",
    label: "Window",
    keys: [
      { key: "header_background", label: "Background", hint: "Window and header fill" },
      { key: "header_text", label: "Text", hint: "Headers, labels, controls" },
      { key: "border", label: "Border", hint: "Dividers and control outlines" },
      { key: "selector", label: "Sidebar / dropdowns", hint: "Secondary surfaces" },
    ],
  },
  {
    id: "accent",
    label: "Accents",
    keys: [
      { key: "search_term", label: "Searched term", hint: "Highlighted term and focus rings" },
      { key: "example_highlight", label: "Example sentence", hint: "Example background wash" },
      { key: "pitch_accent_color", label: "Pitch accent", hint: "Alternate readings" },
    ],
  },
  {
    id: "tabs",
    label: "Tabs & buttons",
    keys: [
      { key: "current_tab_gradient_top", label: "Active tab (top)", hint: "Gradient start" },
      { key: "current_tab_gradient_bottom", label: "Active tab (bottom)", hint: "Gradient end" },
      { key: "tab_hover", label: "Tab hover", hint: "Hovered tab fill" },
      { key: "anki_button_background", label: "Button fill", hint: "Export buttons" },
      { key: "anki_button_text", label: "Button text", hint: "Export button label" },
    ],
  },
  {
    id: "content",
    label: "Definitions",
    keys: [
      { key: "definition_background", label: "Card background", hint: "Definition block fill" },
      { key: "definition_text", label: "Card text", hint: "Definition body copy" },
    ],
  },
];

/** Foreground/background pairs the UI audits for WCAG contrast. */
export const CONTRAST_PAIRS: { fg: ThemeKey; bg: ThemeKey; label: string }[] = [
  { fg: "header_text", bg: "header_background", label: "Header text" },
  { fg: "header_text", bg: "selector", label: "Sidebar text" },
  { fg: "definition_text", bg: "definition_background", label: "Definition text" },
  { fg: "search_term", bg: "definition_background", label: "Searched term" },
  { fg: "pitch_accent_color", bg: "definition_background", label: "Pitch accent" },
  { fg: "anki_button_text", bg: "anki_button_background", label: "Button label" },
];

// ── color math ───────────────────────────────────────────────────────────────

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

/** Parse `#rgb` / `#rrggbb` (and bare hex). Returns null when unparseable. */
export function parseHex(value: string): Rgb | null {
  const hex = (value ?? "").trim().replace(/^#/, "");
  const full =
    hex.length === 3
      ? hex
          .split("")
          .map((c) => c + c)
          .join("")
      : hex;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) return null;
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  };
}

export function isValidHex(value: string): boolean {
  return parseHex(value) !== null;
}

/** Normalise any accepted form to `#rrggbb` (lowercase); "" when invalid. */
export function normalizeHex(value: string): string {
  const rgb = parseHex(value);
  return rgb ? toHex(rgb) : "";
}

export function toHex({ r, g, b }: Rgb): string {
  const part = (n: number) =>
    Math.max(0, Math.min(255, Math.round(n)))
      .toString(16)
      .padStart(2, "0");
  return `#${part(r)}${part(g)}${part(b)}`;
}

export function rgba(value: string, alpha: number): string {
  const c = parseHex(value) ?? { r: 0, g: 0, b: 0 };
  return `rgba(${c.r}, ${c.g}, ${c.b}, ${alpha})`;
}

/** WCAG relative luminance (0 = black, 1 = white). */
export function luminance(value: string): number {
  const c = parseHex(value);
  if (!c) return 1;
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
}

/** WCAG contrast ratio between two colors (1 – 21). */
export function contrastRatio(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

export type ContrastGrade = "AAA" | "AA" | "AA Large" | "Fail";

export function grade(ratio: number): ContrastGrade {
  if (ratio >= 7) return "AAA";
  if (ratio >= 4.5) return "AA";
  if (ratio >= 3) return "AA Large";
  return "Fail";
}

/** Same rule Python's `ThemeManager.is_dark` uses, so badges agree with Qt. */
export function isDarkTheme(theme: ThemeColors): boolean {
  const c = parseHex(theme.header_background);
  if (!c) return false;
  return (0.299 * c.r + 0.587 * c.g + 0.114 * c.b) / 255 < 0.5;
}

/** Linear blend between two colors; `t` 0 → a, 1 → b. */
export function mix(a: string, b: string, t: number): string {
  const ca = parseHex(a) ?? { r: 0, g: 0, b: 0 };
  const cb = parseHex(b) ?? { r: 255, g: 255, b: 255 };
  return toHex({
    r: ca.r + (cb.r - ca.r) * t,
    g: ca.g + (cb.g - ca.g) * t,
    b: ca.b + (cb.b - ca.b) * t,
  });
}

/** Move a color toward white (positive) or black (negative) by `amount`. */
export function shade(value: string, amount: number): string {
  return amount >= 0 ? mix(value, "#ffffff", amount) : mix(value, "#000000", -amount);
}

/** Pick whichever of black/white reads better on `bg`. */
export function readableOn(bg: string): string {
  return contrastRatio("#ffffff", bg) >= contrastRatio("#111111", bg)
    ? "#ffffff"
    : "#111111";
}

/**
 * Derive a complete, readable theme from just a background and an accent.
 *
 * Every surface is a luminance step away from the background (so the ramp
 * works for light and dark bases alike) and every foreground is nudged until
 * it clears WCAG AA against the surface it sits on.
 */
export function deriveTheme(background: string, accent: string): ThemeColors {
  const bg = normalizeHex(background) || "#ffffff";
  const acc = normalizeHex(accent) || "#4f6ef7";
  const dark = luminance(bg) < 0.4;
  const step = (n: number) => shade(bg, dark ? n : -n);

  const text = ensureContrast(dark ? shade(bg, 0.75) : shade(bg, -0.78), bg, 7);
  const surface = step(0.05);
  const card = dark ? step(0.02) : bg;

  return {
    header_background: bg,
    selector: surface,
    header_text: text,
    search_term: ensureContrast(acc, card, 4.5),
    border: step(0.16),
    anki_button_background: step(0.08),
    anki_button_text: ensureContrast(text, step(0.08), 4.5),
    tab_hover: step(0.12),
    current_tab_gradient_top: step(0.1),
    current_tab_gradient_bottom: bg,
    example_highlight: mix(bg, acc, dark ? 0.22 : 0.18),
    definition_background: card,
    definition_text: ensureContrast(dark ? shade(bg, 0.68) : shade(bg, -0.72), card, 7),
    pitch_accent_color: ensureContrast(rotateHue(acc, 150), card, 4.5),
  };
}

/**
 * Nudge `fg` lighter or darker (away from `bg`) until it reaches `target`
 * contrast, giving up at pure white/black rather than looping forever.
 */
export function ensureContrast(fg: string, bg: string, target: number): string {
  let out = normalizeHex(fg) || "#000000";
  if (contrastRatio(out, bg) >= target) return out;
  const towardWhite = luminance(bg) < 0.5;
  for (let i = 0; i < 20; i++) {
    out = shade(out, towardWhite ? 0.06 : -0.06);
    if (contrastRatio(out, bg) >= target) break;
  }
  return out;
}

/** Rotate hue by `deg`, keeping saturation and lightness — used for accents. */
export function rotateHue(value: string, deg: number): string {
  const c = parseHex(value);
  if (!c) return value;
  const [h, s, l] = rgbToHsl(c);
  return hslToHex((h + deg / 360 + 1) % 1, s, l);
}

function rgbToHsl({ r, g, b }: Rgb): [number, number, number] {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return [0, 0, l];
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;
  return [h, s, l];
}

function hslToHex(h: number, s: number, l: number): string {
  if (s === 0) {
    const v = l * 255;
    return toHex({ r: v, g: v, b: v });
  }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const channel = (t: number) => {
    let tc = t;
    if (tc < 0) tc += 1;
    if (tc > 1) tc -= 1;
    if (tc < 1 / 6) return p + (q - p) * 6 * tc;
    if (tc < 1 / 2) return q;
    if (tc < 2 / 3) return p + (q - p) * (2 / 3 - tc) * 6;
    return p;
  };
  return toHex({
    r: channel(h + 1 / 3) * 255,
    g: channel(h) * 255,
    b: channel(h - 1 / 3) * 255,
  });
}

// ── (de)serialisation ────────────────────────────────────────────────────────

/** Human label for a stored theme id (`catppuccin_mocha` → Catppuccin Mocha). */
export function themeLabel(name: string): string {
  return name
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const FALLBACK: ThemeColors = {
  header_background: "#ffffff",
  selector: "#f8f9fa",
  header_text: "#212529",
  search_term: "#007bff",
  border: "#dee2e6",
  anki_button_background: "#f8f9fa",
  anki_button_text: "#212529",
  tab_hover: "#e9ecef",
  current_tab_gradient_top: "#ffffff",
  current_tab_gradient_bottom: "#e9ecef",
  example_highlight: "#fff3cd",
  definition_background: "#ffffff",
  definition_text: "#212529",
  pitch_accent_color: "#dc3545",
};

/** Coerce arbitrary JSON into a complete theme, filling gaps with defaults. */
export function coerceTheme(raw: unknown): ThemeColors {
  const src = (raw ?? {}) as Record<string, unknown>;
  const out = { ...FALLBACK };
  for (const key of THEME_KEYS) {
    const v = src[key];
    if (typeof v === "string" && isValidHex(v)) out[key] = normalizeHex(v);
  }
  return out;
}

/** True when every key of two themes matches (used for the dirty check). */
export function themesEqual(a: ThemeColors, b: ThemeColors): boolean {
  return THEME_KEYS.every((k) => a[k] === b[k]);
}

export const DEFAULT_THEME = FALLBACK;
