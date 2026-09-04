<script lang="ts">
  import type { LoaderBlockData } from "../lib/types";

  const { block }: { block: LoaderBlockData } = $props();
</script>

<!--
  Opaque section for the dynamic services (Images / LLM / Forvo). The HTML is
  the placeholder markup Python already emits; async results inject into it via
  loadImageHtml / loadLLMResults / onForvoResult, so this stays raw.
-->
{@html block.html}