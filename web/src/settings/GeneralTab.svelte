<script lang="ts">
  import { settings, saveSettings } from "../lib/settings.svelte";
  import DictGroupEditorModal from "./modals/DictGroupEditorModal.svelte";
  import ExportTemplateModal from "./modals/ExportTemplateModal.svelte";

  interface Group {
    dictionaries?: string[];
    customFont?: boolean;
    font?: string;
    [key: string]: unknown;
  }
  interface TemplateFields {
    noteType?: string;
    sentence?: string;
    secondary?: string;
    notes?: string;
    word?: string;
    image?: string;
    audio?: string;
    unspecified?: string;
    specific?: Record<string, string[]>;
    separator?: string;
    [key: string]: unknown;
  }

  let editingGroupName = $state<string | null>(null);
  let editingGroup = $state<Group | null>(null);
  let showGroupModal = $state(false);

  let editingTemplateName = $state<string | null>(null);
  let editingTemplate = $state<TemplateFields | null>(null);
  let showTemplateModal = $state(false);

  const cfg = {
    get: (k: string, d: unknown) => settings.dirty[k] ?? d,
    set: (k: string, v: unknown) => {
      settings.dirty[k] = v;
      settings.dirty = settings.dirty;
    },
  };

  function groups(): Record<string, Group> {
    const g = cfg.get("DictionaryGroups", {});
    return typeof g === "object" && g ? (g as Record<string, Group>) : {};
  }

  function templates(): Record<string, TemplateFields> {
    const t = cfg.get("ExportTemplates", {});
    return typeof t === "object" && t ? (t as Record<string, TemplateFields>) : {};
  }

  function addGroupEditor(): void {
    editingGroupName = null;
    editingGroup = null;
    showGroupModal = true;
  }

  function editGroupEditor(name: string): void {
    editingGroupName = name;
    editingGroup = { ...(groups()[name] ?? {}) };
    showGroupModal = true;
  }

  function removeGroup(name: string): void {
    if (!confirm(`Remove dictionary group "${name}"?`)) return;
    const g = groups();
    delete g[name];
    cfg.set("DictionaryGroups", g);
    // Drop any language defaults pointing at the removed group.
    const langDefaults = { ...(cfg.get("language_defaults", {}) as Record<string, string>) };
    for (const k of Object.keys(langDefaults)) {
      if (langDefaults[k] === name) delete langDefaults[k];
    }
    cfg.set("language_defaults", langDefaults);
  }

  function dictionaryCount(group: Group): string {
    const n = (group.dictionaries ?? []).length;
    return `${n} ${n === 1 ? "dictionary" : "dictionaries"}`;
  }

  function addTemplateEditor(): void {
    editingTemplateName = null;
    editingTemplate = null;
    showTemplateModal = true;
  }

  function editTemplateEditor(name: string): void {
    editingTemplateName = name;
    editingTemplate = { ...(templates()[name] ?? {}) };
    showTemplateModal = true;
  }

  function removeTemplate(name: string): void {
    if (!confirm(`Remove export template "${name}"?`)) return;
    const t = templates();
    delete t[name];
    cfg.set("ExportTemplates", t);
  }
</script>

