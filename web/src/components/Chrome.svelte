<script lang="ts">
  /**
   * S1 minimal header: search + scope + overflow.
   *
   * Only three units stay visible: the search box (with history), a joined
   * scope control (group + mode styled as one), and a `⋯` overflow menu
   * holding every rarer capability (sidebar, font, tabs, history,
   * deinflection, theme, clipboard pause, settings). Status pills render
   * only when interesting (clipboard source / paused / editor target) —
   * the always-on "Manual" pill is gone.
   *
   * S3 lives in `CommandPalette.svelte`: Ctrl/⌘+K opens it; `/` focuses
   * this search box. Header state itself lives in the shared `ui` store
   * (written by `bridge.ts` from `pushHeaderState`).
   */
  import { onMount } from "svelte";
  import { CMD, pycmd } from "../lib/pycmd";
  import { scaleFont, toggleSidebar, ui } from "../lib/tabs.svelte";
  import type { HistoryEntry } from "../lib/types";

  let query = $state("");
  let open = $state(false); // history dropdown
  let sel = $state(-1);
  let menuOpen = $state(false);
  let input: HTMLInputElement | undefined = $state();

  const filtered = $derived(
    query.trim()
      ? ui.history.filter((h) =>
          h.term.toLowerCase().includes(query.trim().toLowerCase()),
        )
      : ui.history,
  );

  const showClipboardPill = $derived(
    ui.searchSource === "clipboard" || ui.clipboardPaused,
  );
  const clipboardTitle = $derived(
    ui.clipboardPaused
      ? "Clipboard monitoring paused — click ⋯ to resume"
      : "Searched from the global clipboard hotkey",
  );
  const showTargetPill = $derived(ui.showTarget && ui.target !== "");

  function today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function requestHistory(): void {
    pycmd(CMD.getSearchHistory());
  }

  function requestHeaderState(): void {
    pycmd(CMD.getHeaderState());
  }

  export function focusSearch(): void {
    requestHistory();
    input?.focus();
    input?.select();
  }

  function submit(value?: string): void {
    const q = (value ?? query).trim();
    if (!q) return;
    pycmd(CMD.searchTerm(q));
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

  /** Ctrl/⌘+K opens the S3 palette; `/` focuses search. */
  function onGlobalKey(e: KeyboardEvent): void {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      ui.showPalette = true;
      return;
    }
    if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const t = e.target;
      if (t instanceof HTMLElement) {
        if (
          t.isContentEditable ||
          t instanceof HTMLInputElement ||
          t instanceof HTMLTextAreaElement ||
          t instanceof HTMLSelectElement
        ) {
          return;
        }
      }
      e.preventDefault();
      focusSearch();
    }
  }

  onMount(() => {
    requestHeaderState();
    requestHistory();
    document.addEventListener("keydown", onGlobalKey);
    const onDocClick = (): void => {
      menuOpen = false;
    };
    document.addEventListener("click", onDocClick);
    return () => {
      document.removeEventListener("keydown", onGlobalKey);
      document.removeEventListener("click", onDocClick);
    };
  });

  function onFocus(): void {
    requestHistory();
    open = true;
    sel = -1;
  }

  function onFocusOut(): void {
    setTimeout(() => {
      open = false;
      sel = -1;
    }, 150);
  }

  // ── overflow actions (same bridge calls as before, now behind ⋯) ──
  function togglePause(): void {
    pycmd(CMD.setClipboardPaused(!ui.clipboardPaused));
  }
  function toggleDeinflect(): void {
    pycmd(CMD.setDeinflect(!ui.deinflect));
  }
  function toggleTabs(): void {
    pycmd(CMD.setTabMode(!ui.singleTab));
  }
  function closeMenu(): void {
    menuOpen = false;
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
      placeholder="Search the dictionary  ( / )"
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

  <!-- Scope: group + mode joined as one visual unit -->
  <div class="scopeWrap" role="group" aria-label="Search scope">
    <select
      class="scopeGroup"
      aria-label="Dictionary group"
      title="Dictionary group"
      bind:value={ui.group}
      onchange={() => {
        if (ui.group) pycmd(CMD.setGroup(ui.group));
      }}
    >
      {#each ui.groups as g (g)}
        <option value={g}>{g}</option>
      {/each}
    </select>
    <span class="scopeDiv" aria-hidden="true"></span>
    <select
      class="scopeMode"
      aria-label="Search mode"
      title="Search mode: how the term is matched"
      bind:value={ui.searchMode}
      onchange={() => {
        if (ui.searchMode) pycmd(CMD.setSearchMode(ui.searchMode));
      }}
    >
      {#each ui.searchModes as m (m)}
        <option value={m}>{m}</option>
      {/each}
    </select>
  </div>

  {#if showClipboardPill}
    <button
      type="button"
      class="sourcePill"
      class:clipboard={ui.searchSource === "clipboard"}
      class:paused={ui.clipboardPaused}
      title={clipboardTitle}
      aria-label={ui.clipboardPaused
        ? "Resume clipboard monitoring"
        : "Clipboard search source"}
      onclick={togglePause}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <rect x="8" y="2" width="8" height="4" rx="1" />
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      </svg>
      <span>{ui.clipboardPaused ? "Paused" : "Clipboard"}</span>
    </button>
  {/if}

  {#if showTargetPill}
    <div class="sourcePill targetPill" title="Anki editor target">
      <span>Target: {ui.target}</span>
    </div>
  {/if}

  <div class="menuWrap">
    <button
      class="chromeBtn"
      type="button"
      title="More actions (⌘K for commands)"
      aria-label="More actions"
      aria-expanded={menuOpen}
      aria-haspopup="menu"
      onclick={(e) => {
        e.stopPropagation();
        menuOpen = !menuOpen;
      }}
    >
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <circle cx="5" cy="12" r="1.8" />
        <circle cx="12" cy="12" r="1.8" />
        <circle cx="19" cy="12" r="1.8" />
      </svg>
    </button>
    {#if menuOpen}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div
        class="chromeMenu"
        role="menu"
        tabindex="-1"
        onclick={(e) => e.stopPropagation()}
      >
        <div class="menuLabel">View</div>
        <button role="menuitem" type="button" onclick={() => { toggleSidebar(); closeMenu(); }}>
          <span>Toggle sidebar</span><kbd>{ui.sidebarOpened ? "on" : "off"}</kbd>
        </button>
        <button role="menuitem" type="button" onclick={() => { scaleFont(false); }}>
          <span>Font smaller</span><kbd>−</kbd>
        </button>
        <button role="menuitem" type="button" onclick={() => { scaleFont(true); }}>
          <span>Font larger</span><kbd>+</kbd>
        </button>
        <button role="menuitem" type="button" onclick={() => { toggleTabs(); closeMenu(); }}>
          <span>Tab mode</span><kbd>{ui.singleTab ? "single" : "multi"}</kbd>
        </button>
        <div class="menuSep"></div>
        <div class="menuLabel">Search</div>
        <button
          role="menuitem"
          type="button"
          onclick={() => { pycmd(CMD.openHistory()); closeMenu(); }}
        >
          <span>Search history</span>
        </button>
        <button role="menuitem" type="button" onclick={() => { toggleDeinflect(); closeMenu(); }}>
          <span>Deinflection</span><kbd>{ui.deinflect ? "on" : "off"}</kbd>
        </button>
        <button role="menuitem" type="button" onclick={() => { togglePause(); closeMenu(); }}>
          <span>Clipboard monitoring</span><kbd>{ui.clipboardPaused ? "paused" : "active"}</kbd>
        </button>
        <div class="menuSep"></div>
        <div class="menuLabel">Addon</div>
        <button
          role="menuitem"
          type="button"
          onclick={() => { pycmd(CMD.openTheme()); closeMenu(); }}
        >
          <span>Theme editor</span>
        </button>
        <button
          role="menuitem"
          type="button"
          onclick={() => { pycmd(CMD.openSettings()); closeMenu(); }}
        >
          <span>Dictionary settings</span><kbd>⌘K</kbd>
        </button>
      </div>
    {/if}
  </div>
</div>
