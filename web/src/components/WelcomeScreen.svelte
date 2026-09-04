<script lang="ts">
  let { html }: { html: string } = $props();
</script>

<div id="welcomeBackground">
  {@html html}
</div>