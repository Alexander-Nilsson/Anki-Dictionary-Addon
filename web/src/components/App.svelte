<script lang="ts">
  import TabBar from "./TabBar.svelte";
  import TabContent from "./TabContent.svelte";
  import WelcomeScreen from "./WelcomeScreen.svelte";
  import {
    applySidebarState,
    resizer,
    ui,
  } from "../lib/tabs.svelte";

  // Keep injected-content sidebar/layout state in sync whenever the active
  // tab or the sidebar toggle changes.
  $effect(() => {
    ui.activeId;
    ui.sidebarOpened;
    applySidebarState();
    resizer();
  });
</script>

<div id="dictBox" class={ui.tabs.length === 0 ? "no-tabs" : ""}>
  <div id="tabContainer">
    <TabBar />
    <div id="defArea">
      {#if ui.tabs.length === 0}
        <WelcomeScreen html={ui.welcomeHtml} />
      {:else}
        <div id="defBox">
          {#each ui.tabs as tab (tab.id)}
            <TabContent {tab} active={tab.id === ui.activeId} />
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>