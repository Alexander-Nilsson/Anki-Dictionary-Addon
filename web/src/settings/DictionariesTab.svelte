<script lang="ts">
  import { settings, removeLanguage } from "../lib/settings.svelte";
  import { pycmd } from "../lib/pycmd";

  function installFromWeb(): void {
    pycmd("settings:webInstallDicts");
  }
  function importFromFiles(): void {
    pycmd("settings:importDicts");
  }
  function installFreqFromWeb(): void {
    pycmd("settings:webInstallFreq");
  }
  function importFreqFromFiles(): void {
    pycmd("settings:importFreq");
  }
</script>

<div class="card">
  <h3>Language Options</h3>
  <p class="hint">
    Manage the languages and dictionaries the addon loads. Installing
    dictionaries opens the addon's native import flow.
  </p>
  <div style="display:flex;gap:8px;margin-bottom:12px">
    <button type="button" class="btn" onclick={installFromWeb}>Install Dictionaries (Web Wizard)</button>
    <button type="button" class="btn" onclick={importFromFiles}>Install Dictionaries (Files)</button>
    <button type="button" class="btn" onclick={installFreqFromWeb}>Install Frequency Data (Web)</button>
    <button type="button" class="btn" onclick={importFreqFromFiles}>Install Frequency Data (Files)</button>
  </div>

  {#each Object.entries(settings.languagesDicts) as [lang, dicts] (lang)}
    <div class="list-row" style="margin-bottom:6px">
      <span class="name">{lang}</span>
      <span class="sub">{dicts.length} dictionaries</span>
      <button
        type="button"
        class="btn danger"
        onclick={() => {
          if (confirm(`Remove language "${lang}" and its dictionaries?`)) removeLanguage(lang);
        }}
      >
        Remove Language
      </button>
    </div>
    <div class="list" style="margin-left:18px;margin-bottom:12px">
      {#each dicts as dictName (dictName)}
        <div class="list-row">
          <span class="name">{dictName}</span>
        </div>
      {/each}
    </div>
  {/each}
  {#if Object.keys(settings.languagesDicts).length === 0}
    <p class="hint">No languages installed yet.</p>
  {/if}
</div>