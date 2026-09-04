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

  interface HistoryItem {
    term: string;
    date: string;
  }

  let query = $state("");
  let history = $state<HistoryItem[]>([]);
  let groups = $state<string[]>([]);
  let group = $state("");
  let open = $state(false);
  let sel = $state(-1);
  let input: HTMLInputElement | undefined = $state();

  const filtered = $derived(
    query.trim()
      ? history.filter((h) =>
          h.term.toLowerCase().includes(query.trim().toLowerCase()),
        )
      : history,
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
    // Optimistically prepend the search locally (Python persists the real one).
    history = [{ term: q, date: today() }, ...history.filter((h) => h.term !== q)].slice(0, 50);
    open = false;
    sel = -1;
  }

  function pick(h: HistoryItem): void {
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
    w.setSearchHistory = (payload: unknown) => {
      // Python ships history as [[term, date], …] (the model rows persisted to
      // _searchHistory.json). Tolerate {term, date} objects too.
      const list = Array.isArray(payload) ? (payload as unknown[]) : [];
      history = list
        .map((h): HistoryItem | null => {
          if (Array.isArray(h) && typeof h[0] === "string") {
            return { term: h[0], date: typeof h[1] === "string" ? h[1] : "" };
          }
          if (h && typeof (h as HistoryItem).term === "string") {
            return {
              term: (h as HistoryItem).term,
              date: (h as HistoryItem).date ?? "",
            };
          }
          return null;
        })
        .filter((h): h is HistoryItem => h !== null)
        .slice(0, 50);
    };
    w.setGroups = (payload: unknown) => {
      const data = (payload ?? {}) as { groups?: unknown[]; current?: string };
      groups = Array.isArray(data.groups)
        ? data.groups.filter((g): g is string => typeof g === "string")
        : [];
      if (typeof data.current === "string" && data.current) group = data.current;
    };
    requestGroups();
    document.addEventListener("keydown", onGlobalKey);
    return () => {
      delete (w as Record<string, unknown>).setSearchHistory;
      delete (w as Record<string, unknown>).setGroups;
      document.removeEventListener("keydown", onGlobalKey);
    };
  });

  function requestGroups(): void {
    pycmd(CMD.getGroups());
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