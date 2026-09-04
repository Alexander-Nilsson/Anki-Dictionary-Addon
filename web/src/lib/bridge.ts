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
} from "./tabs.svelte";
import { addCustomFont } from "./compat";

/** Convert a Python "true"/"false" string or boolean to a boolean. */
function asBoolean(value: unknown): boolean {
  return value === true || value === "true";
}

/**
 * Install the full window API used by Python and by injected content.
 * Safe to call once at startup.
 */
export function initBridge(): void {
  initCompatGlobals();

  const w = window as unknown as Record<string, unknown>;
  Object.assign(w, {
    // Shell-level API called by Python.
    addNewTab: (html: unknown, term: unknown, singleTab: unknown, _id: unknown) => {
      addTab(String(term ?? ""), String(html ?? ""), asBoolean(singleTab));
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