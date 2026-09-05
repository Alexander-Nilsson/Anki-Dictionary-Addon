<script lang="ts">
  import { onMount } from "svelte";
  import type { DictDocument } from "../lib/types";
  import { fontFamilyFromAttr } from "../lib/dom";
  import { CMD, pycmd } from "../lib/pycmd";
  import { refreshHistory, ui } from "../lib/tabs.svelte";

  const { doc }: { doc: DictDocument } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(doc.font));

  function startResize(ev: MouseEvent): void {
    const fn = (
      window as unknown as Record<string, unknown>
    ).hresize as ((e: MouseEvent) => void) | undefined;
    fn?.(ev);
  }

  /** Click a history entry to re-search it (U3). */
  function research(term: string): void {
    if (term) pycmd(CMD.searchTerm(term));
  }

  /** Prune a single history entry (U3) — Python pushes the refreshed list. */
  function prune(term: string): void {
    if (term) pycmd(CMD.deleteSearchHistory(term));
  }

  // The sidebar lives per-tab but history is shared; refresh once on mount so
  // the first painted sidebar has data (subsequent pushes keep it live).
  onMount(refreshHistory);
</script>

<div
  class="definitionSideBar"
  style:font-family={fontFamily}
>
  <div class="innerSideBar">
    {#each doc.sidebar as dict (dict.dataIndex)}
      <div data-index={dict.dataIndex} class="listTitle">{dict.displayName}</div>
      <ol class="foundEntriesList">
        {#each dict.entries as entry (entry.dataIndex)}
          <li data-index={entry.dataIndex}>{@html entry.headerHtml}</li>
        {/each}
      </ol>
    {/each}
    <!-- U3: recent searches with dates; click to re-search, × to prune. -->
    {#if ui.history.length > 0}
      <div class="sidebarHistory">
        <div class="listTitle">Recent searches</div>
        <ul class="historyList">
          {#each ui.history as h (h.term)}
            <li class="historyEntry">
              <button
                type="button"
                class="historyTerm"
                data-key-handled
                title={`Re-search "${h.term}"`}
                onclick={() => research(h.term)}
              >
                {h.term}
              </button>
              <span class="historyDate">{h.date}</span>
              <button
                type="button"
                class="historyPrune"
                title="Remove from history"
                aria-label={`Remove ${h.term} from history`}
                data-key-handled
                onclick={() => prune(h.term)}
              >
                ×
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
    <br />
  </div>
  <!-- Drag handle: mouse-only by design (keyboard users resize via the
       settings dialog); the ARIA role mirrors the legacy resizeBar. -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="resizeBar"
    role="separator"
    aria-label="Resize sidebar"
    aria-orientation="vertical"
    onmousedown={startResize}
  ></div>
</div>