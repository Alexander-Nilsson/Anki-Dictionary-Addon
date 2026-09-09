<script lang="ts">
  /**
   * Automatic-definition settings — the Svelte replacement for the Qt
   * "Definition Settings" pop-out window. Picks up to three dictionaries and
   * how many definitions to pull from each when a card is added with
   * "Automatically Add Definitions" on.
   */
  import { exporter, type DefinitionSetting } from "../lib/exporter.svelte";

  interface Props {
    onclose: () => void;
  }
  let { onclose }: Props = $props();

  const names = $derived(exporter.state.dictionaryNames);

  // One-shot initializer: the modal remounts for each open.
  // svelte-ignore state_referenced_locally
  const saved = exporter.state.definitionSettings;
  let rows = $state<DefinitionSetting[]>(
    [0, 1, 2].map((i) => ({
      name: saved[i]?.name ?? "",
      limit: saved[i]?.limit ?? 1,
    })),
  );

  const ordinals = ["1st", "2nd", "3rd"];

  function save(): void {
    exporter.saveDefinitionSettings($state.snapshot(rows));
    onclose();
  }
</script>

<div class="modal-backdrop" role="presentation" onclick={onclose}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="modal" role="dialog" tabindex="-1" aria-label="Definition Settings" onclick={(e) => e.stopPropagation()}>
    <div class="modal-header">
      <h3>Automatic Definition Settings</h3>
    </div>
    <div class="modal-body">
      <p class="hint">
        When a card is added with a word, definitions are pulled automatically
        from these dictionaries.
      </p>
      {#each rows as row, i (i)}
        <div class="field">
          <label for="def-dict-{i}">{ordinals[i]} Dictionary</label>
          <select
            id="def-dict-{i}"
            value={row.name}
            onchange={(e) => (rows[i].name = e.currentTarget.value)}
          >
            <option value="">None</option>
            {#each names as name (name)}
              <option value={name}>{name}</option>
            {/each}
          </select>
          <label class="inline" for="def-limit-{i}">Max</label>
          <input
            id="def-limit-{i}"
            type="number"
            min="1"
            max="20"
            style="width:76px;flex:0 0 auto"
            value={row.limit}
            oninput={(e) => (rows[i].limit = Number(e.currentTarget.value) || 1)}
          />
        </div>
      {/each}
    </div>
    <div class="modal-footer">
      <button type="button" class="btn" onclick={onclose}>Cancel</button>
      <button type="button" class="btn primary" onclick={save}>Save Settings</button>
    </div>
  </div>
</div>
