<script lang="ts">
  import { onMount } from "svelte";
  import {
    DEFAULT_DICTIONARY_SERVER,
    fetchWebIndex,
    removeLanguage,
    settings,
    startWebInstall,
  } from "../lib/settings.svelte";
  import { pycmd } from "../lib/pycmd";
  import WebInstallModal from "./modals/WebInstallModal.svelte";

  let installModal = $state<"dictionaries" | "frequency" | null>(null);

  interface TranslationOption {
    name_en?: string;
    code?: string;
    dictionaries?: { name: string; url: string }[];
  }

  let targetCode = $state("");
  let translationCode = $state("");
  let quickStarted = $state(false);

  const targets = $derived(
    (settings.webIndex?.ok ? (settings.webIndex?.index?.languages ?? []) : [])
      .filter((l) => (l.name_en ?? "") !== ""),
  );
  const target = $derived(
    targets.find((l) => l.code === targetCode) ?? targets[0] ?? null,
  );
  const translationOptions = $derived.by((): TranslationOption[] => {
    if (!target) return [];
    const pairs = (target.to_languages ?? []).filter(
      (t) => (t.dictionaries ?? []).length > 0,
    );
    if (pairs.length > 0) return pairs;
    return [
      {
        name_en: target.name_en,
        code: target.code,
        dictionaries: target.dictionaries ?? [],
      },
    ];
  });
  const translation = $derived(
    translationOptions.find((t) => t.code === translationCode) ??
      translationOptions[0] ??
      null,
  );

  /** Forvo uses short codes; the index uses e.g. zh_CN / zh_TW. */
  function forvoCode(code: string | undefined): string {
    const lower = (code ?? "").toLowerCase();
    if (lower.startsWith("zh") || lower === "yue") return "zh";
    return lower.split("_")[0];
  }

  /** Prefer the canonical learner dictionary for the pair. */
  function recommended(
    dicts: { name: string; url: string }[] | undefined,
  ): { name: string; url: string } | null {
    const list = dicts ?? [];
    const preferred = list.find((d) =>
      /jmdict|cedict|wiktionary|wordset/i.test(d.name),
    );
    return preferred ?? list[0] ?? null;
  }

  $effect(() => {
    if (!targetCode && targets.length > 0) {
      const preferred = targets.find((l) => l.name_en === "Japanese");
      targetCode = preferred?.code ?? targets[0].code ?? "";
    }
  });

  $effect(() => {
    if (translationOptions.length === 0) return;
    if (!translationOptions.some((t) => t.code === translationCode)) {
      const english = translationOptions.find((t) => t.code === "en");
      translationCode = english?.code ?? translationOptions[0].code ?? "";
    }
  });

  function quickInstall(): void {
    if (!target || !translation) return;
    const dict = recommended(translation.dictionaries);
    startWebInstall({
      server: DEFAULT_DICTIONARY_SERVER,
      install_dictionaries: true,
      install_word_lists: true,
      install_conjugation: Boolean(target.conjugation_url),
      languages: [
        {
          name: target.name_en,
          dictionaries: dict ? [{ name: dict.name, url: dict.url }] : [],
          frequency_lists: target.frequency_lists ?? [],
          word_lists: target.word_lists ?? [],
          conjugation_url: target.conjugation_url ?? "",
        },
      ],
      apply_setup: {
        language: target.name_en,
        forvo_language: forvoCode(target.code),
        deinflect: Boolean(target.conjugation_url),
      },
    });
    quickStarted = true;
  }

  onMount(() => {
    if (!settings.webIndex) fetchWebIndex(DEFAULT_DICTIONARY_SERVER);
  });

  function importFromFiles(): void {
    pycmd("settings:importDicts");
  }
  function importFreqFromFiles(): void {
    pycmd("settings:importFreq");
  }
</script>

<div class="card">
  <h3>Quick Setup</h3>
  <p class="hint">
    Pick your target language and the language you want definitions in. The
    addon installs one recommended dictionary plus frequency, level and
    conjugation data, then configures Forvo and auto-grouping.
  </p>
  {#if !settings.webIndex}
    <p class="hint">Loading the dictionary index…</p>
  {:else if !settings.webIndex.ok}
    <p class="hint">
      Could not reach the dictionary server. Check your connection and try again.
    </p>
    <button
      type="button"
      class="btn"
      onclick={() => fetchWebIndex(DEFAULT_DICTIONARY_SERVER)}
    >
      Retry
    </button>
  {:else if targets.length === 0}
    <p class="hint">The server index contains no languages.</p>
  {:else}
    <div class="field">
      <label for="quickTarget">Target language</label>
      <select
        id="quickTarget"
        value={targetCode}
        disabled={settings.webInstall.running}
        onchange={(e) => (targetCode = e.currentTarget.value)}
      >
        {#each targets as l (l.code ?? l.name_en)}
          <option value={l.code ?? ""}>{l.name_en}{l.name_native ? ` (${l.name_native})` : ""}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <label for="quickTranslation">Definitions in</label>
      <select
        id="quickTranslation"
        value={translation?.code ?? ""}
        disabled={settings.webInstall.running}
        onchange={(e) => (translationCode = e.currentTarget.value)}
      >
        {#each translationOptions as t (t.code ?? t.name_en)}
          <option value={t.code ?? ""}>{t.name_en ?? t.code}</option>
        {/each}
      </select>
    </div>
    {#if translation}
      {@const dict = recommended(translation.dictionaries)}
      <p class="hint">
        Installs <strong>{dict?.name ?? "no dictionary"}</strong>
        {#if target && (target.frequency_lists ?? []).length > 0}
          · {(target.frequency_lists ?? []).length} frequency list(s)
        {/if}
        {#if target && (target.word_lists ?? []).length > 0}
          · {(target.word_lists ?? []).length} level list(s)
        {/if}
        {#if target?.conjugation_url}· conjugation data{/if}
      </p>
    {/if}
    <button
      type="button"
      class="btn primary"
      disabled={settings.webInstall.running || !translation}
      onclick={quickInstall}
    >
      {settings.webInstall.running ? "Installing…" : "Install recommended pack"}
    </button>
    {#if quickStarted || settings.webInstall.running}
      <div class="install-progress" style="margin-top:10px">
        <div
          class="bar"
          style:width={`${settings.webInstall.percent ?? 0}%`}
        ></div>
      </div>
      <p class="hint">
        {#if settings.webInstall.running}
          {settings.webInstall.percent ?? 0}% — downloading and importing…
        {:else if settings.webInstall.completed}
          Installed. Reopen the dictionary to search.
        {:else if (settings.webInstall.failed ?? 0) > 0}
          Finished with {settings.webInstall.failed} error(s). See the log below.
        {:else}
          Finished.
        {/if}
      </p>
      {#if settings.webInstall.log && settings.webInstall.log.length > 0}
        <pre class="install-log">{settings.webInstall.log.slice(-12).join("\n")}</pre>
      {/if}
    {/if}
  {/if}
</div>

<div class="card">
  <h3>Language Options</h3>
  <p class="hint">
    Manage the languages and dictionaries the addon loads. Installing
    dictionaries from files opens the addon's native import flow.
  </p>
  <div class="install-grid">
    <button type="button" class="btn primary" onclick={() => (installModal = "dictionaries")}>Install Dictionaries (Web)</button>
    <button type="button" class="btn" onclick={importFromFiles}>Install Dictionaries (Files)</button>
    <button type="button" class="btn" onclick={() => (installModal = "frequency")}>Install Frequency Data (Web)</button>
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

{#if installModal}
  <WebInstallModal mode={installModal} onclose={() => (installModal = null)} />
{/if}
