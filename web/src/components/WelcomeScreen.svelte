<script lang="ts">
  import { modKey } from "../lib/platform";

  let { html }: { html: string } = $props();

  const modifier = modKey();

  // Python already renders {{MOD_KEY}}, but the standalone preview and any
  // cached welcome HTML may still carry the placeholder — resolve it here so
  // the badges always match the OS (⌘ on macOS, Ctrl elsewhere).
  const resolved = $derived(
    html
      .replaceAll("{{MOD_KEY}}", modifier)
      .replaceAll(
        /<div class="key__button" data-mod-key>.*?<\/div>/g,
        `<div class="key__button" data-mod-key>${modifier}</div>`,
      ),
  );
</script>

<div id="welcomeBackground">
  {@html resolved}
</div>
