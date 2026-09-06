/**
 * Dev-only mock bridge for previewing the web UI in a plain browser.
 *
 * Anki injects `window.pycmd` and replies through the `SETTINGS.*` /
 * `addNewTab`-style globals; a browser has neither, so the pages can only
 * render their shells. Opening either page with `?mock=1` (e.g.
 * `http://localhost:5173/settings.html?mock=1`) activates this module: it
 * installs a fake `window.pycmd` that serves canned replies through the same
 * reply surfaces Python uses, making every tab/modals/buttons clickable.
 *
 * It is inert everywhere else: without the `mock=1` query parameter it does
 * nothing, and Anki never loads its pages with that parameter, so this never
 * runs inside the addon.
 */
import type { DictDocument } from "./lib/types";
import { showToast } from "./lib/toast.svelte";

const MOCK_BANNER_ID = "dev-mock-banner";

/** In-browser mirror of Python-side header/tab state. */
const MOCK_STATE = {
  groups: ["All", "Japanese"],
  currentGroup: "All",
  searchModes: ["Forward", "Reverse"],
  searchMode: "Forward",
  deinflect: false,
  singleTab: true,
  clipboardPaused: false,
  source: "manual",
  showTarget: false,
  target: "",
};

/** Mirrors the persisted search history an Anki user would have. */
let MOCK_HISTORY: string[][] = [["example", "2026-09-06"], ["こんにちは", "2026-09-05"]];

function pushHeaderState(): void {
  callReply("setHeaderState", {
    ...MOCK_STATE,
    current: MOCK_STATE.currentGroup,
  });
}

function pushMockHistory(): void {
  callReply("setSearchHistory", MOCK_HISTORY);
}

/** Internal notes: simulate toggles, log what can't be simulated. */
function pushNote(msg: string): void {
  console.info("[dev-mock]", msg);
}

/** Call a Python->JS reply global if it has been installed. */
function callReply(name: string, ...args: unknown[]): void {
  const w = window as unknown as Record<string, unknown>;
  const fn = w[name];
  if (typeof fn === "function") {
    try {
      (fn as (...a: unknown[]) => void)(...args);
    } catch (err) {
      console.error(`[dev-mock] ${name}(...) failed:`, err);
    }
  } else {
    console.warn(`[dev-mock] reply surface ${name} not installed yet`);
  }
}

