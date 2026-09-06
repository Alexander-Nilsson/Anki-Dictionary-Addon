<script lang="ts">
  import { onMount } from "svelte";
  import { settings, clearFontFile } from "../../lib/settings.svelte";
  import { pycmd } from "../../lib/pycmd";

  interface Props {
    name: string | null;
    group: Record<string, unknown> | null;
    oncancel: () => void;
    onsave: () => void;
  }
  let {
    name = null,
    group = null,
    oncancel,
    onsave,
  }: Props = $props();

  interface DictRow {
    name: string;
    selected: boolean;
  }

  const dictionaryNames: string[] = settings.dictionaryNames;

  // The group/name props are one-shot initializers — the modal remounts fresh
  // for each edit (via {#if}), so snapshotting them is intentional.
  // svelte-ignore state_referenced_locally
  let groupName = $state(name ?? "");
  // svelte-ignore state_referenced_locally
  let fontFromDropdown = $state(!(group?.customFont ?? false));
  // svelte-ignore state_referenced_locally
  let fontDropdown = $state(String(group?.font ?? ""));
  // svelte-ignore state_referenced_locally
  let fontFile = $state(String(group?.font ?? ""));
  // svelte-ignore state_referenced_locally
  let useCustomFont = $state(Boolean(group?.customFont ?? false));

  // Sync a path picked by the native font browser (SETTINGS.setFontFile) into
  // the Font File input. clearFontFile() on open prevents a stale pick from a
  // previously edited group from leaking in.
  onMount(() => clearFontFile());
  $effect(() => {
    if (settings.fontFile) fontFile = settings.fontFile;
  });

  // Pre-select dictionaries already in the group.
  // svelte-ignore state_referenced_locally
  const existing = Array.isArray(group?.dictionaries)
    ? (group?.dictionaries as string[])
    : [];
  let rows = $state<DictRow[]>(
    dictionaryNames.map((dn) => ({ name: dn, selected: existing.includes(dn) })),
  );

  function toggleAll(selected: boolean): void {
    rows = rows.map((r) => ({ ...r, selected }));
  }

  function save(): void {
    if (!groupName.trim()) {
      alert("The dictionary group must have a name.");
      return;
    }
    const groups = (settings.dirty.DictionaryGroups ?? {}) as Record<string, unknown>;
    const selected = rows.filter((r) => r.selected).map((r) => r.name);
    const font = fontFromDropdown ? fontDropdown : fontFile;
    groups[groupName.trim()] = {
      dictionaries: selected,
      customFont: useCustomFont && font.trim() !== "",
      font: font.trim(),
    };
    settings.dirty.DictionaryGroups = groups;
    settings.dirty = settings.dirty;
    onsave();
  }
</script>

<div
  class="modal-backdrop"
  role="presentation"
  onclick={(e) => {
    if (e.target === e.currentTarget) oncancel();
  }}
  onkeydown={(e) => {
    if (e.key === "Escape") oncancel();
  }}
>
  <div class="modal" role="dialog" aria-modal="true" tabindex="-1">
    <div class="modal-header">
      <h3>{name ? "Edit Dictionary Group" : "Add Dictionary Group"}</h3>
      <button type="button" class="btn" onclick={oncancel}>✕</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label for="grpName">Group Name</label>
        <input
          id="grpName"
          type="text"
          value={groupName}
          disabled={name !== null}
          oninput={(e) => (groupName = e.currentTarget.value)}
        />
      </div>

      <label class="check">
        <input type="checkbox" checked={useCustomFont} onchange={(e) => (useCustomFont = e.currentTarget.checked)} />
        Custom Font
      </label>

      {#if useCustomFont}
        <div class="field">
          <span class="field-label" id="fontSourceLabel">Font Source</span>
          <div style="flex:1;display:flex;gap:8px" role="group" aria-labelledby="fontSourceLabel">
            <button type="button" class:btn={true} class:primary={fontFromDropdown} onclick={() => (fontFromDropdown = true)}>From Dropdown</button>
            <button type="button" class:btn={true} class:primary={!fontFromDropdown} onclick={() => (fontFromDropdown = false)}>From File</button>
          </div>
        </div>
        {#if fontFromDropdown}
          <div class="field">
            <label for="fontDrop">Font</label>
            <input id="fontDrop" type="text" value={fontDropdown} oninput={(e) => (fontDropdown = e.currentTarget.value)} />
          </div>
        {:else}
          <div class="field">
            <label for="fontFile">Font File</label>
            <div style="flex:1;display:flex;gap:8px">
              <input id="fontFile" type="text" value={fontFile} oninput={(e) => (fontFile = e.currentTarget.value)} />
              <button type="button" class="btn" onclick={() => pycmd("settings:browseFontFile")}>Browse…</button>
            </div>
          </div>
        {/if}
      {/if}

      <div style="display:flex;gap:8px;justify-content:flex-end;margin:10px 0">
        <button type="button" class="btn" onclick={() => toggleAll(true)}>Select All</button>
        <button type="button" class="btn" onclick={() => toggleAll(false)}>Deselect All</button>
      </div>

      <div class="list" style="max-height:240px;overflow-y:auto">
        {#each rows as row, i (row.name)}
          <label class="check">
            <input type="checkbox" checked={row.selected} onchange={(e) => { rows[i] = { ...row, selected: e.currentTarget.checked }; }} />
            {row.name}
          </label>
        {/each}
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn" onclick={oncancel}>Cancel</button>
      <button type="button" class="btn primary" onclick={save}>Save</button>
    </div>
  </div>
</div>