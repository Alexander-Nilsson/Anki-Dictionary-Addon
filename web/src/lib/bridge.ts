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

/** Apply the unified header payload (`pushHeaderState`) to the store. */
function applyHeaderState(payload: unknown): void {
  const data = (payload ?? {}) as {
    groups?: unknown;
    current?: unknown;
    searchModes?: unknown;
    searchMode?: unknown;
    deinflect?: unknown;
    singleTab?: unknown;
    source?: unknown;
    clipboardPaused?: unknown;
    target?: unknown;
    showTarget?: unknown;
  };
  if (Array.isArray(data.groups)) {
    const gs = data.groups.filter((g): g is string => typeof g === "string");
    if (gs.length > 0) ui.groups = gs;
  }
  if (typeof data.current === "string" && data.current) ui.group = data.current;
  if (Array.isArray(data.searchModes)) {
    const ms = data.searchModes.filter((m): m is string => typeof m === "string");
    if (ms.length > 0) ui.searchModes = ms;
  }
  if (typeof data.searchMode === "string" && data.searchMode) {
    ui.searchMode = data.searchMode;
  }
  if (typeof data.deinflect === "boolean") ui.deinflect = data.deinflect;
  if (typeof data.singleTab === "boolean") ui.singleTab = data.singleTab;
  if (typeof data.source === "string") ui.searchSource = data.source;
  if (typeof data.clipboardPaused === "boolean") {
    ui.clipboardPaused = data.clipboardPaused;
  }
  if (typeof data.target === "string") ui.target = data.target;
  if (typeof data.showTarget === "boolean") ui.showTarget = data.showTarget;
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
    // Unified header state (S1): one payload drives Chrome + palette.
    // Legacy per-slice callbacks kept for older bundles.
    setHeaderState: (payload: unknown) => {
      applyHeaderState(payload);
    },
    setGroups: (payload: unknown) => {
      const data = (payload ?? {}) as { groups?: unknown; current?: unknown };
      applyHeaderState({ groups: data.groups, current: data.current });
    },
    setSearchModes: (payload: unknown) => {
      const data = (payload ?? {}) as { modes?: unknown; current?: unknown };
      applyHeaderState({ searchModes: data.modes, searchMode: data.current });
    },
    setSearchSource: (payload: unknown) => {
      if (typeof payload === "string") ui.searchSource = payload;
    },
    setSearchStatus: (payload: unknown) => {
      const data = (payload ?? {}) as {
        source?: unknown;
        clipboardPaused?: unknown;
      };
      if (typeof data.source === "string") ui.searchSource = data.source;
      if (typeof data.clipboardPaused === "boolean") {
        ui.clipboardPaused = data.clipboardPaused;
      }
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