/** Call a `SETTINGS.*` reply handler (settings window). */
function callSettingsReply(name: string, ...args: unknown[]): void {
  const w = window as unknown as Record<string, unknown>;
  const sett = w.SETTINGS as Record<string, unknown> | undefined;
  const handler = sett?.[name];
  if (typeof handler === "function") {
    try {
      (handler as (...a: unknown[]) => void)(...args);
    } catch (err) {
      console.error(`[dev-mock] SETTINGS.${name}(...) failed:`, err);
    }
  } else {
    console.warn(`[dev-mock] SETTINGS.${name} not installed yet`);
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── canned settings data ─────────────────────────────────────────────────────

/** Mirrors the fallback defaults in src/anki_dictionary/utils/config.py. */
const MOCK_CONFIG: Record<string, unknown> = {
  DictionaryGroups: {
    Japanese: {
      dictionaries: ["JMdict", "Kanji"],
      customFont: false,
      font: "",
    },
  },
  ExportTemplates: {
    "Basic template": {
      noteType: "Basic",
      word: "Word",
      sentence: "Sentence",
    },
  },
  maxWidth: 1500,
  maxHeight: 400,
  dictSearch: 50,
  maxSearch: 1000,
  frontBracket: "【",
  backBracket: "】",
  highlightTarget: true,
  showTarget: false,
  tooltips: true,
  currentGroup: "All",
  searchMode: "Forward",
  deinflect: false,
  onetab: true,
  dictSizePos: [0, 0, 800, 600],
  dictAlwaysOnTop: false,
  day: true,
  theme: "light",
  imageAutoConvert: true,
  imageSearchRegion: "United States",
  forvo_enabled: true,
  forvo_language: "ja",
  forvo_limit: 3,
  ForvoFields: [],
  ForvoAddType: "add",
  star_char: "★",
  star_thresholds: [1501, 5001, 15001, 30001, 60001],
  show_stars: true,
  show_rank: false,
  show_level_labels: true,
  word_list_visibility: {},
  auto_select_dict_group: true,
  language_defaults: { Japanese: "Japanese" },
  last_seen_version: "",
  hide_release_notes: false,
  clipboard_monitor_enabled: true,
  restore_session: false,
  session_terms: [],
  llm_enabled: true,
  llm_api_key: "sk-mock-1234",
  llm_base_url: "https://api.openai.com/v1/chat/completions",
  llm_model: "gpt-3.5-turbo",
  llm_temperature: 0.3,
  llm_keep_alive: "30m",
  llm_think: false,
  llm_stream: false,
  llm_get_pronunciation: false,
  llm_prompts: [
    { text: "Provide a concise dictionary definition for the word: {term}", active: true },
  ],
  llm_prompt: "Provide a concise dictionary definition for the word: {term}",
  jReadingCards: false,
};

const MOCK_DICTIONARY_NAMES = ["Images", "JMdict", "Kanji", "LLM", "Mock Dictionary"];

const MOCK_WORD_LIST_DATA = {
  files: [
    {
      lang: "Japanese",
      files: [
        { name: "japanese_frequency.json", size: 3_128_400, type: "rank", status: "ok" },
        { name: "japanese_level.json", size: 812_110, type: "level", status: "ok" },
      ],
    },
  ],
  providers: [
    { key: "Japanese::MockRank", lang: "Japanese", name: "MockRank", type: "rank" },
    { key: "Japanese::MockLevel", lang: "Japanese", name: "MockLevel", type: "level" },
  ],
};

const MOCK_NOTE_TYPES: Record<string, string[]> = {
  Basic: ["Front", "Back"],
  "Basic (and reversed card)": ["Front", "Back"],
};

const MOCK_LANGUAGES_DICTS: Record<string, string[]> = {
  Japanese: ["JMdict", "Kanji"],
  Spanish: ["SpanishDict"],
  German: ["GermanDict"],
};

/** A subset of the full Forvo catalogue (Python's FORVO_LANGUAGES). */
const MOCK_FORVO_LANGUAGES = [
  { code: "ar", name: "Arabic" },
  { code: "de", name: "German" },
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "it", name: "Italian" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "nl", name: "Dutch" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
  { code: "zh", name: "Chinese" },
];

/** Mirrors the built-in themes in src/anki_dictionary/ui/themes.py. */
const MOCK_THEMES: Record<string, Record<string, string>> = {
  light: {
    header_background: "#FFFFFF",
    selector: "#F8F9FA",
    header_text: "#212529",
    search_term: "#007BFF",
    border: "#DEE2E6",
    anki_button_background: "#F8F9FA",
    anki_button_text: "#212529",
    tab_hover: "#E9ECEF",
    current_tab_gradient_top: "#FFFFFF",
    current_tab_gradient_bottom: "#E9ECEF",
    example_highlight: "#FFF3CD",
    definition_background: "#FFFFFF",
    definition_text: "#212529",
    pitch_accent_color: "#DC3545",
  },
  dark: {
    header_background: "#1A1B1E",
    selector: "#25262B",
    header_text: "#C1C2C5",
    search_term: "#4DABF7",
    border: "#373A40",
    anki_button_background: "#25262B",
    anki_button_text: "#C1C2C5",
    tab_hover: "#2C2E33",
    current_tab_gradient_top: "#2C2E33",
    current_tab_gradient_bottom: "#1A1B1E",
    example_highlight: "#2C2E33",
    definition_background: "#1A1B1E",
    definition_text: "#C1C2C5",
    pitch_accent_color: "#FF6B6B",
  },
  catppuccin_mocha: {
    header_background: "#1e1e2e",
    selector: "#181825",
    header_text: "#cdd6f4",
    search_term: "#89b4fa",
    border: "#b4befe",
    anki_button_background: "#313244",
    anki_button_text: "#cdd6f4",
    tab_hover: "#45475a",
    current_tab_gradient_top: "#585b70",
    current_tab_gradient_bottom: "#1e1e2e",
    example_highlight: "#313244",
    definition_background: "#1e1e2e",
    definition_text: "#cdd6f4",
    pitch_accent_color: "#f38ba8",
  },
  nord: {
    header_background: "#3b4252",
    selector: "#434c5e",
    header_text: "#eceff4",
    search_term: "#88c0d0",
    border: "#4c566a",
    anki_button_background: "#81a1c1",
    anki_button_text: "#2e3440",
    tab_hover: "#4c566a",
    current_tab_gradient_top: "#434c5e",
    current_tab_gradient_bottom: "#3b4252",
    example_highlight: "#ebcb8b",
    definition_background: "#2e3440",
    definition_text: "#d8dee9",
    pitch_accent_color: "#bf616a",
  },
  solarized_light: {
    header_background: "#eee8d5",
    selector: "#fdf6e3",
    header_text: "#586e75",
    search_term: "#268bd2",
    border: "#93a1a1",
    anki_button_background: "#859900",
    anki_button_text: "#fdf6e3",
    tab_hover: "#eee8d5",
    current_tab_gradient_top: "#fdf6e3",
    current_tab_gradient_bottom: "#eee8d5",
    example_highlight: "#b58900",
    definition_background: "#fdf6e3",
    definition_text: "#657b83",
    pitch_accent_color: "#dc322f",
  },
  tokyo_night: {
    header_background: "#1f2335",
    selector: "#24283b",
    header_text: "#c0caf5",
    search_term: "#7aa2f7",
    border: "#414868",
    anki_button_background: "#bb9af7",
    anki_button_text: "#1a1b26",
    tab_hover: "#3b4261",
    current_tab_gradient_top: "#24283b",
    current_tab_gradient_bottom: "#1f2335",
    example_highlight: "#e0af68",
    definition_background: "#1a1b26",
    definition_text: "#a9b1d6",
    pitch_accent_color: "#f7768e",
  },
  gruvbox: {
    header_background: "#3c3836",
    selector: "#504945",
    header_text: "#ebdbb2",
    search_term: "#fabd2f",
    border: "#665c54",
    anki_button_background: "#b8bb26",
    anki_button_text: "#282828",
    tab_hover: "#504945",
    current_tab_gradient_top: "#504945",
    current_tab_gradient_bottom: "#3c3836",
    example_highlight: "#d65d0e",
    definition_background: "#282828",
    definition_text: "#ebdbb2",
    pitch_accent_color: "#fb4934",
  },
};

/** Built-ins are everything Python ships; anything else is a user theme. */
const MOCK_BUILTIN_THEMES = Object.keys(MOCK_THEMES);

MOCK_THEMES["My Sepia"] = {
  header_background: "#f4ecd8",
  selector: "#e9dcc0",
  header_text: "#43382b",
  search_term: "#9c5b25",
  border: "#d3c3a3",
  anki_button_background: "#e2d3b3",
  anki_button_text: "#3b3125",
  tab_hover: "#e9dcc0",
  current_tab_gradient_top: "#fbf5e7",
  current_tab_gradient_bottom: "#e9dcc0",
  example_highlight: "#d9c48f",
  definition_background: "#fbf5e7",
  definition_text: "#3f362a",
  pitch_accent_color: "#a33a2b",
};
let MOCK_ACTIVE_THEME = "light";

function pushMockThemes(): void {
  callSettingsReply("setThemes", {
    themes: MOCK_THEMES,
    active: MOCK_ACTIVE_THEME,
    builtins: MOCK_BUILTIN_THEMES,
  });
}

// ── canned dictionary data ───────────────────────────────────────────────────



/** A believable search document so the dictionary page renders a result. */
function mockDocument(term: string): DictDocument {
  const safe = escapeHtml(term);
  return {
    font: " ",
    ankiIcon: "",
    sidebar: [
      {
        displayName: "Mock Dictionary",
        dataIndex: 1,
        entries: [{ dataIndex: 1, headerHtml: `<span class="term">${safe}</span>` }],
      },
    ],
    blocks: [
      {
        type: "dictionaryTitle",
        dataIndex: 0,
        title: "Mock Dictionary",
        font: " ",
        overwriteHtml: "",
        fieldHtml: "",
      },
      {
        type: "termPronunciation",
        dataIndex: 1,
        dictName: "Mock Dictionary",
        cleanName: "Mock Dictionary",
        font: " ",
        headerHtml: `<span class="term">${safe}</span>`,
        stars: "",
        starTip: "",
        rank: null,
        levels: null,
        definitionHtml: "",
      },
      {
        type: "definition",
        font: " ",
        html: `<div class="definition"><p>This is a mock dictionary definition for <b>${safe}</b>.</p><p>You are viewing the dev mock (URL parameter <code>mock=1</code>); open the addon inside Anki for real results from your installed dictionaries.</p></div>`,
      },
      { type: "llmLoader", id: "llm-mock", html: `<div class="llm"></div>` },
      { type: "imageLoader", id: "img-mock", html: `<div class="imageResults"></div>` },
      { type: "forvoLoader", id: "forvo-mock", html: `<div class="forvo"></div>` },
    ],
  };
}

// ── command routing ──────────────────────────────────────────────────────────

function handleSettingsCommand(cmd: string): void {
  if (cmd === "settings:getConfig") {
    callSettingsReply("setConfig", MOCK_CONFIG);
  } else if (cmd === "settings:getDictionaryNames") {
    callSettingsReply("setDictionaryNames", MOCK_DICTIONARY_NAMES);
  } else if (cmd === "settings:getWordListData") {
    callSettingsReply("setWordListData", MOCK_WORD_LIST_DATA);
  } else if (cmd === "settings:getNoteTypes") {
    callSettingsReply("setNoteTypes", MOCK_NOTE_TYPES);
  } else if (cmd === "settings:getLanguagesDicts") {
    callSettingsReply("setLanguagesDicts", MOCK_LANGUAGES_DICTS);
  } else if (cmd === "settings:getForvoLanguages") {
    callSettingsReply("setForvoLanguages", MOCK_FORVO_LANGUAGES);
  } else if (cmd.startsWith("settings:save:")) {
    callSettingsReply("setSaved", true);
    console.log("[dev-mock] settings saved (not persisted)");
  } else if (cmd.startsWith("settings:testLLM:")) {
    setTimeout(
      () => callSettingsReply("setLLMTest", { success: true, message: "Mock: LLM connection OK" }),
      400,
    );
  } else if (cmd === "settings:restoreDefaults") {
    callSettingsReply("setConfig", MOCK_CONFIG);
  } else if (cmd === "settings:browseFontFile") {
    callSettingsReply("setFontFile", "/mock/fonts/TakaoMincho.ttf");
  } else if (cmd === "settings:getThemes") {
    pushMockThemes();
  } else if (cmd.startsWith("settings:applyTheme:")) {
    const name = JSON.parse(cmd.slice("settings:applyTheme:".length)) as string;
    if (MOCK_THEMES[name]) MOCK_ACTIVE_THEME = name;
    pushMockThemes();
  } else if (cmd.startsWith("settings:saveTheme:")) {
    const payload = JSON.parse(cmd.slice("settings:saveTheme:".length)) as {
      name: string;
      colors: Record<string, string>;
      apply?: boolean;
    };
    MOCK_THEMES[payload.name] = payload.colors;
    if (payload.apply !== false) MOCK_ACTIVE_THEME = payload.name;
    pushMockThemes();
  } else if (cmd.startsWith("settings:deleteTheme:")) {
    const name = JSON.parse(cmd.slice("settings:deleteTheme:".length)) as string;
    if (!MOCK_BUILTIN_THEMES.includes(name)) delete MOCK_THEMES[name];
    if (MOCK_ACTIVE_THEME === name) MOCK_ACTIVE_THEME = "light";
    pushMockThemes();
  } else if (cmd === "settings:close") {
    console.log("[dev-mock] settings:close (no-op in browser)");
  } else {
    // Native delegations (file dialogs / installers) can't run in a browser.
    console.log("[dev-mock] settings command (no-op):", cmd);
  }
}

function handleDictionaryCommand(cmd: string): void {
  // Header state / data fetch commands.
  if (cmd === "AnkiDictionaryLoaded") {
    pushNote("page loaded");
  } else if (cmd === "getHeaderState:" || cmd === "getGroups:" || cmd === "getSearchModes:") {
    if (cmd === "getGroups:")
      callReply("setGroups", {
        groups: MOCK_STATE.groups,
        current: MOCK_STATE.currentGroup,
      });
    if (cmd === "getSearchModes:")
      callReply("setSearchModes", {
        modes: MOCK_STATE.searchModes,
        current: MOCK_STATE.searchMode,
      });
    pushHeaderState();
  } else if (cmd === "getSearchHistory:") {
    pushMockHistory();
  } else if (cmd === "requestSearchStatus:") {
    callReply("setSearchStatus", {
      source: MOCK_STATE.source,
      clipboardPaused: MOCK_STATE.clipboardPaused,
    });
  }
  // In-web chrome actions: toggle state and reflect it back via setHeaderState.
  else if (cmd === "setClipboardPaused:true") {
    MOCK_STATE.clipboardPaused = true;
    pushHeaderState();
  } else if (cmd === "setClipboardPaused:false") {
    MOCK_STATE.clipboardPaused = false;
    pushHeaderState();
  } else if (cmd === "setDeinflect:true") {
    MOCK_STATE.deinflect = true;
    pushHeaderState();
  } else if (cmd === "setDeinflect:false") {
    MOCK_STATE.deinflect = false;
    pushHeaderState();
  } else if (cmd.startsWith("setTabMode:")) {
    MOCK_STATE.singleTab = cmd === "setTabMode:single";
    pushHeaderState();
  } else if (cmd.startsWith("setGroup:")) {
    MOCK_STATE.currentGroup = cmd.slice("setGroup:".length);
    pushHeaderState();
  } else if (cmd.startsWith("setSearchMode:")) {
    MOCK_STATE.searchMode = cmd.slice("setSearchMode:".length);
    pushHeaderState();
  }
  // Content interactions on a result document. The block components
  // (TermPronunciation etc.) show their own toasts, so only log here.
  else if (
    cmd.startsWith("clipped") ||
    cmd.startsWith("addDef") ||
    cmd.startsWith("sendToField") ||
    cmd.startsWith("sendImgToField") ||
    cmd.startsWith("sendAudioToField")
  ) {
    pushNote(`content action (${cmd.slice(0, 30)}…)`);
  } else if (cmd.startsWith("fieldsSetting") || cmd.startsWith("overwriteSetting")) {
    pushNote(`field / overwrite updated (${cmd.slice(0, 30)}…)`);
  } else if (cmd.startsWith("playAudio:") || cmd.startsWith("audioExport")) {
    pushNote("audio play/export simulated; no audio in browser preview");
  } else if (cmd.startsWith("getMoreImages:")) {
    pushNote("image fetch simulated (no Anki image provider in browser)");
  }
  // Search: add a mock tab + push a mock history entry.
  else if (cmd.startsWith("searchTerm:")) {
    const term = cmd.slice("searchTerm:".length) || "example";
    MOCK_HISTORY = [[term, new Date().toISOString().slice(0, 10)], ...MOCK_HISTORY];
    pushMockHistory();
    setTimeout(() => {
      callReply("addNewTab", mockDocument(term), term, MOCK_STATE.singleTab, 1);
    }, 250);
  } else if (cmd.startsWith("updateTerm:")) {
    // Tab term renamed (from a new search on an existing tab).
  }
  // Actions that open native Anki windows: acknowledge them so clicks register.
  else if (cmd === "openHistory") {
    showToast("Anki search-history window would open");
  } else if (cmd === "openTheme") {
    showToast("Anki theme editor would open");
  } else if (cmd === "openSettings") {
    showToast("Anki settings window would open");
  }
  // History row actions.
  else if (cmd.startsWith("deleteSearchHistory:")) {
    const term = cmd.slice("deleteSearchHistory:".length);
    MOCK_HISTORY = MOCK_HISTORY.filter(([t]) => t !== term);
    pushMockHistory();
  }
  // Persistence writes Python silently accepts.
  else if (cmd.startsWith("saveSession:") || cmd.startsWith("saveFS:")) {
    pushNote("session / font sizes persisted (in-memory)");
  } else {
    pushNote(`unhandled command: ${cmd}`);
  }
}

function handleMockCommand(cmd: string): void {
  if (cmd.startsWith("settings:") || cmd === "settingsLoaded") {
    handleSettingsCommand(cmd);
  } else {
    handleDictionaryCommand(cmd);
  }
}

function showBanner(): void {
  if (document.getElementById(MOCK_BANNER_ID)) return;
  const el = document.createElement("div");
  el.id = MOCK_BANNER_ID;
  el.textContent = "dev mock active";
  el.style.cssText =
    "position:fixed;right:8px;bottom:8px;z-index:99999;padding:6px 12px;border-radius:12px;" +
    "background:#334155;color:#e2e8f0;font:12px/1.4 system-ui,sans-serif;" +
    "box-shadow:0 2px 8px rgba(0,0,0,.35);pointer-events:none";
  document.body.appendChild(el);
}

/**
 * Install the browser mock bridge. Only active when the URL has `mock=1`;
 * returns immediately everywhere else so it never runs inside Anki.
 */
export function installDevMock(): void {
  if (!globalThis.location?.search?.includes("mock=1")) return;

  const w = window as unknown as Record<string, unknown>;
  w.pycmd = (command: string) => handleMockCommand(command);

  // The banner needs the body; wait for it if the script ran very early.
  if (document.body) showBanner();
  else document.addEventListener("DOMContentLoaded", () => showBanner(), { once: true });

  console.info("[dev-mock] installed (mock=1). Settings + dictionary commands are simulated.");
}