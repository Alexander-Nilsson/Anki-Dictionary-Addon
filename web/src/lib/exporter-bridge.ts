/**
 * JS -> Python card-exporter bridge.
 *
 * Mirrors `web/src/lib/settings-bridge.ts`: `pycmd(...)` is injected by Anki's
 * AnkiWebView and routed to `ExporterBridge.handleExporterAction` on the
 * Python side; Python replies by calling globals on `window.EXPORTER` (the
 * reply surface installed here) through `AnkiWebView.eval`.
 *
 * Commands:
 *    exporterLoaded                 ->  EXPORTER.setState(<state>)
 *    exporter:getState              ->  EXPORTER.setState(<state>)
 *    exporter:setField:<json>       ->  {field, value} — mirror one edit
 *    exporter:add:<json>            ->  add the card from the given state
 *    exporter:clear                 ->  clear the current card
 *    exporter:close                 ->  hide the exporter window
 *    exporter:playAudio             ->  play the attached audio
 *    exporter:removeDefinition:<i>  ->  drop definition at index i
 *    exporter:search:<json>         ->  {text, inBrowser} — look the text up
 *    exporter:saveDefinitionSettings:<json>  -> [{name, limit}, ...]
 *
 * Python pushes (no command required):
 *    EXPORTER.setState(<state>)     — full state replacement
 *    EXPORTER.patchState(<partial>) — merge a few keys
 *    EXPORTER.setThemeCss(<style element html>)
 *    EXPORTER.focusField(<name>)
 */

export const EXPORTER_CMD = {
  loaded: () => "exporterLoaded",
  getState: () => "exporter:getState",
  setField: (field: string, value: unknown) =>
    `exporter:setField:${JSON.stringify({ field, value })}`,
  add: (state: unknown) => `exporter:add:${JSON.stringify(state)}`,
  clear: () => "exporter:clear",
  close: () => "exporter:close",
  playAudio: () => "exporter:playAudio",
  removeDefinition: (index: number) => `exporter:removeDefinition:${index}`,
  search: (text: string, inBrowser: boolean) =>
    `exporter:search:${JSON.stringify({ text, inBrowser })}`,
  saveDefinitionSettings: (rows: unknown) =>
    `exporter:saveDefinitionSettings:${JSON.stringify(rows)}`,
} as const;

/** Install the `window.EXPORTER` reply surface used by Python. */
export function initExporterBridge(): void {
  const w = window as unknown as Record<string, unknown>;
  w.EXPORTER = {
    setState: () => undefined,
    patchState: () => undefined,
    setThemeCss: () => undefined,
    focusField: () => undefined,
  } satisfies Record<string, unknown>;
}
