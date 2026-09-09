<script lang="ts">
  /**
   * Web-install modal for dictionaries and frequency lists.
   *
   * Replaces the old Qt wizard (`DictionaryWebInstallWizard`) and the
   * frequency list dialog (`FreqConjWebWindow`): fetches the dictionary
   * server's index, lets the user pick languages/dictionaries (or frequency
   * lists), then streams the install job's progress log.
   */
  import {
    cancelWebInstall,
    fetchWebIndex,
    settings,
    startWebInstall,
  } from "../../lib/settings.svelte";
  import type { WebIndexLanguage } from "../../lib/settings.svelte";
  import { onMount } from "svelte";

  interface Props {
    mode: "dictionaries" | "frequency";
    onclose: () => void;
  }
  let { mode, onclose }: Props = $props();

  /** Default server — mirrors `web/config.py`'s DEFAULT_SERVER. */
  const DEFAULT_SERVER = "https://github.com/Alexander-Nilsson/dictionaries/raw/main";

  let server = $state(DEFAULT_SERVER);
  let fetched = $state(false); // a fetch has been attempted
  let selectedLangs = $state<Record<string, boolean>>({});
  // Dict selections keyed by `${langIndex}:${toIndex}:${dictIdx}`.
  let selectedDicts = $state<Record<string, boolean>>({});
  // Frequency-list selections keyed by `${langIndex}:${listIdx}`.
  let selectedLists = $state<Record<string, boolean>>({});
  let installWordLists = $state(true);
  let installConjugation = $state(true);
  let launched = $state(false);

  const index = $derived(settings.webIndex?.ok ? (settings.webIndex?.index?.languages ?? []) : []);
  const installing = $derived(settings.webInstall.running);
  const finished = $derived(
    launched && !settings.webInstall.running && settings.webInstall.completed === true,
  );

  function connect(): void {
    fetched = true;
    fetchWebIndex(server.trim() || DEFAULT_SERVER);
  }

  // Load the default server's index as soon as the modal opens, so the
  // dictionary list appears without requiring a manual "Connect" click.
  // "Connect" remains for pointing at a different server.
  onMount(() => {
    connect();
  });

  function langLabel(l: WebIndexLanguage): string {
    let label = l.name_en ?? "?";
    if (l.name_native) label += ` (${l.name_native})`;
    return label;
  }

  function flatDicts(l: WebIndexLanguage): { name: string; url: string }[] {
    const out: { name: string; url: string }[] = [];
    for (const tl of l.to_languages ?? []) {
      for (const d of tl.dictionaries ?? []) out.push(d);
    }
    for (const d of l.dictionaries ?? []) out.push(d);
    return out;
  }

  function langHasDicts(l: WebIndexLanguage): boolean {
    return flatDicts(l).length > 0;
  }

  function toggleLang(i: number, l: WebIndexLanguage, checked: boolean): void {
    selectedLangs = { ...selectedLangs, [i]: checked };
    const next = { ...selectedDicts };
    flatDicts(l).forEach((_, di) => {
      next[`${i}:${di}`] = checked;
    });
    selectedDicts = next;
  }

  function toggleDict(i: number, di: number, checked: boolean): void {
    selectedDicts = { ...selectedDicts, [`${i}:${di}`]: checked };
  }

  function toggleList(i: number, li: number, checked: boolean): void {
    selectedLists = { ...selectedLists, [`${i}:${li}`]: checked };
  }

  function langChecked(i: number, l: WebIndexLanguage): boolean {
    const dicts = flatDicts(l);
    return dicts.length > 0 && dicts.every((_, di) => selectedDicts[`${i}:${di}`]);
  }

  function anyDictSelected(): boolean {
    return Object.values(selectedDicts).some(Boolean);
  }

  function anyListSelected(): boolean {
    return Object.values(selectedLists).some(Boolean);
  }

  function install(): void {
    const languages: Record<string, unknown>[] = [];
    if (mode === "dictionaries") {
      index.forEach((l, i) => {
        const dicts = flatDicts(l)
          .filter((_, di) => selectedDicts[`${i}:${di}`])
          .map((d) => ({ name: d.name, url: d.url }));
        if (!dicts.length) return;
        languages.push({
          name: l.name_en,
          dictionaries: dicts,
          // Word lists / conjugation ride along for every selected language.
          frequency_lists: installWordLists ? (l.frequency_lists ?? []) : [],
          word_lists: installWordLists ? (l.word_lists ?? []) : [],
          conjugation_url: installConjugation ? (l.conjugation_url ?? "") : "",
        });
      });
      startWebInstall({
        server: server.trim() || DEFAULT_SERVER,
        install_dictionaries: true,
        install_word_lists: installWordLists,
        install_conjugation: installConjugation,
        languages,
      });
    } else {
      index.forEach((l, i) => {
        const lists = (l.frequency_lists ?? [])
          .filter((_, li) => selectedLists[`${i}:${li}`])
          .map((f) => ({ name: f.name, url: f.url }));
        if (!lists.length) return;
        languages.push({ name: l.name_en, frequency_lists: lists });
      });
      startWebInstall({
        server: server.trim() || DEFAULT_SERVER,
        install_dictionaries: false,
        install_word_lists: true,
        install_conjugation: false,
        languages,
      });
    }
    launched = true;
  }

  function close(): void {
    if (settings.webInstall.running) cancelWebInstall();
    onclose();
  }

  function onKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") close();
  }
