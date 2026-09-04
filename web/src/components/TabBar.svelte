<script lang="ts">
  import {
    activate,
    closeTab,
    ui,
    updateTermFromTab,
  } from "../lib/tabs.svelte";
</script>

<div id="tabs">
  {#each ui.tabs as tab (tab.id)}
    <button
      type="button"
      class="tablinks"
      class:active={tab.id === ui.activeId}
      data-index={tab.id}
      onclick={() => {
        activate(tab.id);
        updateTermFromTab(tab.id);
      }}
    >
      <span>{tab.term}</span>
      <span
        class="tab-close"
        role="button"
        tabindex="0"
        aria-label="Close tab"
        onclick={(e) => {
          e.stopPropagation();
          closeTab(tab.id);
        }}
        onkeydown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            closeTab(tab.id);
          }
        }}
        >&times;</span
      >
    </button>
  {/each}
</div>