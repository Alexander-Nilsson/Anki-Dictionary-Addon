/**
 * JS -> Python bridge.
 *
 * `pycmd(...)` is injected by Anki's AnkiWebView; every `pycmd("...")` call is
 * routed to `MIDict.handleDictAction` on the Python side. This module centralises
 * the few commands the web UI itself issues (font saving, term updates, the
 * initial "page loaded" handshake) and guards against the bridge not being
 * ready yet.
 */
import type { FontSizes } from "./types";

/** Send a raw command to Python via the Anki bridge. */
export function pycmd(command: string): void {
  if (typeof window.pycmd === "function") {
    try {
      window.pycmd(command);
    } catch (err) {
      console.error("pycmd failed:", command, err);
    }
  } else {
    console.warn("pycmd not available yet:", command);
  }
}

export const CMD = {
  pageLoaded: () => "AnkiDictionaryLoaded",
  updateTerm: (term: string) => `updateTerm:${term}`,
  saveFontSizes: ({ fefs, dbfs }: FontSizes) => `saveFS:${fefs}:${dbfs}`,
  fieldsSetting: (dictName: string, fields: string[]) =>
    `fieldsSetting:${JSON.stringify({ dictName, fields })}`,
  overwriteSetting: (name: string, type: string) =>
    `overwriteSetting:${JSON.stringify({ name, type })}`,
  clipped: (text: string) => `clipped:${text.replace("&lt", "<").replace("&gt;", ">")}`,
  clippedImages: (urls: string[]) => `clipped_images:${JSON.stringify(urls)}`,
  sendToField: (dictName: string, text: string) =>
    `sendToField:${dictName}\u25f3\u25f4${text}`,
  sendImgToField: (urls: string[]) => `sendImgToField:${JSON.stringify(urls)}`,
  sendAudioToField: (url: string) => `sendAudioToField:${url}`,
  playAudio: (url: string) => `playAudio:${url}`,
  addDef: (dictName: string, word: string, text: string) =>
    `addDef:${dictName}\u25f3\u25f4${word}\u25f3\u25f4${text}`,
  audioExport: (word: string, url: string) =>
    `audioExport:${word}\u25f3\u25f4${url}`,
  imgExport: (word: string, urls: string[]) =>
    `imgExport:${word}\u25f3\u25f4${JSON.stringify(urls)}`,
  getMoreImages: (term: string) => `getMoreImages::${term}`,
  /** Persist the drag-resized sidebar width (px). */
  saveSidebarWidth: (width: number) => `saveSidebarWidth:${Math.round(width)}`,
  /** Open the dictionary settings window (contains the usage guide). */
  openSettings: () => "openSettings",
  // In-web search chrome (Phase 2.5): search + history + group switching.
  searchTerm: (term: string) => `searchTerm:${term}`,
  getSearchHistory: () => "getSearchHistory:",
  getGroups: () => "getGroups:",
  setGroup: (name: string) => `setGroup:${name}`,
} as const;

/**
 * Wait for the Anki bridge to be injected, then announce the page is ready
 * (mirrors the legacy `awaitPycmdToLoad` in dictionary.js).
 */
export function awaitPycmdToLoad(): void {
  const timer = setInterval(() => {
    if (typeof window.pycmd === "function") {
      clearInterval(timer);
      pycmd(CMD.pageLoaded());
    }
  }, 5);
}