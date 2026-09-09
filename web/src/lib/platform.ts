/**
 * Platform-adaptive modifier labels (⌘ on macOS, Ctrl on Linux/Windows).
 *
 * Python injects the authoritative `window.isMac` (Anki knows the OS; the
 * webview UA is spoofed to macOS so `navigator.userAgent` alone would always
 * report Mac). Fall back to navigator sniffing for the standalone preview.
 */

declare global {
  interface Window {
    isMac?: boolean;
    fefs?: number;
    dbfs?: number;
    sidebarWidth?: number;
  }
}

export function isMacPlatform(): boolean {
  if (typeof window !== "undefined" && typeof window.isMac === "boolean") {
    return window.isMac;
  }
  if (typeof navigator === "undefined") return false;
  const platform = navigator.platform ?? "";
  if (/mac/i.test(platform)) return true;
  const ua = navigator.userAgent ?? "";
  if (/macintosh|mac os x/i.test(ua)) return true;
  return false;
}

/** Modifier badge text: "⌘" on macOS, "Ctrl" elsewhere. */
export function modKey(): string {
  return isMacPlatform() ? "⌘" : "Ctrl";
}

/** e.g. "⌘K" on macOS, "Ctrl+K" on Linux/Windows. */
export function modKeyLabel(key: string): string {
  return isMacPlatform() ? `⌘${key}` : `Ctrl+${key}`;
}

/** Palette hint: "⌘K" on macOS, "Ctrl+K" elsewhere. */
export function paletteHint(): string {
  return modKeyLabel("K");
}
