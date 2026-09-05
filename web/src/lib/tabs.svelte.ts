/**
 * Reactive state for the dictionary shell (Svelte 5 runes).
 *
 * The shell owns tabs, the welcome screen, sidebar state and font scaling.
 * Tab *content* is still Python-generated HTML (Phase 1 boundary) injected via
 * `{@html}`; later phases will replace it with structured data + components.
 */
import { CMD, pycmd } from "./pycmd";
import { offsetTopRelative } from "./dom";
import type { DictDocument, HistoryEntry, Tab } from "./types";
import { showToast } from "./toast.svelte";

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
  /** Tabs that have been mounted at least once (lazy-render, A3). */
  mounted = $state(new Set<number>());
  /** Toast id most recently announced when a tab was auto-closed by pruning. */
  lastPrunedNotice = $state("");
  /** Persisted search history (`_searchHistory.json`), shared by the chrome
   *  dropdown and the sidebar "Recent searches" section (U3). */
  history = $state<HistoryEntry[]>([]);
  /** Keyboard-map cheat sheet overlay visible (U5). */
  showKeymap = $state(false);
  /** The currently-highlighted entry (scrollspy), target for E/C keys (U5).
   *  Plain field on purpose — DOM elements don't belong in reactive state. */
  activeEntry: HTMLElement | null = null;
}

export const ui = new DictionaryUIStore();

let nextId = 1;

/** Ask Python for the persisted search history (`setSearchHistory` reply). */
export function refreshHistory(): void {
  pycmd(CMD.getSearchHistory());
}

/** Per-tab scroll positions of the shared #defBox scroller. */
const scrollPositions = new Map<number, number>();

// ── tabs ────────────────────────────────────────────

/**
 * Add (or, in single-tab mode, replace) a tab. Mirrors the legacy
 * `addNewTab(payload, term, singleTab, id)` semantics so Python callers are
 * unaffected. In Svelte mode the payload is a structured `DictDocument`; the
 * legacy fallback page still sends an HTML string.
 */
export function addTab(
  term: string,
  payload: string | DictDocument,
  singleTab: boolean
): void {
  if (payload === undefined || payload === null) {
    console.warn("addTab: called without content, skipping");
    return;
  }
  const cleanTerm = term ?? "";
  const doc = typeof payload === "object" ? payload : null;
  const html = doc ? "" : (payload as string);

  if (singleTab && ui.tabs.length > 0) {
    // Replace the content of the active tab (or the last one if none active).
    const idx = ui.tabs.findIndex((t) => t.id === ui.activeId);
    const target = idx >= 0 ? idx : ui.tabs.length - 1;
    ui.tabs[target] = {
      ...ui.tabs[target],
      term: cleanTerm,
      html,
      doc,
    };
    // Content changed — forget the old scroll position and start at the top.
    scrollPositions.delete(ui.tabs[target].id);
    const defBox = document.getElementById("defBox");
    if (defBox) defBox.scrollTop = 0;
    return;
  }

  if (!singleTab) {
    // Legacy behaviour: searching again opens a new tab; a leftover "Welcome"
    // tab (only relevant to older addon versions) is closed first.
    attemptCloseFirstTab();
  }

  const tab: Tab = { id: nextId++, term: cleanTerm, html, doc };
  rememberActiveScroll();
  ui.tabs.push(tab);
  ui.activeId = tab.id;
  ui.mounted.add(tab.id);
  touch(tab.id);
  pruneToCap();
  restoreScroll(tab.id);
  notifyTabChanged();
  persistSession();
}

/**
 * LRU cap (A3): keep at most `MAX_TABS` open tabs, closing the least-recently
 * used one (never the active tab). Reduces memory creep from image grids / LLM
 * text that otherwise stay live in hidden tabs. Purely additive — the user can
 * still close tabs manually, and single-tab mode never adds more than one.
 */
const MAX_TABS = 10;

function pruneToCap(): void {
  if (ui.tabs.length <= MAX_TABS) return;
  // Sort by last-used ascending — the oldest goes first. The active tab is
  // always skipped (closing it while in use is never desirable).
  const [oldest, ...rest] = [...ui.tabs].sort(
    (a, b) => (a.lastUsed ?? 0) - (b.lastUsed ?? 0),
  );
  if (!oldest || oldest.id === ui.activeId) {
    // Active is the stalest — drop the next one instead.
    if (rest.length) closeTab(rest[0].id);
    return;
  }
  const term = oldest.term;
  closeTab(oldest.id);
  showToast(`Closed "${term}" to keep at most ${MAX_TABS} tabs open`);
}

