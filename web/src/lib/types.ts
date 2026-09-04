/**
 * Shared types for the Svelte dictionary UI.
 */

declare global {
  interface Window {
    /** Bridge injected by Anki's AnkiWebView (Python <=> JS). */
    pycmd?: (command: string) => void;
    /** Font sizes injected by Python in getHTMLURL (defaults below). */
    fefs?: number;
    dbfs?: number;
    /** Saved sidebar width (px) injected by Python; 0 means unset. */
    sidebarWidth?: number;
  }
}

export {};

/** One open dictionary tab. */
export interface Tab {
  id: number;
  term: string;
  /** Legacy HTML payload (pre-Phase-2 or legacy-fallback tabs). */
  html: string;
  /** Structured search document (Phase 2, Svelte shell). */
  doc: DictDocument | null;
}

export interface FontSizes {
  fefs: number;
  dbfs: number;
}

// ── Phase-2 structured search document ──────────────────────────────────────
// Python (SearchPipeline.getStructuredResult) emits this document instead of a
// single HTML blob; the Svelte shell renders it with typed components. Leaf
// text/HTML fragments (headword headers, definition bodies) are still computed
// by Python so the cleaning/highlighting logic lives in exactly one place.

/** A highlighted headword fragment for one sidebar entry. */
export interface SidebarEntry {
  dataIndex: number;
  headerHtml: string;
}

/** One dictionary group in the sidebar (listTitle + its entries). */
export interface SidebarDict {
  displayName: string;
  dataIndex: number;
  entries: SidebarEntry[];
}

/** A level-label badge ("HSK3", …). */
export interface LevelLabel {
  label: string;
  source?: string;
}

/** The frequency-rank badge ("[12k]"). */
export interface RankInfo {
  label: string;
  tip?: string;
}

/** Static dictionary header row (title + overwrite/field dropdowns + nav). */
export interface DictionaryTitleBlockData {
  type: "dictionaryTitle";
  dataIndex: number;
  title: string;
  /** Font-family style attribute produced by Python (`" "` when unset). */
  font: string;
  /** Overwrite-mode dropdown HTML (stays raw; dynamic). */
  overwriteHtml: string;
  /** Field-select dropdown HTML (stays raw; dynamic). */
  fieldHtml: string;
}

/** Headword + pronunciation + tools + badge row for one entry. */
export interface TermPronunciationBlockData {
  type: "termPronunciation";
  dataIndex: number;
  dictName: string;
  cleanName: string;
  font: string;
  /** Highlighted headword/pronunciation HTML from Python. */
  headerHtml: string;
  stars: string;
  starTip: string;
  rank: RankInfo | null;
  levels: LevelLabel[] | null;
  /** Processed + highlighted definition body (for copy/export fallback). */
  definitionHtml: string;
}

/** One rendered definition body (already processed + highlighted). */
export interface DefinitionBlockData {
  type: "definition";
  font: string;
  html: string;
}

/**
 * Opaque section for the dynamic services (Images / LLM / Forvo). The HTML is
 * the existing placeholder markup; async results inject into it unchanged.
 */
export interface LoaderBlockData {
  type: "imageLoader" | "llmLoader" | "forvoLoader";
  id: string;
  html: string;
}

/** Empty-result state. */
export interface NoResultsBlockData {
  type: "noResults";
  term: string;
  icon: string;
}

export type ContentBlock =
  | DictionaryTitleBlockData
  | TermPronunciationBlockData
  | DefinitionBlockData
  | LoaderBlockData
  | NoResultsBlockData;

/** The full payload of `addNewTab` in Svelte mode. */
export interface DictDocument {
  font: string;
  sidebar: SidebarDict[];
  blocks: ContentBlock[];
  /** Base64 anki-export icon (dark-theme aware). */
  ankiIcon: string;
}
