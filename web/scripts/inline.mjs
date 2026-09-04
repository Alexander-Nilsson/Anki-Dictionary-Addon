#!/usr/bin/env node
/**
 * Post-build step: turns Vite's `dist/index.html` into a single, self-contained
 * `dist/dictionary.html` suitable for Anki's QtWebEngine (AnkiWebView).
 *
 * - Inlines the JS bundle as a plain (classic) `<script>` before `</body>`.
 * - Inlines the CSS bundle into a `<style>` in `<head>`.
 * - Drops `modulepreload` links (not needed for a single inline bundle).
 * - Escapes `</script>` sequences in the JS so it can live inside a script tag.
 *
 * The output mirrors the contract of the legacy `assets/templates/dictionary.html`
 * so Python's `getHTMLURL` injection (theme CSS, welcome content, font sizes)
 * keeps working unchanged.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "dist");
const htmlPath = join(dist, "index.html");
const outPath = join(dist, "dictionary.html");

/** Escape `</script` so the JS is safe inside a <script> element. */
function escapeScript(text) {
  return text.replace(/<\/script/gi, "<\\/script");
}

let html = readFileSync(htmlPath, "utf8");

// 1. Inline CSS.
html = html.replace(
  /<link rel="stylesheet"[^>]*href="\.\/([^"]+\.css)"[^>]*>/gi,
  (match) => {
    const css = readFileSync(join(dist, match.match(/href="\.\/([^"]+\.css)"/)[1]), "utf8");
    return `<style>\n${css}\n</style>`;
  },
);

// 2. Inline JS: capture the module script, strip the tag, re-insert as a
//    classic script just before `</body>` (after the welcome placeholder).
const jsTags = [];
html = html.replace(
  /<script type="module"[^>]*src="\.\/([^"]+\.js)"[^>]*><\/script>/gi,
  (match) => {
    const src = match.match(/src="\.\/([^"]+\.js)"/)[1];
    const js = escapeScript(readFileSync(join(dist, src), "utf8"));
    jsTags.push(`<script>\n${js}\n</script>`);
    return "";
  },
);

// 3. Drop Vite preload hints.
html = html.replace(/<link rel="modulepreload"[^>]*>/gi, "");

if (jsTags.length === 0) {
  console.error("No module script found in dist/index.html; nothing to inline.");
  process.exit(1);
}

// Place the inlined script after the welcome placeholder so the app mounts
// after the welcome content (and Python-injected font vars) are in the DOM.
//
// IMPORTANT: use *function* replacements here. A string replacement would
// interpret `$` escape sequences that appear inside the bundle's own JS
// (`$&`, `` $` ``, `$'`, `$$` — e.g. the regex-escape idiom `` '\\$&' `` used
// by cleanTermDef). `String.replace` would substitute the matched substring /
// document prefix / suffix into the script, corrupting the bundle and
// splicing an unescaped `</script>` into it, which truncates the script at
// parse time and prevents the app from ever mounting.
const welcomeDiv = '<div id="welcomeBackground"></div>';
if (html.includes(welcomeDiv)) {
  html = html.replace(welcomeDiv, () => `${welcomeDiv}\n    ${jsTags.join("\n    ")}`);
} else {
  html = html.replace("</body>", () => `${jsTags.join("\n    ")}\n</body>`);
}

writeFileSync(outPath, html, "utf8");
console.log(`✅ Inlined bundle written to ${outPath} (${jsTags.length} script(s), CSS inlined)`);