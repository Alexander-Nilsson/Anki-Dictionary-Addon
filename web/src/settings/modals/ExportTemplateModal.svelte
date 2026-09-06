<script lang="ts">
  import { settings } from "../../lib/settings.svelte";

  interface Props {
    name: string | null;
    template: Record<string, unknown> | null;
    oncancel: () => void;
    onsave: () => void;
  }
  let {
    name = null,
    template = null,
    oncancel,
    onsave,
  }: Props = $props();

  const noteTypes = settings.noteTypes;

  interface Row {
    dictName: string;
    fieldName: string;
  }

  // The template/name props are one-shot initializers — the modal remounts
  // fresh for each edit (via {#if}), so snapshotting them is intentional.
  // svelte-ignore state_referenced_locally
  let templateName = $state(name ?? "");
  // svelte-ignore state_referenced_locally
  let noteType = $state(String(template?.noteType ?? Object.keys(noteTypes)[0] ?? ""));
  // svelte-ignore state_referenced_locally
  let sentenceField = $state(String(template?.sentence ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let secondaryField = $state(String(template?.secondary ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let notesField = $state(String(template?.notes ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let wordField = $state(String(template?.word ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let imageField = $state(String(template?.image ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let audioField = $state(String(template?.audio ?? "Don't Export"));
  // svelte-ignore state_referenced_locally
  let otherDictsField = $state(String(template?.unspecified ?? ""));
  // svelte-ignore state_referenced_locally
  let entrySeparator = $state(String(template?.separator ?? "<br><br>"));

  const fieldsFor = $derived(noteTypes[noteType] ?? []);

  // svelte-ignore state_referenced_locally
  const specific = (template?.specific ?? {}) as Record<string, string[]>;
  let rows = $state<Row[]>(
    Object.entries(specific).flatMap(([field, dicts]) =>
      dicts.map((d) => ({ dictName: d, fieldName: field })),
    ),
  );

  let dictCombo = $state("");
  let fieldCombo = $state("");

  function addRow(): void {
    if (!dictCombo || !fieldCombo) return;
    if (rows.some((r) => r.dictName === dictCombo)) return;
    rows = [...rows, { dictName: dictCombo, fieldName: fieldCombo }];
  }
  function removeRow(i: number): void {
    rows = rows.filter((_, idx) => idx !== i);
  }

  function toSpecific(): Record<string, string[]> {
    const out: Record<string, string[]> = {};
    for (const r of rows) {
      out[r.fieldName] = [...(out[r.fieldName] ?? []), r.dictName];
    }
    return out;
  }

  function save(): void {
    if (!templateName.trim()) {
      alert("The export template must have a name.");
      return;
    }
    const templates = (settings.dirty.ExportTemplates ?? {}) as Record<string, unknown>;
    templates[templateName.trim()] = {
      noteType,
      sentence: sentenceField,
      secondary: secondaryField,
      notes: notesField,
      word: wordField,
      image: imageField,
      audio: audioField,
      unspecified: otherDictsField,
      specific: toSpecific(),
      separator: entrySeparator,
    };
    settings.dirty.ExportTemplates = templates;
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
      <h3>{name ? "Edit Export Template" : "Add Export Template"}</h3>
      <button type="button" class="btn" onclick={oncancel}>✕</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label for="tplName">Name</label>
        <input id="tplName" type="text" value={templateName} disabled={name !== null} oninput={(e) => (templateName = e.currentTarget.value)} />
      </div>
      <div class="field">
        <label for="tplNoteType">Notetype</label>
        <select id="tplNoteType" value={noteType} onchange={(e) => (noteType = e.currentTarget.value)}>
          {#each Object.keys(noteTypes).sort() as nt (nt)}
            <option value={nt}>{nt}</option>
          {/each}
        </select>
      </div>

      {#if fieldsFor.length > 0}
        <div class="field">
          <label for="sentenceField">Sentence Field</label>
          <select id="sentenceField" value={sentenceField} onchange={(e) => (sentenceField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="secondaryField">Secondary Field</label>
          <select id="secondaryField" value={secondaryField} onchange={(e) => (secondaryField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="wordField">Word Field</label>
          <select id="wordField" value={wordField} onchange={(e) => (wordField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="notesField">User Notes</label>
          <select id="notesField" value={notesField} onchange={(e) => (notesField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="imageField">Image Field</label>
          <select id="imageField" value={imageField} onchange={(e) => (imageField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="audioField">Audio Field</label>
          <select id="audioField" value={audioField} onchange={(e) => (audioField = e.currentTarget.value)}>
            <option value="Don't Export">Don't Export</option>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
        <div class="field">
          <label for="otherDictsField">Unspecified Dictionaries Field</label>
          <select id="otherDictsField" value={otherDictsField} onchange={(e) => (otherDictsField = e.currentTarget.value)}>
            {#each fieldsFor as f (f)}
              <option value={f}>{f}</option>
            {/each}
          </select>
        </div>
      {/if}

      <div style="display:flex;gap:8px;margin-bottom:8px">
        <select style="flex:1" value={dictCombo} onchange={(e) => (dictCombo = e.currentTarget.value)}>
          <option value="">Select dictionary…</option>
          {#each settings.dictionaryNames as dn (dn)}
            <option value={dn}>{dn}</option>
          {/each}
        </select>
        <select style="flex:1" value={fieldCombo} onchange={(e) => (fieldCombo = e.currentTarget.value)}>
          <option value="">Select field…</option>
          {#each fieldsFor as f (f)}
            <option value={f}>{f}</option>
          {/each}
        </select>
        <button type="button" class="btn" onclick={addRow}>Add</button>
      </div>

      <div class="list" style="max-height:160px;overflow-y:auto;margin-bottom:10px">
        {#each rows as row, i (row.dictName + row.fieldName)}
          <div class="list-row">
            <span class="name">{row.dictName}</span>
            <span class="sub">{row.fieldName}</span>
            <button type="button" class="btn danger" onclick={() => removeRow(i)}>&#x2715;</button>
          </div>
        {/each}
      </div>

      <div class="field">
        <label for="separator">Entry Separator</label>
        <input id="separator" type="text" value={entrySeparator} oninput={(e) => (entrySeparator = e.currentTarget.value)} />
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn" onclick={oncancel}>Cancel</button>
      <button type="button" class="btn primary" onclick={save}>Save</button>
    </div>
  </div>
</div>