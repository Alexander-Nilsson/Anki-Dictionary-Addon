import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// Dev-server configuration only. The production bundles are built by
// `scripts/build-pages.mjs` (one single-entry IIFE build per page so each
// page is fully self-contained) and then inlined by `scripts/inline.mjs`.
// Do not add a multi-page `build` section here: a shared chunk would split
// out as a `modulepreload` link that the inline step drops.
export default defineConfig({
  plugins: [svelte()],
  base: "./",
});