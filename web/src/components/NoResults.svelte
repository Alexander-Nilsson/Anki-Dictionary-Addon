<script lang="ts">
  import type { NoResultsBlockData } from "../lib/types";
  import { CMD, pycmd } from "../lib/pycmd";

  const { block }: { block: NoResultsBlockData } = $props();

  const hint = $derived(block.deinflected || "");
  const suggestions = $derived(block.suggestions ?? []);

  /** Re-run a search for a suggested / deinflected form (U4). */
  function search(term: string): void {
    if (!term) return;
    pycmd(CMD.searchTerm(term));
  }
</script>

<div class="vertical-center noresults">
  <div style="text-align:center">
    <img src={block.icon} width="50px" height="40px" alt="" />
    <h3 style="text-align:center">
      No dictionary entries were found for {block.term}.
    </h3>
    {#if hint}
      <p class="deinflect-hint">
        That looks inflected — try the dictionary form
        <button
          type="button"
          class="suggestion-chip"
          data-key-handled
          onclick={() => search(hint)}
        >
          {hint}
        </button>
      </p>
    {/if}
    {#if suggestions.length > 0}
      <p class="suggestion-label">Did you mean…</p>
      <div class="suggestion-row">
        {#each suggestions as s (s)}
          <button
            type="button"
            class="suggestion-chip"
            data-key-handled
            onclick={() => search(s)}
          >
            {s}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>