/**
 * JS -> Python settings bridge.
 *
 * `pycmd(...)` is injected by Anki's AnkiWebView; every `pycmd("...")` call is
 * routed to the settings bridge's `handleSettingsAction` on the Python side.
 * Python replies by calling globals on the `window.SETTINGS` object (installed
 * by this module) via `AnkiWebView.eval`.
 *
 * Commands follow the JSON-payload convention used elsewhere in the addon:
 *    settings:getConfig          ->  SETTINGS.setConfig(<dict>)
 *    settings:getDictionaryNames ->  SETTINGS.setDictionaryNames(<[string]>)
 *    settings:getWordListData    ->  SETTINGS.setWordListData(<dict>)
 *    settings:getNoteTypes       ->  SETTINGS.setNoteTypes(<{[name]:[flds]}>)
 *    settings:getForvoLanguages  ->  SETTINGS.setForvoLanguages(<[{code,name}]>)
 *    settings:save:<json>        ->  persist the given config
 *    settings:testLLM:<json>     ->  SETTINGS.setLLMTest({ok, message})
 *    settings:deleteWordList:<name>
 *    settings:restoreDefaults
 *    settings:close
 *    settings:removeLanguage:<lang>
 *    settings:webInstallDicts | settings:importDicts
 *    settings:webInstallFreq   | settings:importFreq
 *    settings:browseFontFile   ->  SETTINGS.setFontFile(path)
 */

export const SETTINGS_CMD = {
  loaded: () => "settingsLoaded",
  getConfig: () => "settings:getConfig",
  getDictionaryNames: () => "settings:getDictionaryNames",
  getWordListData: () => "settings:getWordListData",
  getNoteTypes: () => "settings:getNoteTypes",
  getLanguagesDicts: () => "settings:getLanguagesDicts",
  getForvoLanguages: () => "settings:getForvoLanguages",
  save: (config: unknown) => `settings:save:${JSON.stringify(config)}`,
  testLLM: (config: unknown) => `settings:testLLM:${JSON.stringify(config)}`,
  deleteWordList: (filename: string) =>
    `settings:deleteWordList:${JSON.stringify(filename)}`,
  restoreDefaults: () => "settings:restoreDefaults",
  close: () => "settings:close",
  removeLanguage: (lang: string) =>
    `settings:removeLanguage:${JSON.stringify(lang)}`,
} as const;

/** Install the `window.SETTINGS` reply surface used by Python. */
export function initSettingsBridge(): void {
  const w = window as unknown as Record<string, unknown>;
  const replies: Record<string, unknown> = {
    setConfig: () => undefined,
    setDictionaryNames: () => undefined,
    setWordListData: () => undefined,
    setNoteTypes: () => undefined,
    setLanguagesDicts: () => undefined,
    setForvoLanguages: () => undefined,
    setLLMTest: () => undefined,
    setSaved: () => undefined,
    setFontFile: () => undefined,
  };
  w.SETTINGS = replies;
}