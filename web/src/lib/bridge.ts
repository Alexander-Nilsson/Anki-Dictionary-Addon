/**
 * Python -> JS bridge.
 *
 * These globals are what the Python side calls via `AnkiWebView.eval(...)`
 * (see search/pipeline.py, search/coordinator.py, core/dictionary.py). They
 * drive the reactive Svelte shell instead of mutating the DOM imperatively.
 */
import { appendNewImages, initCompatGlobals, loadImageHtml } from "./compat";
import {
  addTab,
  resizer,
  scaleFont,
  toggleSidebar,
  ui,
} from "./tabs.svelte";
import { addCustomFont } from "./compat";
import type { DictDocument, HistoryEntry } from "./types";

/** Convert a Python "true"/"false" string or boolean to a boolean. */
function asBoolean(value: unknown): boolean {
  return value === true || value === "true";
}

/** Coerce Python's [[term, date], …] payload into HistoryEntry objects. */
function toHistory(payload: unknown): HistoryEntry[] {
  const list = Array.isArray(payload) ? (payload as unknown[]) : [];
  return list
    .map((h): HistoryEntry | null => {
      if (Array.isArray(h) && typeof h[0] === "string") {
        return { term: h[0], date: typeof h[1] === "string" ? h[1] : "" };
      }
      if (h && typeof (h as HistoryEntry).term === "string") {
        return {
          term: (h as HistoryEntry).term,
          date: (h as HistoryEntry).date ?? "",
        };
      }
      return null;
    })
    .filter((h): h is HistoryEntry => h !== null)
    .slice(0, 50);
}

/**
 * Install the full window API used by Python and by injected content.
 * Safe to call once at startup.
 */
export function initBridge(): void {
  initCompatGlobals();

  const w = window as unknown as Record<string, unknown>;
  Object.assign(w, {
    // Shell-level API called by Python. In Svelte mode the payload is a
    // structured search document; the legacy fallback page sends an HTML blob.
    addNewTab: (payload: unknown, term: unknown, singleTab: unknown, _id: unknown) => {
      if (payload && typeof payload === "object") {
        addTab(String(term ?? ""), payload as DictDocument, asBoolean(singleTab));
      } else {
        addTab(String(term ?? ""), String(payload ?? ""), asBoolean(singleTab));
      }
    },
    // Shared search history: Python ships [[term, date], …] (the model rows
    // persisted to _searchHistory.json). Drives the chrome dropdown autocomplete
    // and the sidebar "Recent searches" section together (U3).
    setSearchHistory: (payload: unknown) => {
      ui.history = toHistory(payload);
    },
    loadImageHtml,
    appendNewImages,
    addCustomFont,
    openSidebar: () => toggleSidebar(),
    scaleFont: (increase: unknown) => scaleFont(asBoolean(increase)),
    updateWelcomeVisibility: () => {
      // Welcome visibility is fully reactive in the Svelte shell; kept as a
      // no-op so the initial script injected by Python cannot fail.
    },
    resizer,
  });
}