<script lang="ts">
  /**
   * S3 command palette (Ctrl/⌘+K).
   *
   * The header stays minimal on purpose; everything reachable there (and
   * more) is also reachable here: free-text search plus filterable commands
   * for scope, view and addon actions. Enter runs the highlighted row — or
   * searches the typed text when nothing matches.
   */
  import { CMD, pycmd } from "../lib/pycmd";
  import { scaleFont, toggleSidebar, ui } from "../lib/tabs.svelte";

  type Entry = {
    id: string;
    label: string;
    hint: string;
    run: () => void;
  };

  let input: HTMLInputElement | undefined = $state();
  let text = $state("");
  let sel = $state(0);

  function today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function search(term: string): void {
    const q = term.trim();
    if (!q) return;
    pycmd(CMD.searchTerm(q));
    ui.history = [
      { term: q, date: today() },
      ...ui.history.filter((h) => h.term !== q),
    ].slice(0, 50);
    ui.showPalette = false;
  }

  function commands(): Entry[] {
    const list: Entry[] = [
      {
        id: "sidebar",
        label: `${ui.sidebarOpened ? "Close" : "Open"} sidebar`,
        hint: "S",
        run: () => toggleSidebar(),
      },
      {
        id: "tabs",
        label: `Tab mode: ${ui.singleTab ? "single → multi" : "multi → single"}`,
        hint: "T",
        run: () => pycmd(CMD.setTabMode(!ui.singleTab)),
      },
      {
        id: "deinflect",
        label: `Deinflection ${ui.deinflect ? "off" : "on"}`,
        hint: "D",
        run: () => pycmd(CMD.setDeinflect(!ui.deinflect)),
      },
      {
        id: "pause",
        label: ui.clipboardPaused
          ? "Resume clipboard monitoring"
          : "Pause clipboard monitoring",
        hint: "P",
        run: () => pycmd(CMD.setClipboardPaused(!ui.clipboardPaused)),
      },
      {
        id: "history",
        label: "Open search history",
        hint: "H",
        run: () => pycmd(CMD.openHistory()),
      },
      {
        id: "theme",
        label: "Open theme editor",
        hint: "",
        run: () => pycmd(CMD.openTheme()),
      },
      {
        id: "settings",
        label: "Open dictionary settings",
        hint: ",",
        run: () => pycmd(CMD.openSettings()),
      },
      {
        id: "font-",
        label: "Font smaller",
        hint: "−",
        run: () => scaleFont(false),
      },
      {
        id: "font+",
        label: "Font larger",
        hint: "+",
        run: () => scaleFont(true),
      },
    ];
    for (const g of ui.groups) {
      list.push({
        id: `group:${g}`,
        label: `Group: ${g}${g === ui.group ? "  ✓" : ""}`,
        hint: "G",
        run: () => pycmd(CMD.setGroup(g)),
      });
    }
    for (const m of ui.searchModes) {
      list.push({
        id: `mode:${m}`,
        label: `Mode: ${m}${m === ui.searchMode ? "  ✓" : ""}`,
        hint: "M",
        run: () => pycmd(CMD.setSearchMode(m)),
      });
    }
    return list;
  }

  const filtered = $derived.by(() => {
    const q = text.trim().toLowerCase();
    const all = commands();
    if (!q) return all;
    return all.filter((c) => c.label.toLowerCase().includes(q));
  });

  function close(): void {
    ui.showPalette = false;
  }

  function runEntry(e: Entry): void {
    e.run();
    close();
  }

  function onKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[sel]) runEntry(filtered[sel]);
      else search(text);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      sel = filtered.length ? (sel + 1) % filtered.length : 0;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      sel = filtered.length ? (sel - 1 + filtered.length) % filtered.length : 0;
    }
  }

  $effect(() => {
    // Reset per open; focus the input once visible.
    if (ui.showPalette) {
      text = "";
      sel = 0;
      requestAnimationFrame(() => input?.focus());
    }
  });

  $effect(() => {
    // Keep selection valid while filtering.
    text;
    sel = 0;
  });
</script>

{#if ui.showPalette}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="palBackdrop"
    role="presentation"
    onclick={(e) => {
      if (e.target === e.currentTarget) close();
    }}
  >
    <div class="palCard" role="dialog" aria-modal="true" aria-label="Command palette">
      <div class="palSearch">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          bind:this={input}
          bind:value={text}
          type="text"
          placeholder="Search the dictionary or type a command…"
          aria-label="Command palette"
          autocomplete="off"
          spellcheck="false"
          onkeydown={onKeydown}
        />
        <kbd>esc</kbd>
      </div>
      <div class="palHint">
        <span>Enter: search{filtered.length ? " / run" : ""}</span>
        <span>↑↓: navigate</span>
      </div>
      <div class="palList" role="listbox" aria-label="Commands">
        {#if filtered.length === 0}
          <button
            type="button"
            class="palItem"
            onclick={() => search(text)}
          >
            <span>Search for “{text.trim()}”</span><kbd>↵</kbd>
          </button>
        {:else}
          {#each filtered as c, i (c.id)}
            <button
              type="button"
              role="option"
              aria-selected={i === sel}
              class="palItem"
              class:sel={i === sel}
              onmouseenter={() => (sel = i)}
              onclick={() => runEntry(c)}
            >
              <span>{c.label}</span>
              {#if c.hint}<kbd>{c.hint}</kbd>{/if}
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}
