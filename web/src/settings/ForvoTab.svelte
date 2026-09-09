<script lang="ts">
  import { settings } from "../lib/settings.svelte";
  import type { ForvoLanguage } from "../lib/settings.svelte";

  const cfg = {
    get: (k: string, d: unknown) => settings.dirty[k] ?? d,
    set: (k: string, v: unknown) => {
      settings.dirty[k] = v;
      settings.dirty = settings.dirty;
    },
  };

  // Fallback used before the bridge delivers the full 431-language catalogue
  // (or if it fails to load) — mirrors the common cases from FORVO_LANGUAGES.
  const FALLBACK_LANGUAGES: ForvoLanguage[] = [
    { code: "ja", name: "Japanese" },
    { code: "en", name: "English" },
    { code: "zh", name: "Chinese" },
    { code: "ko", name: "Korean" },
    { code: "fr", name: "French" },
    { code: "de", name: "German" },
    { code: "es", name: "Spanish" },
    { code: "it", name: "Italian" },
    { code: "ru", name: "Russian" },
    { code: "pt", name: "Portuguese" },
    { code: "nl", name: "Dutch" },
    { code: "sv", name: "Swedish" },
    { code: "ar", name: "Arabic" },
  ];

  let current = $state(String(cfg.get("forvo_language", "ja")));

  // Full catalogue from Python, or the fallback list while loading.
  const catalogue = $derived(
    settings.forvoLanguages.length > 0 ? settings.forvoLanguages : FALLBACK_LANGUAGES,
  );

  // The dropdown must never render blank: if the stored language isn't in the
  // catalogue (e.g. chosen years ago via the old editable combo), expose it as
  // an extra option so the current value stays visible and editable.
  const options = $derived(
    catalogue.some((l) => l.code === current)
      ? catalogue
      : [...catalogue, { code: current, name: current }],
  );
</script>

<div class="card">
  <h3>Forvo Configuration</h3>
  <p class="hint">Enable Forvo to fetch native pronunciations for your search terms.</p>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("forvo_enabled", true)} onchange={(e) => cfg.set("forvo_enabled", e.currentTarget.checked)} />
    Enable Forvo Dictionary
  </label>
  <div class="field">
    <label for="forvoLang">Forvo Language</label>
    <select
      id="forvoLang"
      value={current}
      onchange={(e) => {
        current = e.currentTarget.value;
        cfg.set("forvo_language", current);
      }}
    >
      {#each options as lang (lang.code)}
        <option value={lang.code}>{lang.name}</option>
      {/each}
    </select>
  </div>
  <p class="hint">Select the language for Forvo pronunciation searches.</p>
</div>