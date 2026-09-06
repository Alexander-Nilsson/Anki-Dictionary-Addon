#!/usr/bin/env node
/**
 * Builds each Svelte page as its own single-entry bundle.
 *
 * The two UI pages (dictionary results shell + settings window) used to be
 * built in one multi-page pass with `format: "es"`. That made Rollup split
 * the shared code (Svelte runtime, the `pycmd` CMD object, the settings
 * bridge) into a shared `legacy-*.js` chunk, emitted as a `modulepreload`
 * link — which `scripts/inline.mjs` drops when inlining into a single,
 * self-contained HTML file. The inlined pages therefore lost the shared
 * chunk and were broken at runtime (`searchTerm:` and friends missing from
 * the bundle).
 *
 * Instead, we build each page separately (single entry, IIFE with dynamic
 * imports inlined), so every page bundle is self-contained with no shared
 * chunks. `scripts/inline.mjs` then inlines each page's one script + CSS.
 */
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(here, "..");
const dist = resolve(webDir, "dist");

rmSync(dist, { recursive: true, force: true });

/** Common options for a single-page build. */
function pageConfig(pageKey, htmlName, clearOutDir) {
  return {
    // Do NOT auto-load web/vite.config.ts: that is the dev-server config, and
    // merging it here would double-register the Svelte plugin (compiling
    // already-compiled .svelte.ts files) and re-introduce the multi-page
    // input that splits a shared chunk out of each page.
    configFile: false,
    root: webDir,
    base: "./",
    plugins: [svelte()],
    build: {
      outDir: dist,
      // Only the first build may clear the shared dist/ directory.
      emptyOutDir: clearOutDir,
      cssCodeSplit: false,
      rollupOptions: {
        input: { [pageKey]: resolve(webDir, htmlName) },
        output: {
          format: "es",
          entryFileNames: "assets/[name].js",
          chunkFileNames: "assets/[name]-[hash].js",
          // Content-hashed asset names keep the two builds' CSS distinct
          // (e.g. `style-<hash>.css`) since they share an output directory.
          assetFileNames: "assets/[name]-[hash].[ext]",
        },
      },
    },
  };
}

// Dictionary results shell (built first; may wipe dist/).
await build(pageConfig("index", "index.html", true));
// Settings window (must keep the dictionary outputs in dist/).
await build(pageConfig("settings", "settings.html", false));

console.log("✅ Built dictionary + settings bundles into web/dist");