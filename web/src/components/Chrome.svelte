<script lang="ts">
  /**
   * Unified in-web header: the single chrome for the dictionary.
   *
   * The old Qt toolbar was removed (it duplicated this strip and never
   * showed up in the standalone web preview), so every capability lives
   * here: search + history, dictionary-group + search-mode selects, sidebar
   * toggle, font sizing, single/multi-tab, history viewer, deinflection,
   * theme editor, clipboard pause + search-source chip, settings.
   *
   * Search runs through the same Python path as before
   * (`searchTerm:` -> `initSearch`). All other controls go through the
   * matching `CMD.*` bridge calls; Python pushes the combined state back
   * via the `setHeaderState` window callback that `pushHeaderState` evals
   * (legacy `setGroups` / `setSearchStatus` / `setSearchModes` still work).
   */
  import { onMount } from "svelte";
  import { CMD, pycmd } from "../lib/pycmd";
  import { scaleFont, toggleSidebar, ui } from "../lib/tabs.svelte";
  import type { HistoryEntry } from "../lib/types";

  const FALLBACK_GROUPS = ["All", "Images"];
  const FALLBACK_MODES = [
    "Forward",
    "Backward",
    "Exact",
    "Anywhere",
    "Definition",
    "Example",
    "Pronunciation",
  ];

  let query = $state("");
  let groups = $state<string[]>([...FALLBACK_GROUPS]);
  let group = $state("All");
  let modes = $state<string[]>([...FALLBACK_MODES]);
  let mode = $state("Forward");
  let deinflect = $state(false);
  let singleTab = $state(true);
  let open = $state(false);
  let sel = $state(-1);
  let input: HTMLInputElement | undefined = $state();
  // U2: where the last search came from + clipboard-monitor pause state.
  let source = $state("manual");
  let clipboardPaused = $state(false);
  // Editor target (showTarget): e.g. "Reviewer" or a field name.
  let target = $state("");
  let showTarget = $state(false);

  const sourceLabel = $derived.by(() => {
    switch (source) {
      case "clipboard":
        return "From clipboard";
      case "browser":
        return "From browser";
      case "extension":
        return "From extension";
      default:
        return "Manual";
    }
  });

  const filtered = $derived(
    query.trim()
      ? ui.history.filter((h) =>
          h.term.toLowerCase().includes(query.trim().toLowerCase()),
        )
      : ui.history,
  );

  function today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function hasBridge(): boolean {
    return typeof window.pycmd === "function";
  }

  function requestHistory(): void {
    pycmd(CMD.getSearchHistory());
  }

  function requestHeaderState(): void {
    pycmd(CMD.getHeaderState());
  }

  function submit(value?: string): void {
    const q = (value ?? query).trim();
    if (!q) return;
    pycmd(CMD.searchTerm(q));
    // Optimistically prepend the search (Python persists the real one); the
    // shared store keeps the chrome dropdown + sidebar list in sync.
    ui.history = [
      { term: q, date: today() },
      ...ui.history.filter((h) => h.term !== q),
    ].slice(0, 50);
    open = false;
    sel = -1;
  }

  function pick(h: HistoryEntry): void {
    query = h.term;
    submit(h.term);
  }

  function onKeydown(e: KeyboardEvent): void {
    if (e.key === "Enter") {
      e.preventDefault();
      if (open && sel >= 0 && filtered[sel]) pick(filtered[sel]);
      else submit();
    } else if (e.key === "Escape") {
      open = false;
      sel = -1;
      input?.blur();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!open) {
        requestHistory();
        open = true;
        return;
      }
      e.preventDefault();
      const n = filtered.length;
      if (n === 0) return;
      sel = (sel + (e.key === "ArrowDown" ? 1 : n - 1)) % n;
    }
  }

  /** Ctrl/Cmd+K focuses the search box from anywhere in the shell. */
  function onGlobalKey(e: KeyboardEvent): void {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      requestHistory();
      input?.focus();
      input?.select();
    }
  }

  type HeaderState = {
    groups?: unknown;
    current?: unknown;
    searchModes?: unknown;
    searchMode?: unknown;
    deinflect?: unknown;
    singleTab?: unknown;
    source?: unknown;
    clipboardPaused?: unknown;
    target?: unknown;
    showTarget?: unknown;
  };

  function applyHeaderState(data: HeaderState): void {
    if (Array.isArray(data.groups)) {
      const gs = data.groups.filter((g): g is string => typeof g === "string");
      if (gs.length > 0) groups = gs;
    }
    if (typeof data.current === "string" && data.current) group = data.current;
    if (Array.isArray(data.searchModes)) {
      const ms = data.searchModes.filter(
        (m): m is string => typeof m === "string",
      );
      if (ms.length > 0) modes = ms;
    }
    if (typeof data.searchMode === "string" && data.searchMode)
      mode = data.searchMode;
    if (typeof data.deinflect === "boolean") deinflect = data.deinflect;
    if (typeof data.singleTab === "boolean") singleTab = data.singleTab;
    if (typeof data.source === "string") source = data.source;
    if (typeof data.clipboardPaused === "boolean")
      clipboardPaused = data.clipboardPaused;
    if (typeof data.target === "string") target = data.target;
    if (typeof data.showTarget === "boolean") showTarget = data.showTarget;
  }

  onMount(() => {
    const w = window as unknown as Record<string, unknown>;
    // setSearchHistory lives in bridge.ts (shared store) — the sidebar
    // "Recent searches" section reads the same list as this dropdown.
    w.setGroups = (payload: unknown) => {
      const data = (payload ?? {}) as { groups?: unknown[]; current?: string };
      if (Array.isArray(data.groups)) {
        const gs = data.groups.filter((g): g is string => typeof g === "string");
        if (gs.length > 0) groups = gs;
      }
      if (typeof data.current === "string" && data.current) group = data.current;
    };
    w.setSearchModes = (payload: unknown) => {
      const data = (payload ?? {}) as { modes?: unknown[]; current?: string };
      if (Array.isArray(data.modes)) {
        const ms = data.modes.filter((m): m is string => typeof m === "string");
        if (ms.length > 0) modes = ms;
      }
      if (typeof data.current === "string" && data.current) mode = data.current;
    };
    w.setHeaderState = (payload: unknown) => {
      applyHeaderState((payload ?? {}) as HeaderState);
    };
    w.setSearchSource = (payload: unknown) => {
      // Pushed on every search (initSearch) so the pill tracks the latest
      // trigger (clipboard/browser/extension/manual) live.
      if (typeof payload === "string") source = payload;
    };
    w.setSearchStatus = (payload: unknown) => {
      const data = (payload ?? {}) as {
        source?: unknown;
        clipboardPaused?: unknown;
      };
      if (typeof data.source === "string") source = data.source;
      if (typeof data.clipboardPaused === "boolean") {
        clipboardPaused = data.clipboardPaused;
      }
    };
    requestHeaderState();
    requestHistory();
    document.addEventListener("keydown", onGlobalKey);
    return () => {
      delete w.setGroups;
      delete w.setSearchModes;
      delete w.setHeaderState;
      delete w.setSearchSource;
      delete w.setSearchStatus;
      document.removeEventListener("keydown", onGlobalKey);
    };
  });

  /** Toggle clipboard-monitor snooping (one-click pause/resume pill). */
  function toggleClipboardPause(): void {
    const next = !clipboardPaused;
    clipboardPaused = next;
    pycmd(CMD.setClipboardPaused(next));
  }

  function toggleDeinflect(): void {
    const next = !deinflect;
    deinflect = next;
    pycmd(CMD.setDeinflect(next));
  }

  function toggleTabMode(): void {
    const next = !singleTab;
    singleTab = next;
    pycmd(CMD.setTabMode(next));
  }

  function openHistoryViewer(): void {
    if (hasBridge()) {
      pycmd(CMD.openHistory());
    } else {
      // Standalone web preview: no Qt dialog — show the inline history.
      requestHistory();
      open = true;
      input?.focus();
    }
  }

  function onFocus(): void {
    requestHistory();
    open = true;
    sel = -1;
  }

  function onFocusOut(): void {
    // Delay so the mouse-down on a history item fires before the popup hides.
    setTimeout(() => {
      open = false;
      sel = -1;
    }, 150);
  }
