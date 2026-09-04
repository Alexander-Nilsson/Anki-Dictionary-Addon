<script lang="ts">
  import type { DefinitionBlockData } from "../lib/types";
  import { fontFamilyFromAttr } from "../lib/dom";

  const { block }: { block: DefinitionBlockData } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(block.font));

  // QW5: very tall definition bodies collapse to a capped height with a
  // "show more" fade button. Measurement happens once per component (el is
  // stable for the block's lifetime). No text is removed — only clipped.
  const COLLAPSE_AT = 460; // px of definition body
  let el: HTMLDivElement | undefined = $state();
  let collapsible = $state(false);
  let collapsed = $state(false);

  $effect(() => {
    const node = el;
    if (!node || collapsible) return;
    collapsible = node.scrollHeight > COLLAPSE_AT;
    collapsed = collapsible;
  });
</script>

<div
  class="definitionBlock"
  class:collapsible
  class:collapsed
  bind:this={el}
  style:font-family={fontFamily}
>
  {@html block.html}
  {#if collapsible && collapsed}
    <button
      type="button"
      class="defExpand"
      data-key-handled
      aria-label="Show more"
      onclick={() => (collapsed = false)}
    >…show more</button>
  {/if}
</div>