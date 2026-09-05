<script lang="ts">
  import type { Tab } from "../lib/types";
  import DefinitionBlock from "./DefinitionBlock.svelte";
  import DictionaryTitleBlock from "./DictionaryTitleBlock.svelte";
  import LoaderBlock from "./LoaderBlock.svelte";
  import NoResults from "./NoResults.svelte";
  import Sidebar from "./Sidebar.svelte";
  import TermPronunciation from "./TermPronunciation.svelte";
  import { applySidebarState, isMounted, ui } from "../lib/tabs.svelte";

  const { tab, active }: { tab: Tab; active: boolean } = $props();

  // A3 lazy render: inactive tabs that have never been mounted stay empty
  // (display:none) so their image grids / LLM text don't stay live in the DOM
  // and cause memory creep. Activating a tab flips its mounted flag.
  const rendered = $derived(active || isMounted(tab.id) || ui.mounted.has(tab.id));

  // Newly-rendered (or newly-shown) content must reflect the current global
  // sidebar state — the sidebar lives inside the tab markup.
  $effect(() => {
    active;
    applySidebarState();
  });
</script>

{#if rendered}
  <div
    class="tabContent"
    class:active
    class:doc-mode={!!tab.doc}
    style:display={active ? "block" : "none"}
    data-index={tab.id}
  >
    {#if tab.doc}
      <!-- Phase 2: typed components render the structured search document. -->
      <Sidebar doc={tab.doc} />
      <div class="mainDictDisplay">
        {#each tab.doc.blocks as block, i (i)}
          {#if block.type === "dictionaryTitle"}
            <DictionaryTitleBlock block={block} />
          {:else if block.type === "termPronunciation"}
            <TermPronunciation doc={tab.doc} block={block} />
          {:else if block.type === "definition"}
            <DefinitionBlock block={block} />
          {:else if block.type === "noResults"}
            <NoResults block={block} />
          {:else}
            <LoaderBlock block={block} />
          {/if}
        {/each}
      </div>
    {:else}
      <!-- Legacy/Phase-1 tabs: Python-generated HTML injected raw. -->
      {@html tab.html}
    {/if}
  </div>
{/if}