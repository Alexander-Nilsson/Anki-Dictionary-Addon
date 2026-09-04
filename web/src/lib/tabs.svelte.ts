/**
 * Reactive state for the dictionary shell (Svelte 5 runes).
 *
 * The shell owns tabs, the welcome screen, sidebar state and font scaling.
 * Tab *content* is still Python-generated HTML (Phase 1 boundary) injected via
 * `{@html}`; later phases will replace it with structured data + components.
 */
import { CMD, pycmd } from "./pycmd";
import type { Tab } from "./types";

/**
 * Module-scope shared store. A class instance is the idiomatic Svelte 5 way to
 * share reactive state across modules (exported bindings cannot themselves be
 * reassigned, but `ui.<field>` mutations are fine).
 */
class DictionaryUIStore {
  tabs = $state<Tab[]>([]);
  activeId = $state<number | null>(null);
  sidebarOpened = $state(false);
  fefs = $state(12);
  dbfs = $state(22);
  welcomeHtml = $state("");
}

export const ui = new DictionaryUIStore();

let nextId = 1;

// ── tabs ────────────────────────────────────────────

/**
 * Add (or, in single-tab mode, replace) a tab. Mirrors the legacy
 * `addNewTab(html, term, singleTab, id)` semantics so Python callers are
 * unaffected.
 */
export function addTab(term: string, html: string, singleTab: boolean): void {
  if (html === undefined || html === null) {
    console.warn("addTab: called without html, skipping");
    return;
  }
  const cleanTerm = term ?? "";

  if (singleTab && ui.tabs.length > 0) {
    // Replace the content of the active tab (or the last one if none active).
    const idx = ui.tabs.findIndex((t) => t.id === ui.activeId);
    const target = idx >= 0 ? idx : ui.tabs.length - 1;
    ui.tabs[target] = { ...ui.tabs[target], term: cleanTerm, html };
    return;
  }

  if (!singleTab) {
    // Legacy behaviour: searching again opens a new tab; a leftover "Welcome"
    // tab (only relevant to older addon versions) is closed first.
    attemptCloseFirstTab();
  }

  const tab: Tab = { id: nextId++, term: cleanTerm, html };
  ui.tabs.push(tab);
  ui.activeId = tab.id;
}

export function closeTab(id: number): void {
  const idx = ui.tabs.findIndex((t) => t.id === id);
  if (idx === -1) return;
  const wasActive = id === ui.activeId;
  ui.tabs.splice(idx, 1);
  if (wasActive) {
    if (ui.tabs.length === 0) {
      ui.activeId = null;
    } else {
      // Prefer the tab to the left, like the legacy focusAnotherTab.
      ui.activeId = ui.tabs[Math.max(idx - 1, 0)].id;
    }
  }
}

export function activate(id: number): void {
  ui.activeId = id;
}

/** Search result replaced the tab's content; send the term back to Python. */
export function updateTermFromTab(id: number): void {
  const tab = ui.tabs.find((t) => t.id === id);
  if (tab) pycmd(CMD.updateTerm(tab.term));
}

/** If the active tab is a leftover "Welcome" tab, close it (legacy compat). */
export function attemptCloseFirstTab(): void {
  const active = ui.tabs.find((t) => t.id === ui.activeId);
  if (active && active.term === "Welcome") closeTab(active.id);
}

// ── sidebar ─────────────────────────────────────────

/** Apply the global sidebar state to every tab's injected content. */
export function applySidebarState(): void {
  for (const content of Array.from(
    document.querySelectorAll<HTMLElement>(".tabContent"),
  )) {
    const isActive = content.style.display === "block";
    const sidebar = content.querySelector<HTMLElement>(".definitionSideBar");
    const mainDisplay = content.querySelector<HTMLElement>(".mainDictDisplay");
    if (ui.sidebarOpened) {
      if (sidebar) {
        sidebar.style.display = isActive ? "block" : "none";
        sidebar.classList.add("sidebarOpenedSideBar");
      }
      mainDisplay?.classList.add("sidebarOpenedDisplay");
    } else {
      if (sidebar) {
        sidebar.style.display = "none";
        sidebar.classList.remove("sidebarOpenedSideBar");
      }
      mainDisplay?.classList.remove("sidebarOpenedDisplay");
    }
  }
}

