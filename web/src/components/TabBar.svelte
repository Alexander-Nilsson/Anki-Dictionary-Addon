<script lang="ts">
  import {
    activate,
    closeTab,
    ui,
    updateTermFromTab,
  } from "../lib/tabs.svelte";
  import { CMD, pycmd } from "../lib/pycmd";

  let tabsElement: HTMLDivElement | undefined = $state();
  let canScrollLeft = $state(false);
  let canScrollRight = $state(false);

  // Track whether the tab strip overflows so edge fades can appear.
  $effect(() => {
    const el = tabsElement;
    if (!el) return;
    const update = (): void => {
      canScrollLeft = el.scrollLeft > 4;
      canScrollRight = el.scrollLeft + el.clientWidth < el.scrollWidth - 4;
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  });

  // When the active tab changes, keep it visible in the (possibly overflowing)
  // tab strip.
  $effect(() => {
    ui.activeId;
    tabsElement
      ?.querySelector(".tablinks.active")
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
</script>

<div id="tabs" bind:this={tabsElement}>
  {#each ui.tabs as tab (tab.id)}
    <button
      type="button"
      class="tablinks"
      class:active={tab.id === ui.activeId}
      data-index={tab.id}
      title={tab.term}
      onclick={() => {
        activate(tab.id);
        updateTermFromTab(tab.id);
      }}
      onauxclick={(e) => {
        // Middle-click closes the tab.
        if (e.button === 1) {
          e.preventDefault();
          closeTab(tab.id);
        }
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
  <span
    class="tabs-fade tabs-fade-left"
    class:visible={canScrollLeft}
    aria-hidden="true"
  ></span>
  <span
    class="tabs-fade tabs-fade-right"
    class:visible={canScrollRight}
    aria-hidden="true"
  ></span>
  <button
    type="button"
    class="tablinks help-button"
    aria-label="Open dictionary settings and guide"
    title="Settings & guide"
    onclick={() => pycmd(CMD.openSettings())}
    >?</button
  >
</div>