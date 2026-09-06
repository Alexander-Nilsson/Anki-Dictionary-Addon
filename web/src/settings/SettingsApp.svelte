<script lang="ts">
  import { onMount } from "svelte";
  import { pycmd } from "../lib/pycmd";
  import { SETTINGS_CMD } from "../lib/settings-bridge";
  import { loadSettings, saveSettings, settings } from "../lib/settings.svelte";
  import GeneralTab from "./GeneralTab.svelte";
  import LlmTab from "./LlmTab.svelte";
  import ForvoTab from "./ForvoTab.svelte";
  import FrequencyTab from "./FrequencyTab.svelte";
  import DictionariesTab from "./DictionariesTab.svelte";

  type TabId = "general" | "llm" | "forvo" | "frequency" | "dictionaries";

  let active: TabId = $state("general");

  const TABS: { id: TabId; label: string }[] = [
    { id: "general", label: "Settings" },
    { id: "llm", label: "LLM" },
    { id: "forvo", label: "Forvo" },
    { id: "frequency", label: "Frequency Lists" },
    { id: "dictionaries", label: "Dictionaries" },
  ];

  let toast = $state("");

  function showToast(msg: string): void {
    toast = msg;
    setTimeout(() => {
      toast = "";
    }, 3000);
  }

  function onSave(): void {
    saveSettings();
    showToast("Settings saved");
  }

  function onRestoreDefaults(): void {
    if (
      confirm(
        "This will remove any export templates and dictionary groups you have created, and is not undoable. Are you sure you would like to restore the default settings?",
      )
    ) {
      pycmd(SETTINGS_CMD.restoreDefaults());
    }
  }

  function onClose(): void {
    pycmd(SETTINGS_CMD.close());
  }

  onMount(() => {
    loadSettings();
    // Handshake with Python — lets the bridge know the page is ready.
    pycmd(SETTINGS_CMD.loaded());
  });
</script>

<div class="settings-chrome">
  <h2 class="settings-title">Anki Dictionary Settings</h2>
  <div class="spacer"></div>
  <span class="status ok">
    {settings.configLoaded ? "Configuration loaded" : "Loading…"}
  </span>
</div>

<div class="settings-tabs" role="tablist">
  {#each TABS as tab (tab.id)}
    <button
      type="button"
      role="tab"
      class:active={active === tab.id}
      onclick={() => (active = tab.id)}
    >
      {tab.label}
    </button>
  {/each}
</div>

<div class="settings-body">
  {#if !settings.configLoaded}
    <div class="card">
      <p class="hint">Loading settings…</p>
    </div>
  {:else}
    {#if active === "general"}
      <GeneralTab />
    {:else if active === "llm"}
      <LlmTab />
    {:else if active === "forvo"}
      <ForvoTab />
    {:else if active === "frequency"}
      <FrequencyTab />
    {:else if active === "dictionaries"}
      <DictionariesTab />
    {/if}
  {/if}
</div>

<div class="settings-footer">
  <div class="spacer" style="flex:1"></div>
  <button type="button" class="btn danger" onclick={onRestoreDefaults}>
    Restore Defaults
  </button>
  <button type="button" class="btn" onclick={onClose}>
    Cancel
  </button>
  <button type="button" class="btn primary" onclick={onSave}>
    Apply
  </button>
</div>

{#if toast}
  <div class="toast">{toast}</div>
{/if}
