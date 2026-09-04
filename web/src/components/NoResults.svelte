<script lang="ts">
  import type { NoResultsBlockData } from "../lib/types";

  const { block }: { block: NoResultsBlockData } = $props();
</script>

<div class="vertical-center noresults">
  <div style="text-align:center">
    <img src={block.icon} width="50px" height="40px" alt="" />
    <h3 style="text-align:center">
      No dictionary entries were found for {block.term}.
    </h3>
  </div>
</div>