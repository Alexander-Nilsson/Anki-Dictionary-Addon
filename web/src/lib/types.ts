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

/** One open dictionary tab. Content HTML is produced by the Python renderer. */
export interface Tab {
  id: number;
  term: string;
  html: string;
}

export interface FontSizes {
  fefs: number;
  dbfs: number;
}