/** Stamp a tab as recently used (LRU bookkeeping, A3). */
function touch(id: number): void {
  const tab = ui.tabs.find((t) => t.id === id);
  if (tab) tab.lastUsed = Date.now();
}

/** Notify the scrollspy observer that the visible tab's content changed. */
function notifyTabChanged(): void {
  document.dispatchEvent(new Event("tabChanged"));
}

/** Persist the current open-tab terms so A5 can restore the session. */
function persistSession(): void {
  const terms = ui.tabs.map((t) => t.term).filter(Boolean);
  try {
    pycmd(CMD.saveSession(terms));
  } catch {
    /* non-critical — session restore is best-effort */
  }
}

export function closeTab(id: number): void {
  const idx = ui.tabs.findIndex((t) => t.id === id);
  if (idx === -1) return;
  const wasActive = id === ui.activeId;
  ui.tabs.splice(idx, 1);
  ui.mounted.delete(id);
  scrollPositions.delete(id);
  if (wasActive) {
    if (ui.tabs.length === 0) {
      ui.activeId = null;
    } else {
      // Prefer the tab to the left, like the legacy focusAnotherTab.
      ui.activeId = ui.tabs[Math.max(idx - 1, 0)].id;
    }
  }
  notifyTabChanged();
  persistSession();
}

/** True once a tab's content has been mounted (drives A3 lazy rendering). */
export function isMounted(id: number): boolean {
  return ui.mounted.has(id);
}

export function activate(id: number): void {
  if (id === ui.activeId) return;
  rememberActiveScroll();
  ui.activeId = id;
  ui.mounted.add(id);
  touch(id);
  restoreScroll(id);
  notifyTabChanged();
}

/** Save the outgoing tab's scroll before the shared #defBox is repurposed. */
function rememberActiveScroll(): void {
  const defBox = document.getElementById("defBox");
  if (defBox && ui.activeId !== null) {
    scrollPositions.set(ui.activeId, defBox.scrollTop);
  }
}

