import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

export default {
  // Use Vite's preprocess so <script lang="ts"> works out of the box.
  preprocess: vitePreprocess(),
};