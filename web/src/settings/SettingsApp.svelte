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
  import AppearanceTab from "./AppearanceTab.svelte";

  type TabId =
    | "general"
    | "appearance"
    | "llm"
    | "forvo"
    | "frequency"
    | "dictionaries";

  let active: TabId = $state("general");

  const TABS: { id: TabId; label: string }[] = [
    { id: "general", label: "Settings" },
    { id: "appearance", label: "Appearance" },
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

  function onTabKeydown(e: KeyboardEvent): void {
    const idx = TABS.findIndex((t) => t.id === active);
    let next: number | null = null;
    if (e.key === "ArrowRight") next = (idx + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + TABS.length) % TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    if (next === null) return;
    e.preventDefault();
    active = TABS[next].id;
    document.getElementById(`tab-${TABS[next].id}`)?.focus();
  }

  // Python can steer the page to a tab (the dictionary's theme button opens
  // the gallery this way); ignore anything that isn't a real tab id.
  $effect(() => {
    const requested = settings.requestedTab;
    if (requested && TABS.some((t) => t.id === requested)) {
      active = requested as TabId;
      settings.requestedTab = "";
    }
  });

  // First run: land on the one tab that actually unblocks the addon. Do this
  // once, after the language list arrives, so a slow reply cannot move the
  // user out of a tab they picked.
  let setupTabApplied = $state(false);
  $effect(() => {
    if (setupTabApplied || !settings.languagesLoaded) return;
    setupTabApplied = true;
    if (Object.keys(settings.languagesDicts).length === 0) {
      active = "dictionaries";
    }
  });

  onMount(() => {
    loadSettings();
    // Handshake with Python — lets the bridge know the page is ready.
    pycmd(SETTINGS_CMD.loaded());
  });
</script>

<header class="settings-header">
  <h2 class="settings-title">Anki Dictionary Settings</h2>
  <div class="settings-tabs" role="tablist" aria-label="Settings sections" tabindex="-1" onkeydown={onTabKeydown}>
    {#each TABS as tab (tab.id)}
      <button
        type="button"
        role="tab"
        id={`tab-${tab.id}`}
        aria-selected={active === tab.id}
        aria-controls="settings-body"
        tabindex={active === tab.id ? 0 : -1}
        class:active={active === tab.id}
        onclick={() => (active = tab.id)}
      >
        {tab.label}
      </button>
    {/each}
  </div>
</header>

<div class="settings-body" id="settings-body" role="tabpanel">
  {#if !settings.configLoaded}
    <div class="card">
      <p class="hint">Loading settings…</p>
    </div>
  {:else}
    {#if active === "general"}
      <GeneralTab goto={(tab) => (active = tab as TabId)} />
    {:else if active === "appearance"}
      <AppearanceTab />
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
