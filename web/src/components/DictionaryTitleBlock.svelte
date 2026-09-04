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
      >▲</div>
      <div
        role="button"
        tabindex="0"
        aria-label="Next dictionary"
        class="nextDict"
        data-key-handled
        onclick={(e) => navigateDict(e, true)}
        onkeydown={(e) => onNavKey(e, true)}
      >▼</div>
    </div>
  </div>
</div>