</script>

<div
  class="modal-backdrop"
  role="presentation"
  onclick={(e) => {
    if (e.target === e.currentTarget) close();
  }}
  onkeydown={onKeydown}
>
  <div class="modal install-modal" role="dialog" aria-modal="true" tabindex="-1">
    <div class="modal-header">
      <h3>
        {mode === "dictionaries" ? "Install Dictionaries from Web" : "Install Frequency Data from Web"}
      </h3>
      <button type="button" class="btn" onclick={close}>✕</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label for="webServer">Dictionary Server</label>
        <div style="flex:1;display:flex;gap:8px">
          <input
            id="webServer"
            type="text"
            value={server}
            disabled={installing}
            oninput={(e) => (server = e.currentTarget.value)}
            onkeydown={(e) => {
              if (e.key === "Enter") connect();
            }}
          />
          <button type="button" class="btn" disabled={installing} onclick={connect}>
            Connect
          </button>
        </div>
      </div>

      {#if fetched && !settings.webIndex}
        <p class="hint">Fetching index…</p>
      {:else if fetched && settings.webIndex && !settings.webIndex.ok}
        <p class="hint">
          The server "{settings.webIndex.server}" is not reachable. Make sure you are
          connected to the internet and the url you entered is valid.
        </p>
      {:else if index.length === 0}
        <p class="hint">The server's index contains no languages.</p>
      {:else if mode === "dictionaries"}
        <label class="check"><input type="checkbox" bind:checked={installWordLists} disabled={installing} /> Install Word List Data (Frequency, HSK, JLPT…)</label>
        <label class="check"><input type="checkbox" bind:checked={installConjugation} disabled={installing} /> Install Conjugation Data</label>
        <div class="install-lang-list">
          {#each index as l, i (l.name_en ?? i)}
            {#if langHasDicts(l)}
              <div class="install-lang">
                <label class="check">
                  <input
                    type="checkbox"
                    checked={langChecked(i, l)}
                    disabled={installing}
                    onchange={(e) => toggleLang(i, l, e.currentTarget.checked)}
                  />
                  <strong>{langLabel(l)}</strong>
                  <span class="sub">{flatDicts(l).length} dictionaries</span>
                </label>
                <div class="install-dicts">
                  {#each flatDicts(l) as d, di (`${i}:${di}`)}
                    <label class="check">
                      <input
                        type="checkbox"
                        checked={!!selectedDicts[`${i}:${di}`]}
                        disabled={installing}
                        onchange={(e) => toggleDict(i, di, e.currentTarget.checked)}
                      />
                      {d.name}
                    </label>
                  {/each}
                </div>
              </div>
            {/if}
          {/each}
        </div>
      {:else}
        <div class="install-lang-list">
          {#each index as l, i (l.name_en ?? i)}
            {#if (l.frequency_lists ?? []).length > 0}
              <div class="install-lang">
                <strong>{langLabel(l)}</strong>
                <div class="install-dicts">
                  {#each l.frequency_lists ?? [] as f, li (`${i}:${li}`)}
                    <label class="check">
                      <input
                        type="checkbox"
                        checked={!!selectedLists[`${i}:${li}`]}
                        disabled={installing}
                        onchange={(e) => toggleList(i, li, e.currentTarget.checked)}
                      />
                      {f.name}
                    </label>
                  {/each}
                </div>
              </div>
            {/if}
          {/each}
        </div>
      {/if}

      {#if launched}
        <div class="install-progress">
          <div class="install-progress-bar" role="progressbar" aria-valuenow={settings.webInstall.percent} aria-valuemin="0" aria-valuemax="100">
            <div style="width:{Math.max(2, settings.webInstall.percent)}%"></div>
          </div>
          <pre class="install-log">{settings.webInstall.log?.join("\n")}</pre>
        </div>
      {/if}
    </div>
    <div class="modal-footer">
      {#if launched && installing}
        <button type="button" class="btn danger" onclick={() => cancelWebInstall()}>Cancel Install</button>
      {:else if launched && finished}
        <button type="button" class="btn primary" onclick={close}>Done</button>
      {:else}
        <button type="button" class="btn" onclick={close}>Cancel</button>
        {#if mode === "dictionaries"}
          <button
            type="button"
            class="btn primary"
            disabled={!settings.webIndex?.ok || installing || !anyDictSelected()}
            onclick={install}
          >Install</button>
        {:else}
          <button
            type="button"
            class="btn primary"
            disabled={!settings.webIndex?.ok || installing || !anyListSelected()}
            onclick={install}
          >Install</button>
        {/if}
      {/if}
    </div>
  </div>
</div>