<!-- Dictionary Groups -->
<div class="card">
  <h3>Dictionary Groups</h3>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("auto_select_dict_group", true)} onchange={(e) => cfg.set("auto_select_dict_group", e.currentTarget.checked)} />
    Auto-Select (switch group by term script)
  </label>
  <div class="list">
    {#each Object.entries(groups()) as [name, g] (name)}
      <div class="list-row">
        <span class="name">{name}</span>
        <span class="sub">{dictionaryCount(g)}</span>
        <button type="button" class="btn" onclick={() => editGroupEditor(name)}>Edit</button>
        <button type="button" class="btn danger" onclick={() => removeGroup(name)}>Remove</button>
      </div>
    {/each}
    {#if Object.keys(groups()).length === 0}
      <p class="hint">No dictionary groups yet.</p>
    {/if}
  </div>
  <button type="button" class="btn" onclick={addGroupEditor}>Add Dictionary Group</button>
</div>

<!-- Export Templates -->
<div class="card">
  <h3>Export Templates</h3>
  <div class="list">
    {#each Object.entries(templates()) as [name, _t] (name)}
      <div class="list-row">
        <span class="name">{name}</span>
        <button type="button" class="btn" onclick={() => editTemplateEditor(name)}>Edit</button>
        <button type="button" class="btn danger" onclick={() => removeTemplate(name)}>Remove</button>
      </div>
    {/each}
    {#if Object.keys(templates()).length === 0}
      <p class="hint">No export templates yet.</p>
    {/if}
  </div>
  <button type="button" class="btn" onclick={addTemplateEditor}>Add Export Template</button>
</div>

<!-- Search & Behavior -->
<div class="card">
  <h3>Search &amp; Behavior</h3>
  <div class="field">
    <label for="maxSearch">Max Total Results</label>
    <input id="maxSearch" type="number" min="0" value={cfg.get("maxSearch", 1000)} oninput={(e) => cfg.set("maxSearch", Number(e.currentTarget.value))} />
  </div>
  <div class="field">
    <label for="dictSearch">Max per Dictionary</label>
    <input id="dictSearch" type="number" min="0" value={cfg.get("dictSearch", 50)} oninput={(e) => cfg.set("dictSearch", Number(e.currentTarget.value))} />
  </div>
  <div class="field">
    <label for="imageSearchRegion">Image Search Region</label>
    <input id="imageSearchRegion" type="text" value={cfg.get("imageSearchRegion", "United States")} oninput={(e) => cfg.set("imageSearchRegion", e.currentTarget.value)} />
  </div>
  <div class="field">
    <span class="field-label" id="bracketLabel">Surround Term</span>
    <div style="flex:1;display:flex;gap:6px;align-items:center" role="group" aria-labelledby="bracketLabel">
      <input type="text" style="width:60px" value={cfg.get("frontBracket", "【")} oninput={(e) => cfg.set("frontBracket", e.currentTarget.value)} />
      <span>Term</span>
      <input type="text" style="width:60px" value={cfg.get("backBracket", "】")} oninput={(e) => cfg.set("backBracket", e.currentTarget.value)} />
    </div>
  </div>
</div>

<!-- Display & UI -->
<div class="card">
  <h3>Display &amp; UI</h3>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("highlightTarget", true)} onchange={(e) => cfg.set("highlightTarget", e.currentTarget.checked)} />
    Highlight Searched Term
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("showTarget", false)} onchange={(e) => cfg.set("showTarget", e.currentTarget.checked)} />
    Show Export Target Identifier
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("tooltips", true)} onchange={(e) => cfg.set("tooltips", e.currentTarget.checked)} />
    Enable Tooltips
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("dictAlwaysOnTop", false)} onchange={(e) => cfg.set("dictAlwaysOnTop", e.currentTarget.checked)} />
    Keep Dictionary Always on Top
  </label>
</div>

<!-- Media & Integration -->
<div class="card">
  <h3>Media &amp; Integration</h3>
  <div class="field">
    <label for="maxWidth">Max Image Width</label>
    <input id="maxWidth" type="number" min="0" value={cfg.get("maxWidth", 1500)} oninput={(e) => cfg.set("maxWidth", Number(e.currentTarget.value))} />
  </div>
  <div class="field">
    <label for="maxHeight">Max Image Height</label>
    <input id="maxHeight" type="number" min="0" value={cfg.get("maxHeight", 400)} oninput={(e) => cfg.set("maxHeight", Number(e.currentTarget.value))} />
  </div>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("imageAutoConvert", true)} onchange={(e) => cfg.set("imageAutoConvert", e.currentTarget.checked)} />
    Auto-convert images (resize + AVIF)
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("jReadingCards", false)} onchange={(e) => cfg.set("jReadingCards", e.currentTarget.checked)} />
    Generate Japanese Readings (Export)
  </label>
</div>

{#if showGroupModal}
  <DictGroupEditorModal
    name={editingGroupName}
    group={editingGroup}
    oncancel={() => (showGroupModal = false)}
    onsave={() => {
      showGroupModal = false;
      saveSettings();
    }}
  />
{/if}

{#if showTemplateModal}
  <ExportTemplateModal
    name={editingTemplateName}
    template={editingTemplate}
    oncancel={() => (showTemplateModal = false)}
    onsave={() => {
      showTemplateModal = false;
      saveSettings();
    }}
  />
{/if}
