<script lang="ts">
  import Chrome from "./Chrome.svelte";
  import TabBar from "./TabBar.svelte";
  import TabContent from "./TabContent.svelte";
  import Toaster from "./Toaster.svelte";
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

  // Floating "back to top" — only visible once the results pane has been
  // scrolled down. Re-attaches whenever tabs are added/removed or the active
  // tab changes (each switch restores that tab's scroll position).
  const TOP_AFTER = 600;
  let showTop = $state(false);

  $effect(() => {
    ui.tabs;
    ui.activeId;
    const defBox = document.getElementById("defBox");
    if (!defBox) {
      showTop = false;
      return;
    }
    const onScroll = () => {
      showTop = defBox.scrollTop > TOP_AFTER;
    };
    onScroll();
    defBox.addEventListener("scroll", onScroll, { passive: true });
    return () => defBox.removeEventListener("scroll", onScroll);
  });

  function scrollToTop(): void {
    const defBox = document.getElementById("defBox");
    if (defBox) defBox.scrollTop = 0;
  }
</script>

<div id="dictBox" class={ui.tabs.length === 0 ? "no-tabs" : ""}>
  <div id="tabContainer">
    <Chrome />
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
  <button
    class="backToTop"
    class:show={showTop}
    type="button"
    aria-label="Back to top"
    title="Back to top"
    onclick={scrollToTop}
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.4"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  </button>
  <Toaster />
</div>