export function toggleSidebar(): void {
  ui.sidebarOpened = !ui.sidebarOpened;
  applySidebarState();
}

// ── fonts ───────────────────────────────────────────

/** Push fefs/dbfs into CSS variables + the fontSpecs style element. */
export function applyFontSizes(): void {
  const root = document.documentElement;
  root.style.setProperty("--font-size-base", `${ui.fefs}px`);
  root.style.setProperty("--font-size-xs", `${Math.max(ui.fefs - 2, 8)}px`);
  root.style.setProperty("--font-size-sm", `${Math.max(ui.fefs - 1, 9)}px`);
  root.style.setProperty("--font-size-md", `${ui.dbfs}px`);
  root.style.setProperty("--font-size-lg", `${ui.dbfs + 2}px`);
  root.style.setProperty("--font-size-xl", `${ui.dbfs + 4}px`);
  root.style.setProperty("--font-size-2xl", `${ui.dbfs + 6}px`);
  root.style.setProperty("--font-size-3xl", `${ui.dbfs + 10}px`);

  const fontSpecs = document.getElementById("fontSpecs");
  if (fontSpecs) {
    fontSpecs.textContent =
      `.foundEntriesList{font-size: ${ui.fefs}px;}` +
      `.termPronunciation,.definitionBlock{font-size: ${ui.dbfs}px; white-space: pre-line;}`;
  }
  document.body.style.fontSize = `${ui.fefs}px`;
}

export function scaleFont(increase: boolean): void {
  if (increase) {
    ui.fefs += 1;
    ui.dbfs += 1;
  } else {
    ui.fefs = Math.max(ui.fefs - 1, 8);
    ui.dbfs = Math.max(ui.dbfs - 1, 8);
  }
  applyFontSizes();
  pycmd(CMD.saveFontSizes({ fefs: ui.fefs, dbfs: ui.dbfs }));
}

// ── layout ──────────────────────────────────────────

/** Recompute #defBox / sidebar heights (mirrors legacy `resizer()`). */
export function resizer(): void {
  const tabsElement = document.getElementById("tabs");
  const defBox = document.getElementById("defBox");
  if (!tabsElement || !defBox) return;

  let height = 0;
  if (tabsElement.offsetHeight !== undefined && tabsElement.offsetHeight !== null) {
    height = tabsElement.offsetHeight;
  }
  const wHeight = window.innerHeight || 600;
  defBox.style.top = `${height}px`;
  defBox.style.height = `${Math.max(wHeight - height, 100)}px`;

  for (const sb of Array.from(
    document.getElementsByClassName("definitionSideBar"),
  ) as HTMLElement[]) {
    sb.style.height = `${Math.max(wHeight - 14 - height, 100)}px`;
  }
}

export function initFromWindow(): void {
  // Font sizes injected by Python (getHTMLURL) via the FONT_SIZES placeholder.
  if (typeof window.fefs === "number" && Number.isFinite(window.fefs)) {
    ui.fefs = Math.max(8, Math.round(window.fefs));
  }
  if (typeof window.dbfs === "number" && Number.isFinite(window.dbfs)) {
    ui.dbfs = Math.max(8, Math.round(window.dbfs));
  }
  applyFontSizes();

  // Welcome content injected by Python into the #welcomeBackground placeholder.
  const placeholder = document.getElementById("welcomeBackground");
  if (placeholder) {
    ui.welcomeHtml = placeholder.innerHTML;
    placeholder.remove();
  }
}