<script lang="ts">
  import type { LoaderBlockData } from "../lib/types";

  const { block }: { block: LoaderBlockData } = $props();

  // QW3: replace the bare "Loading…" placeholder with a shimmer skeleton. The
  // raw Python placeholder markup is kept (async services inject into its
  // ids — loadImageHtml / loadLLMResults / onForvoResult), so the shimmer
  // sits on top and fades out once the "Loading" text is gone from the host.
  let host: HTMLDivElement | undefined = $state();
  let done = $state(false);

  $effect(() => {
    const el = host;
    if (!el) return;
    const check = () => {
      done = !/Loading/i.test(el.textContent ?? "");
    };
    check();
    const observer = new MutationObserver(check);
    observer.observe(el, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    return () => observer.disconnect();
  });
</script>

<!--
  Opaque section for the dynamic services (Images / LLM / Forvo). The HTML is
  the placeholder markup Python already emits; async results inject into it via
  loadImageHtml / loadLLMResults / onForvoResult, so this stays raw.
-->
<div class="skeletonHost" class:done bind:this={host}>
  {@html block.html}
  <div class="loaderSkeleton" aria-hidden="true"></div>
</div>