/** Restore the incoming tab's saved scroll once it is visible. */
function restoreScroll(id: number): void {
  const defBox = document.getElementById("defBox");
  if (!defBox) return;
  requestAnimationFrame(() => {
    defBox.scrollTop = scrollPositions.get(id) ?? 0;
  });
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

/** Recompute #defBox / sidebar heights (mirrors legacy `resizer()`).

Scoping note: #defArea is `position: relative` (app.css), so an absolute
#defBox must be offset from #defArea's own top — which already sits below the
tab strip. The legacy math (`top: tabsHeight`) double-counted that offset once
app.css introduced the relative container; it also predates the in-web chrome
strip. Both are corrected here: defBox starts at #defArea's top edge and the
chrome + tab-strip heights are subtracted from the available window height.
 */
export function resizer(): void {
  const tabsElement = document.getElementById("tabs");
  const chromeBar = document.getElementById("chromeBar");
  const defBox = document.getElementById("defBox");
  if (!tabsElement || !defBox) return;

  const chromeH = chromeBar ? chromeBar.offsetHeight || 0 : 0;
  const tabsH = tabsElement.offsetHeight || 0;
  const wHeight = window.innerHeight || 600;

  defBox.style.top = "0px";
  defBox.style.height = `${Math.max(wHeight - chromeH - tabsH, 100)}px`;

  for (const sb of Array.from(
    document.getElementsByClassName("definitionSideBar"),
  ) as HTMLElement[]) {
    sb.style.top = `${chromeH + tabsH}px`;
    sb.style.height = `${Math.max(wHeight - 14 - chromeH - tabsH, 100)}px`;
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

  // Sidebar width persisted by the user (0 = unset, keep the CSS default).
  const sidebarWidth = Number(window.sidebarWidth);
  if (Number.isFinite(sidebarWidth) && sidebarWidth > 0) {
    const ws = document.getElementById("widthSpecs");
    if (ws) {
      ws.textContent =
        `.sidebarOpenedDisplay{margin-left:${sidebarWidth}px !important;}` +
        `.sidebarOpenedSideBar{width:${sidebarWidth}px;}`;
    }
  }
}

// ── sidebar active-entry sync ──────────────────────

interface EntryPosition {
  block: HTMLElement;
  dictIndex: number;
  entryIndex: number;
}

/**
 * Highlight the sidebar entry that matches the definition block currently
 * visible in the active tab. The sidebar's structure mirrors the results
 * pane: listTitle *i* ↔ dictionaryTitleBlock *i*, and each li below it ↔ a
 * termPronunciation block (in order), for every dictionary including Images.
 *
 * Purely additive (cosmetic) — no existing navigation is affected.
 */
function syncSidebarActive(): void {
  const defBox = document.getElementById("defBox");
  if (!defBox) return;
  const activeTab = document.querySelector<HTMLElement>(
    `.tabContent[data-index="${ui.activeId}"]`,
  );
  if (!activeTab) return;

  const dictBlocks = Array.from(
    activeTab.querySelectorAll<HTMLElement>(".dictionaryTitleBlock"),
  );
  if (dictBlocks.length === 0) return;

  // Pair each .termPronunciation with the .dictionaryTitleBlock that precedes
  // it. The entry blocks are *siblings* of the title block in the results pane
  // (the legacy renderer and the Svelte components both emit flat siblings), so
  // a children-only query would always be empty — walk document order instead.
  // This also covers the wrapped Images/LLM/Forvo service sections, whose
  // content lives inside the loader wrapper yet still follows their title.
  const entries: EntryPosition[] = [];
  let dictIndex = -1;
  let entryIndex = 0;
  activeTab
    .querySelectorAll<HTMLElement>(
      ".dictionaryTitleBlock, .termPronunciation",
    )
    .forEach((node) => {
      if (node.classList.contains("dictionaryTitleBlock")) {
        dictIndex += 1;
        entryIndex = 0;
      } else {
        entries.push({ block: node, dictIndex, entryIndex });
        entryIndex += 1;
      }
    });
  if (entries.length === 0) return;

  // Bootstrap-style scrollspy: the current entry is the last one whose top
  // has crossed the viewport top edge. When scrolled to the very bottom, pin
  // the last entry — the page may be too short for its top to reach the top
  // edge, so the plain crossing rule would never advance to it.
  const atBottom =
    defBox.scrollTop > 0 &&
    defBox.scrollTop + defBox.clientHeight >= defBox.scrollHeight - 4;
  let current: EntryPosition | null = null;
  if (atBottom) {
    current = entries[entries.length - 1];
  } else {
    const anchor = defBox.scrollTop + 1;
    for (const entry of entries) {
      if (offsetTopRelative(entry.block, defBox) <= anchor) current = entry;
    }
    // Nothing has scrolled past the top yet — highlight the first entry.
    if (!current) current = entries[0];
  }
  if (!current) return;

  // U5: remember the highlighted entry so global E/C keys and arrow nav can
  // act on it (the scrollspy highlight doubles as the "current entry").
  ui.activeEntry = current.block;

  const listTitles = Array.from(
    activeTab.querySelectorAll<HTMLElement>(".definitionSideBar .listTitle"),
  );
  const title = listTitles[current.dictIndex];
  if (!title) return;
  const ol = title.nextElementSibling as HTMLElement | null;
  const lis = ol ? Array.from(ol.querySelectorAll<HTMLElement>("li")) : [];
  const target = lis[current.entryIndex];
  if (!target) return;

  const sidebar = activeTab.querySelector<HTMLElement>(".definitionSideBar");
  sidebar?.querySelectorAll(".foundEntriesList li.active").forEach((el) => {
    if (el !== target) el.classList.remove("active");
  });
  if (!target.classList.contains("active")) target.classList.add("active");
}

/** Track the visible entry in the results pane to sync the sidebar. */
export function initSidebarSync(): void {
  // A3: an IntersectionObserver on the entry blocks replaces the document-level
  // scroll listener (which fired on every scroll event). When the active tab
  // changes or new results arrive, the observer is re-armed against the new doc.
  const observer = new IntersectionObserver(
    (entries) => {
      // The entry whose top is nearest/above the viewport top wins.
      for (const entry of entries) {
        if (entry.isIntersecting) {
          syncSidebarActive();
          break;
        }
      }
    },
    { root: null, threshold: 0 },
  );

  document.addEventListener("tabChanged", () => {
    for (const el of Array.from(document.querySelectorAll(".tabContent"))) {
      observer.unobserve(el);
    }
    const activeTab = document.querySelector<HTMLElement>(
      `.tabContent[data-index="${ui.activeId}"]`,
    );
    if (activeTab) {
      activeTab
        .querySelectorAll<HTMLElement>(".termPronunciation")
        .forEach((el) => observer.observe(el));
    }
  });

  window.addEventListener("load", () => {
    document.dispatchEvent(new Event("tabChanged"));
  });
}