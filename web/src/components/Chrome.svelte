<script lang="ts">
  /**
   * In-web chrome: search box + history + dictionary-group switcher + settings.
   *
   * Search runs through the same Python path as the Qt toolbar field
   * (`searchTerm:` -> `initSearch`), so the two input surfaces stay in sync.
   * Search history (`_searchHistory.json`) and the group list are fetched on
   * demand over the bridge and pushed back in via the `setSearchHistory` /
   * `setGroups` window callbacks that Python evals.
   */
  import { onMount } from "svelte";
  import { CMD, pycmd } from "../lib/pycmd";
  import { ui } from "../lib/tabs.svelte";
  import type { HistoryEntry } from "../lib/types";

  let query = $state("");
  let groups = $state<string[]>([]);
  let group = $state("");
  let open = $state(false);
  let sel = $state(-1);
  let input: HTMLInputElement | undefined = $state();
  // U2: where the last search came from + clipboard-monitor pause state.
  let source = $state("manual");
  let clipboardPaused = $state(false);

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

  function requestHistory(): void {
    pycmd(CMD.getSearchHistory());
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

  onMount(() => {
    const w = window as unknown as Record<string, unknown>;
    // setSearchHistory now lives in bridge.ts (shared store) — the sidebar
    // "Recent searches" section reads the same list as this dropdown.
    w.setGroups = (payload: unknown) => {
      const data = (payload ?? {}) as { groups?: unknown[]; current?: string };
      groups = Array.isArray(data.groups)
        ? data.groups.filter((g): g is string => typeof g === "string")
        : [];
      if (typeof data.current === "string" && data.current) group = data.current;
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
    requestGroups();
    requestSearchStatus();
    document.addEventListener("keydown", onGlobalKey);
    return () => {
      delete (w as Record<string, unknown>).setSearchHistory;
      delete (w as Record<string, unknown>).setGroups;
      delete (w as Record<string, unknown>).setSearchSource;
      delete (w as Record<string, unknown>).setSearchStatus;
      document.removeEventListener("keydown", onGlobalKey);
    };
  });

  function requestGroups(): void {
    pycmd(CMD.getGroups());
  }

  function requestSearchStatus(): void {
    pycmd(CMD.requestSearchStatus());
  }

  /** Toggle clipboard-monitor snooping (one-click pause/resume pill). */
  function toggleClipboardPause(): void {
    const next = !clipboardPaused;
    clipboardPaused = next;
    pycmd(CMD.setClipboardPaused(next));
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

  <select
    aria-label="Dictionary group"
    bind:value={group}
    onchange={() => {
      if (group) pycmd(CMD.setGroup(group));
    }}
  >
    {#each groups as g (g)}
      <option value={g}>{g}</option>
    {/each}
  </select>

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