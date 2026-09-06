#!/usr/bin/env node
/**
 * Post-build step: turns Vite's multi-page `dist/*.html` outputs into single,
 * self-contained HTML files suitable for Anki's QtWebEngine (AnkiWebView).
 *
 * Inputs → outputs:
 *   dist/index.html    → dist/dictionary.html   (results shell)
 *   dist/settings.html → dist/settings.html      (settings window)
 *
 * For each page:
 * - Inlines the JS bundles (shared chunks + entry chunk, in emitted order)
 *   as plain (classic) `<script>` tags.
 * - Inlines the CSS bundle into a `<style>` in `<head>`.
 * - Drops `modulepreload` links (not needed for inline bundles).
 * - Escapes `</script>` sequences in the JS so it can live inside a script tag.
 *
 * The dictionary output mirrors the contract of the legacy
 * `assets/templates/dictionary.html` so Python's `getHTMLURL` injection (theme
 * CSS, welcome content, font sizes) keeps working unchanged. The settings
 * output is a self-contained page hosted by the settings bridge.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "dist");

/** Escape `</script` so the JS is safe inside a <script> element. */
function escapeScript(text) {
  return text.replace(/<\/script/gi, "<\\/script");
}

/**
 * Inline one built page (dist/<srcName>) into a self-contained HTML file
 * (dist/<outName>). Returns the number of JS bundles inlined.
 */
function inlinePage(srcName, outName, injectAfter) {
  const htmlPath = join(dist, srcName);
  let html = readFileSync(htmlPath, "utf8");

  // 1. Inline CSS.
  html = html.replace(
    /<link rel="stylesheet"[^>]*href="\.\/([^"]+\.css)"[^>]*>/gi,
    (match) => {
      const css = readFileSync(
        join(dist, match.match(/href="\.\/([^"]+\.css)"/)[1]),
        "utf8",
      );
      return `<style>\n${css}\n</style>`;
    },
  );

  // 2. Inline JS: capture every module script (shared chunks + entry), strip
  //    the tags, and re-insert as classic scripts (in the same order) before
  //    `</body>` (or after `injectAfter`).
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
    console.warn(`No module script found in ${srcName}; nothing to inline.`);
    return 0;
  }

  // 4. Insert the inlined scripts. For the dictionary page, insert after the
  //    welcome placeholder so the app mounts after the welcome content (and
  //    Python-injected font vars) are in the DOM.
  //
  // IMPORTANT: use *function* replacements here. A string replacement would
  // interpret `$` escape sequences that appear inside the bundle's own JS
  // (`$&`, `` $` ``, `$'`, `$$` — e.g. the regex-escape idiom `` '\\$&' `` used
  // by cleanTermDef). `String.replace` would substitute the matched substring /
  // document prefix / suffix into the script, corrupting the bundle and
  // splicing an unescaped `</script>` into it.
  const insertion = jsTags.join("\n    ");
  if (injectAfter && html.includes(injectAfter)) {
    html = html.replace(injectAfter, () => `${injectAfter}\n    ${insertion}`);
  } else {
    html = html.replace("</body>", () => `${insertion}\n</body>`);
  }

  const outPath = join(dist, outName);
  writeFileSync(outPath, html, "utf8");
  console.log(
    `✅ Inlined bundle written to ${outPath} (${jsTags.length} script(s), CSS inlined)`,
  );
  return jsTags.length;
}

inlinePage("index.html", "dictionary.html", '<div id="welcomeBackground"></div>');
inlinePage("settings.html", "settings.html", null);