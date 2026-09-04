<script lang="ts">
  import type { DictionaryTitleBlockData } from "../lib/types";
  import { fontFamilyFromAttr, navigate } from "../lib/dom";

  const { block }: { block: DictionaryTitleBlockData } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(block.font));

  function navigateDict(ev: Event, next: boolean): void {
    const el = (ev.currentTarget as HTMLElement).closest(
      ".dictionaryTitleBlock",
    ) as HTMLElement | null;
    if (el) navigate(el, next, "dictionaryTitleBlock");
  }

  function onNavKey(ev: KeyboardEvent, next: boolean): void {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      navigateDict(ev, next);
    }
  }
</script>

<div class="dictionaryTitleBlock" data-index={block.dataIndex}>
  <div class="dictionaryTitle" style:font-family={fontFamily}>
    {block.title}
  </div>
  <div class="dictionarySettings">
    {#if block.overwriteHtml}
      {@html block.overwriteHtml}
    {/if}
    {#if block.fieldHtml}
      {@html block.fieldHtml}
    {/if}
    <div class="dictNav">
      <div
        role="button"
        tabindex="0"
        aria-label="Previous dictionary"
        class="prevDict"
        data-key-handled
        onclick={(e) => navigateDict(e, false)}
        onkeydown={(e) => onNavKey(e, false)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        ><path d="M15 18l-6-6 6-6" /></svg>
      </div>
      <div
        role="button"
        tabindex="0"
        aria-label="Next dictionary"
        class="nextDict"
        data-key-handled
        onclick={(e) => navigateDict(e, true)}
        onkeydown={(e) => onNavKey(e, true)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        ><path d="M9 6l6 6-6 6" /></svg>
      </div>
    </div>
  </div>
</div>