</script>

<div id="chromeBar">
  <div class="chromeSearch">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </svg>
    <input
      bind:this={input}
      bind:value={query}
      type="text"
      placeholder="Search the dictionary (Ctrl+K)"
      aria-label="Search the dictionary"
      autocomplete="off"
      spellcheck="false"
      onfocus={onFocus}
      onfocusout={onFocusOut}
      oninput={() => {
        open = true;
        sel = -1;
      }}
      onkeydown={onKeydown}
    />
    {#if open && filtered.length > 0}
      <ul class="chromeHist" role="listbox" aria-label="Search history">
        {#each filtered as h, i (h.term + i)}
          <li
            role="option"
            aria-selected={i === sel}
            class:sel={i === sel}
            onmouseenter={() => (sel = i)}
            onmousedown={(e) => {
              e.preventDefault();
              pick(h);
            }}
          >
            <span>{h.term}</span>
            <small>{h.date}</small>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <button
    class="chromeBtn"
    type="button"
    title="Search"
    aria-label="Search"
    onclick={() => submit()}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  </button>

  <select
    class="chromeSelect"
    aria-label="Dictionary group"
    title="Dictionary group"
    bind:value={group}
    onchange={() => {
      if (group) pycmd(CMD.setGroup(group));
    }}
  >
    {#each groups as g (g)}
      <option value={g}>{g}</option>
    {/each}
  </select>

  <select
    class="chromeSelect chromeMode"
    aria-label="Search mode"
    title="Search mode: how the term is matched"
    bind:value={mode}
    onchange={() => {
      if (mode) pycmd(CMD.setSearchMode(mode));
    }}
  >
    {#each modes as m (m)}
      <option value={m}>{m}</option>
    {/each}
  </select>

  <button
    class="chromeBtn"
    class:active={ui.sidebarOpened}
    type="button"
    title={ui.sidebarOpened ? "Close definition sidebar" : "Open definition sidebar"}
    aria-label={ui.sidebarOpened ? "Close definition sidebar" : "Open definition sidebar"}
    aria-pressed={ui.sidebarOpened}
    onclick={() => toggleSidebar()}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
    </svg>
  </button>

  <span class="chromeDiv" aria-hidden="true"></span>

  <button
    class="chromeBtn"
    type="button"
    title="Decrease font size"
    aria-label="Decrease font size"
    onclick={() => scaleFont(false)}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M5 12h14" />
    </svg>
  </button>
  <button
    class="chromeBtn"
    type="button"
    title="Increase font size"
    aria-label="Increase font size"
    onclick={() => scaleFont(true)}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
    </svg>
  </button>

  <button
    class="chromeBtn"
    class:active={!singleTab}
    type="button"
    title={singleTab ? "Single-tab mode — click for multi-tab" : "Multi-tab mode — click for single-tab"}
    aria-label={singleTab ? "Switch to multi-tab mode" : "Switch to single-tab mode"}
    aria-pressed={!singleTab}
    onclick={toggleTabMode}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      {#if singleTab}
        <rect x="4" y="4" width="16" height="16" rx="2" />
      {:else}
        <rect x="7" y="7" width="13" height="13" rx="2" />
        <path d="M4 16V6a2 2 0 0 1 2-2h10" />
      {/if}
    </svg>
  </button>

  <button
    class="chromeBtn"
    type="button"
    title="Open search history"
    aria-label="Open search history"
    onclick={openHistoryViewer}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 4v5h5" />
      <path d="M12 7v5l3 2" />
    </svg>
  </button>

  <button
    class="chromeBtn"
    class:active={deinflect}
    type="button"
    title={deinflect ? "Deinflection on — click to turn off" : "Deinflection off — click to turn on"}
    aria-label={deinflect ? "Turn deinflection off" : "Turn deinflection on"}
    aria-pressed={deinflect}
    onclick={toggleDeinflect}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" />
      <path d="M12 22V12" />
      <path d="m3 7 9 5 9-5" />
    </svg>
  </button>

  <button
    class="chromeBtn"
    type="button"
    title="Theme editor"
    aria-label="Theme editor"
    onclick={() => pycmd(CMD.openTheme())}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3a9 9 0 0 0 0 18c1.5 0 2-1 1.5-2-.5-1.2.2-2.5 1.5-2.5H17a4 4 0 0 0 4-4c0-5-4-9.5-9-9.5Z" />
      <circle cx="8.5" cy="10.5" r="1" fill="currentColor" />
      <circle cx="12" cy="7.5" r="1" fill="currentColor" />
      <circle cx="15.5" cy="10.5" r="1" fill="currentColor" />
    </svg>
  </button>

  <!-- U2: search-source chip + clipboard-monitor pause pill. -->
  <div class="sourcePill" class:clipboard={source === "clipboard"} title={source === "clipboard" ? "Searched from the global clipboard hotkey" : "Search source"}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      {#if source === "clipboard"}
        <rect x="8" y="2" width="8" height="4" rx="1" />
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <path d="M9 12h6M9 16h4" />
      {:else}
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
      {/if}
    </svg>
    <span>{sourceLabel}</span>
  </div>
  <button
    class="chromeBtn pauseBtn"
    class:paused={clipboardPaused}
    type="button"
    title={clipboardPaused ? "Clipboard monitoring paused — click to resume" : "Clipboard monitoring active — click to pause"}
    aria-label={clipboardPaused ? "Resume clipboard monitoring" : "Pause clipboard monitoring"}
    aria-pressed={clipboardPaused}
    onclick={toggleClipboardPause}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      {#if clipboardPaused}
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
      {:else}
        <path d="M7 6v12M11 6v12M15 6v12" />
      {/if}
    </svg>
  </button>

  {#if showTarget && target}
    <div class="sourcePill targetPill" title="Anki editor target">
      <span>Target: {target}</span>
    </div>
  {/if}

  <button
    class="chromeBtn"
    type="button"
    title="Dictionary settings"
    aria-label="Dictionary settings"
    onclick={() => pycmd(CMD.openSettings())}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
    </svg>
  </button>
</div>
