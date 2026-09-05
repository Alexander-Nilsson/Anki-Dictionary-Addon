/**
 * Global keyboard map for the dictionary shell (U5).
 *
 * The mouse-first results pane becomes keyboard-navigable: ↑/↓ move between
 * entries, Tab/Shift+Tab jump between dictionaries, E exports the current
 * entry and C copies it. The "current entry" is the scrollspy highlight that
 * `syncSidebarActive` maintains (stored on `ui.activeEntry`); E/C simply click
 * that entry's existing tool buttons, so all export/copy logic stays in one
 * place.
 *
 * Native focus traversal is left intact: Tab is intercepted only when no
 * focusable element has focus, and keystrokes meant for the chrome search box
 * or any input/select/textarea are never hijacked.
 */
import { findDictionaryBlock, scrollToElement } from "./dom";
import { ui } from "./tabs.svelte";

/** Entry blocks (.termPronunciation) of the active tab, in document order. */
function activeEntries(): HTMLElement[] {
  const activeTab = document.querySelector<HTMLElement>(
    `.tabContent[data-index="${ui.activeId}"]`,
  );
  if (!activeTab) return [];
  return Array.from(
    activeTab.querySelectorAll<HTMLElement>(".termPronunciation"),
  );
}

/** Dictionary title blocks of the active tab, in document order. */
function activeDictBlocks(): HTMLElement[] {
  const activeTab = document.querySelector<HTMLElement>(
    `.tabContent[data-index="${ui.activeId}"]`,
  );
  if (!activeTab) return [];
  return Array.from(
    activeTab.querySelectorAll<HTMLElement>(".dictionaryTitleBlock"),
  );
}

/** Keystrokes aimed at form fields / editable content are left alone. */
function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  );
}

/** True when focus sits on something Tab normally moves between. */
function hasFocusableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(
    target.closest(
      "button, [role='button'], input, select, textarea, a[href], [tabindex]",
    ),
  );
}

/** Trigger a per-entry tool on the current (or first) entry. */
function clickTool(selector: string): void {
  const entry = ui.activeEntry ?? activeEntries()[0];
  entry?.querySelector<HTMLElement>(selector)?.click();
}

/** Move to the previous/next entry and keep the scrollspy in sync. */
function moveEntry(next: boolean): void {
  const entries = activeEntries();
  if (entries.length === 0) return;
  let idx = ui.activeEntry ? entries.indexOf(ui.activeEntry) : -1;
  if (idx < 0) idx = next ? -1 : entries.length;
  idx = Math.min(Math.max(idx + (next ? 1 : -1), 0), entries.length - 1);
  ui.activeEntry = entries[idx];
  scrollToElement(entries[idx]);
  document.dispatchEvent(new Event("tabChanged"));
}

/** Move to the previous/next dictionary and highlight its first entry. */
function moveDict(next: boolean): void {
  const dicts = activeDictBlocks();
  if (dicts.length === 0) return;
  let idx = -1;
  if (ui.activeEntry) {
    const block = findDictionaryBlock(ui.activeEntry);
    if (block) idx = dicts.indexOf(block);
  }
  if (idx < 0) idx = next ? -1 : dicts.length;
  idx = Math.min(Math.max(idx + (next ? 1 : -1), 0), dicts.length - 1);
  const dict = dicts[idx];
  scrollToElement(dict);

  let firstEntry: HTMLElement | null = null;
  let el = dict.nextElementSibling as HTMLElement | null;
  while (el && !el.classList.contains("dictionaryTitleBlock")) {
    if (el.classList.contains("termPronunciation")) {
      firstEntry = el;
      break;
    }
    el = el.nextElementSibling as HTMLElement | null;
  }
  if (firstEntry) {
    ui.activeEntry = firstEntry;
    document.dispatchEvent(new Event("tabChanged"));
  }
}

/** Attach the global key handler; returns a cleanup. Safe to call once. */
export function installKeymap(): () => void {
  const onKey = (e: KeyboardEvent): void => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (isEditableTarget(e.target)) return;

    const key = e.key;

    if (key === "?" || (key === "/" && e.shiftKey)) {
      e.preventDefault();
      ui.showKeymap = !ui.showKeymap;
      return;
    }
    if (key === "Escape") {
      if (ui.showKeymap) {
        e.preventDefault();
        ui.showKeymap = false;
      }
      return;
    }
    if (ui.showKeymap) return;

    switch (key) {
      case "e":
      case "E":
        e.preventDefault();
        clickTool(".ankiExportButton");
        break;
      case "c":
      case "C":
        e.preventDefault();
        clickTool(".clipper");
        break;
      case "ArrowUp":
        e.preventDefault();
        moveEntry(false);
        break;
      case "ArrowDown":
        e.preventDefault();
        moveEntry(true);
        break;
      case "Tab":
        if (hasFocusableTarget(e.target)) return;
        e.preventDefault();
        moveDict(!e.shiftKey);
        break;
      default:
        break;
    }
  };

  document.addEventListener("keydown", onKey);
  return () => document.removeEventListener("keydown", onKey);
}