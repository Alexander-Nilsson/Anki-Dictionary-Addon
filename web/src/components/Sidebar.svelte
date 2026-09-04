<script lang="ts">
  import type { DictDocument } from "../lib/types";
  import { fontFamilyFromAttr } from "../lib/dom";

  const { doc }: { doc: DictDocument } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(doc.font));

  function startResize(ev: MouseEvent): void {
    const fn = (
      window as unknown as Record<string, unknown>
    ).hresize as ((e: MouseEvent) => void) | undefined;
    fn?.(ev);
  }
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