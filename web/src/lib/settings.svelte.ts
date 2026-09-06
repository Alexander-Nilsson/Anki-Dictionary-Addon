/**
 * Reactive settings state (Svelte 5 runes).
 *
 * Holds the addon config plus the async data the settings UI needs (dictionary
 * names, word-list providers, note types). Mutations are staged locally until
 * the user presses Save, which ships the whole config to Python via
 * `settings:save`.
 */

import { SETTINGS_CMD } from "./settings-bridge";
import { pycmd } from "./pycmd";

export interface WordListFile {
  lang: string;
  files: {
    name: string;
    size: number;
    type: string;
    status: string;
  }[];
}

export interface WordListProvider {
  key: string;
  lang: string;
  name: string;
  type: "rank" | "level";
}

export interface ForvoLanguage {
  code: string;
  name: string;
}

interface LlmTestResult {
  ok: boolean;
  message: string;
}

/** Revision counter so the UI can react when a reply lands for the same page
 * (e.g. config arrived vs. dictionary names arrived). */
class SettingsStore {
  config = $state<Record<string, unknown>>({});
  configLoaded = $state(false);
  dictionaryNames = $state<string[]>([]);
  wordListFiles = $state<WordListFile[]>([]);
  providers = $state<WordListProvider[]>([]);
  noteTypes = $state<Record<string, string[]>>({});
  languagesDicts = $state<Record<string, string[]>>({});
  forvoLanguages = $state<ForvoLanguage[]>([]);
  llmTest = $state<LlmTestResult | null>(null);
  llmTestPending = $state(false);
  savedRevision = $state(0);
  /** The object currently being edited (config + nested editors). */
  dirty = $state<Record<string, unknown>>({});
  saving = $state(false);
  /** Path picked by the native font browser (one-shot, cleared on open). */
  fontFile = $state("");
}

export const settings = new SettingsStore();

/** Request the config and derived data from Python (called on mount). */
export function loadSettings(): void {
  settings.configLoaded = false;
  pycmd(SETTINGS_CMD.getConfig());
  pycmd(SETTINGS_CMD.getDictionaryNames());
  pycmd(SETTINGS_CMD.getWordListData());
  pycmd(SETTINGS_CMD.getNoteTypes());
  pycmd(SETTINGS_CMD.getLanguagesDicts());
  pycmd(SETTINGS_CMD.getForvoLanguages());
}

/** Replace the whole staged config (from Python or after Save). */
export function stageConfig(config: Record<string, unknown>): void {
  settings.config = config;
  settings.dirty = structuredClone(config);
  settings.configLoaded = true;
}

/** Save the staged config back to Python and close. */
export function saveSettings(): void {
  if (settings.saving) return;
  settings.saving = true;
  pycmd(SETTINGS_CMD.save(settings.dirty));
}

export function restoreDefaults(): void {
  pycmd(SETTINGS_CMD.restoreDefaults());
}

export function testLLM(): void {
  settings.llmTestPending = true;
  settings.llmTest = null;
  pycmd(
    SETTINGS_CMD.testLLM({
      llm_api_key: settings.dirty.llm_api_key ?? "",
      llm_base_url: settings.dirty.llm_base_url ?? "",
      llm_model: settings.dirty.llm_model ?? "",
    }),
  );
}

export function deleteWordList(filename: string): void {
  pycmd(SETTINGS_CMD.deleteWordList(filename));
}

export function removeLanguage(lang: string): void {
  pycmd(SETTINGS_CMD.removeLanguage(lang));
}

export function clearFontFile(): void {
  settings.fontFile = "";
}

/**
 * Wire Python's `window.SETTINGS` reply surface (installed by
 * `initSettingsBridge`) to the reactive store. Called once before mount.
 */
export function wireSettingsReplies(): void {
  const replies = (window as unknown as Record<string, unknown>).SETTINGS as
    Record<string, unknown>;

  replies.setConfig = (config: unknown) => {
    if (!config || typeof config !== "object") return;
    settings.config = config as Record<string, unknown>;
    settings.dirty = structuredClone(config) as Record<string, unknown>;
    settings.configLoaded = true;
  };
  replies.setDictionaryNames = (names: unknown) => {
    settings.dictionaryNames = Array.isArray(names) ? (names as string[]) : [];
  };
  replies.setWordListData = (data: unknown) => {
    const d = (data ?? {}) as { files?: unknown[]; providers?: unknown[] };
    settings.wordListFiles = Array.isArray(d.files)
      ? (d.files as WordListFile[])
      : [];
    settings.providers = Array.isArray(d.providers)
      ? (d.providers as WordListProvider[])
      : [];
  };
  replies.setNoteTypes = (types: unknown) => {
    settings.noteTypes = (types ?? {}) as Record<string, string[]>;
  };
  replies.setLanguagesDicts = (data: unknown) => {
    settings.languagesDicts = (data ?? {}) as Record<string, string[]>;
  };
  replies.setForvoLanguages = (data: unknown) => {
    settings.forvoLanguages = Array.isArray(data)
      ? (data as ForvoLanguage[])
      : [];
  };
  replies.setLLMTest = (result: unknown) => {
    settings.llmTestPending = false;
    const r = (result ?? {}) as { success?: boolean; message?: string };
    settings.llmTest = {
      ok: r.success ?? false,
      message: r.message ?? "",
    };
  };
  replies.setSaved = () => {
    settings.saving = false;
    settings.savedRevision += 1;
  };
  replies.setFontFile = (path: unknown) => {
    settings.fontFile = typeof path === "string" ? path : "";
  };
}