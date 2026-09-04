import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// The Svelte UI runs inside Anki's QtWebEngine (AnkiWebView) as a plain,
// self-contained HTML page. We therefore build to a single classic script
// (IIFE) and inline its output into `dictionary.html` via `scripts/inline.mjs`.
export default defineConfig({
  plugins: [svelte()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        format: "iife",
        inlineDynamicImports: true,
        name: "AnkiDictionaryUI",
      },
    },
  },
});