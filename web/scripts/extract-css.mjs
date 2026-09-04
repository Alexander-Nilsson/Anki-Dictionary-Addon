#!/usr/bin/env node
/**
 * One-time migration helper: extracts the <style> blocks from the legacy
 * assets/templates/dictionary.html into web/src/legacy.css so the Svelte UI
 * starts from the exact same stylesheet. Safe to delete after the port.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const htmlPath = join(root, "assets", "templates", "dictionary.html");
const outPath = join(here, "..", "src", "legacy.css");

const html = readFileSync(htmlPath, "utf8");
// Skip runtime-mutable placeholder blocks (fontSpecs, widthSpecs, userSelect,
// customThemeCss, nightModeCss) — those remain dynamic <style> elements in the
// shell and are injected at runtime, not part of the static stylesheet.
const SKIP_IDS = new Set([
  "fontSpecs",
  "widthSpecs",
  "userSelect",
  "customThemeCss",
  "nightModeCss",
]);
const blocks = [...html.matchAll(/<style([^>]*)>([\s\S]*?)<\/style>/g)]
  .filter((m) => {
    const idMatch = m[1].match(/\bid="([^"]+)"/);
    return !idMatch || !SKIP_IDS.has(idMatch[1]);
  })
  .map((m) => m[2].trim())
  .filter(Boolean);

if (blocks.length === 0) {
  console.error("No <style> blocks found in dictionary.html");
  process.exit(1);
}

const banner = `/*\n * Legacy styles extracted from assets/templates/dictionary.html.\n * Phase 1 of the Svelte rewrite: the shell and components re-render the same\n * DOM structure, so this stylesheet keeps the look identical while the UI is\n * progressively componentized. Future phases migrate chunks into per-component\n * styles.\n */\n`;

writeFileSync(outPath, `${banner}\n${blocks.join("\n\n")}\n`, "utf8");
console.log(`✅ Extracted ${blocks.length} <style> block(s) -> ${outPath}`);