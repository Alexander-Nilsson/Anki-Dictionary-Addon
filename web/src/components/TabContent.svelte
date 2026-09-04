<script lang="ts">
  import type { Tab } from "../lib/types";
  import { applySidebarState } from "../lib/tabs.svelte";

  const { tab, active }: { tab: Tab; active: boolean } = $props();

  // Newly-rendered (or newly-shown) content must reflect the current global
  // sidebar state — the sidebar lives inside the injected {#html} markup.
  $effect(() => {
    active;
    applySidebarState();
  });
</script>

<div
  class="tabContent"
  class:active
  style:display={active ? "block" : "none"}
  data-index={tab.id}
>
  {@html tab.html}
</div>