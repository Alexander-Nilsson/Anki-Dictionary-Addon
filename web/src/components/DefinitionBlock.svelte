<script lang="ts">
  import type { DefinitionBlockData } from "../lib/types";
  import { fontFamilyFromAttr } from "../lib/dom";

  const { block }: { block: DefinitionBlockData } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(block.font));
</script>

<div class="definitionBlock" style:font-family={fontFamily}>
  {@html block.html}
</div>