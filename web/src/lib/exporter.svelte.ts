/**
 * Reactive card-exporter state (Svelte 5 runes).
 *
 * Python owns the authoritative state (it is what actually builds the note),
 * so every edit is mirrored back over `exporter:setField` as it happens and
 * the full state travels with `exporter:add`. Python pushes the state back
 * whenever it changes outside the page — a definition sent from the
 * dictionary window, an exported sentence, a cleared card.
 */

import { EXPORTER_CMD } from "./exporter-bridge";
import { pycmd } from "./pycmd";

export interface DefinitionRow {
  /** Dictionary name, or "Images" for an image row. */
  name: string;
  /** Truncated preview text ("" for image rows). */
  short: string;
  /** `file://` thumbnail URLs for image rows; empty otherwise. */
  thumbs: string[];
}

export interface DefinitionSetting {
  name: string;
  limit: number;
}

export interface ExporterState {
  templates: string[];
  template: string;
  decks: string[];
  deck: string;
  sentence: string;
  secondary: string;
  word: string;
  notes: string;
  tags: string;
  definitions: DefinitionRow[];
  /** Label text Python also uses to decide whether a media field is filled. */
  imageLabel: string;
  audioLabel: string;
  /** `file://` preview of the attached image, "" when none. */
  imagePreview: string;
  autoAdd: boolean;
  autoAddDefinitions: boolean;
  unknownsToSearch: number;
  tooltips: boolean;
  /** Dictionary names offered by the automatic-definition settings modal. */
  dictionaryNames: string[];
  definitionSettings: DefinitionSetting[];
}

function emptyState(): ExporterState {
  return {
    templates: [],
    template: "",
    decks: [],
    deck: "",
    sentence: "",
    secondary: "",
    word: "",
    notes: "",
    tags: "",
    definitions: [],
    imageLabel: "No Image Selected",
    audioLabel: "No Audio Selected",
    imagePreview: "",
    autoAdd: false,
    autoAddDefinitions: false,
    unknownsToSearch: 3,
    tooltips: true,
    dictionaryNames: [],
    definitionSettings: [],
  };
}

class ExporterStore {
  state = $state<ExporterState>(emptyState());
  loaded = $state(false);
  /** Bumped when Python replaces the state, so fields can resync their DOM. */
  revision = $state(0);
  /** Field Python asked us to focus ("" when none pending). */
  focusRequest = $state("");

  /** Apply one edit locally and mirror it to Python. */
  setField<K extends keyof ExporterState>(field: K, value: ExporterState[K]): void {
    if (this.state[field] === value) return;
    this.state[field] = value;
    pycmd(EXPORTER_CMD.setField(field as string, value));
  }

  add(): void {
    pycmd(EXPORTER_CMD.add($state.snapshot(this.state)));
  }

  clear(): void {
    pycmd(EXPORTER_CMD.clear());
  }

  close(): void {
    pycmd(EXPORTER_CMD.close());
  }

  playAudio(): void {
    pycmd(EXPORTER_CMD.playAudio());
  }

  removeDefinition(index: number): void {
    // Optimistic removal keeps the table responsive; Python re-pushes the
    // authoritative list right after.
    this.state.definitions = this.state.definitions.filter((_, i) => i !== index);
    pycmd(EXPORTER_CMD.removeDefinition(index));
  }

  search(text: string, inBrowser: boolean): void {
    const trimmed = text.trim();
    if (trimmed) pycmd(EXPORTER_CMD.search(trimmed, inBrowser));
  }

  saveDefinitionSettings(rows: DefinitionSetting[]): void {
    this.state.definitionSettings = rows;
    pycmd(EXPORTER_CMD.saveDefinitionSettings(rows));
  }
}

export const exporter = new ExporterStore();

/** Point the `window.EXPORTER` reply surface at the store. */
export function wireExporterReplies(): void {
  const w = window as unknown as Record<string, Record<string, unknown>>;
  const replies = w.EXPORTER ?? (w.EXPORTER = {});

  replies.setState = (next: Partial<ExporterState>) => {
    exporter.state = { ...emptyState(), ...next };
    exporter.loaded = true;
    exporter.revision += 1;
  };
  replies.patchState = (patch: Partial<ExporterState>) => {
    exporter.state = { ...exporter.state, ...patch };
    exporter.loaded = true;
    exporter.revision += 1;
  };
  replies.setThemeCss = (styleHtml: string) => {
    const existing = document.getElementById("customThemeCss");
    if (existing) existing.outerHTML = styleHtml;
    else document.head.insertAdjacentHTML("beforeend", styleHtml);
  };
  replies.focusField = (field: string) => {
    exporter.focusRequest = field;
  };
}

/** Ask Python for the current state (also announces the page is ready). */
export function requestExporterState(): void {
  pycmd(EXPORTER_CMD.loaded());
}
