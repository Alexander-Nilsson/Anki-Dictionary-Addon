<script lang="ts">
  /**
   * Theme gallery.
   *
   * Themes are chosen by looking at them: every card is a live miniature of
   * the dictionary window painted with that theme's colors, so there is no
   * guessing what "Gruvbox" or a hand-rolled theme will do to the window.
   * Picking a card applies it immediately (with one-press undo); the editor
   * modal handles the fourteen individual colors.
   */
  import ThemePreview from "./ThemePreview.svelte";
  import ThemeEditorModal from "./modals/ThemeEditorModal.svelte";
  import {
    applyTheme,
    deleteTheme,
    saveTheme,
    settings,
  } from "../lib/settings.svelte";
  import { isDarkTheme, themeLabel, type ThemeColors } from "../lib/theme";

  type Filter = "all" | "light" | "dark" | "custom";

  let query = $state("");
  let filter = $state<Filter>("all");
  let focusedIndex = $state(0);
  /** Theme that was active before the last apply, for the undo affordance. */
  let previous = $state<string | null>(null);
  let notice = $state("");

  let editing = $state<{ name: string | null; colors: ThemeColors; readonly: boolean } | null>(
    null,
  );

  const FILTERS: { id: Filter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "light", label: "Light" },
    { id: "dark", label: "Dark" },
    { id: "custom", label: "Custom" },
  ];

  const allNames = $derived(Object.keys(settings.themes));

  const entries = $derived(
    allNames
      .map((name) => ({
        name,
        colors: settings.themes[name],
        dark: isDarkTheme(settings.themes[name]),
        builtin: settings.builtinThemes.includes(name),
      }))
      .filter((t) => {
        if (filter === "light" && t.dark) return false;
        if (filter === "dark" && !t.dark) return false;
        if (filter === "custom" && t.builtin) return false;
        const q = query.trim().toLowerCase();
        return !q || themeLabel(t.name).toLowerCase().includes(q);
      })
      .sort((a, b) => {
        // Custom themes first — they are the ones a user came here to find.
        if (a.builtin !== b.builtin) return a.builtin ? 1 : -1;
        return themeLabel(a.name).localeCompare(themeLabel(b.name));
      }),
  );

  function select(name: string): void {
    if (name === settings.activeTheme) return;
    previous = settings.activeTheme;
    applyTheme(name);
    notice = `Applied ${themeLabel(name)}.`;
  }

  function undo(): void {
    if (!previous) return;
    const target = previous;
    previous = null;
    applyTheme(target);
    notice = `Restored ${themeLabel(target)}.`;
  }

  function uniqueName(stem: string): string {
    if (!allNames.includes(stem)) return stem;
    for (let i = 2; ; i++) {
      if (!allNames.includes(`${stem} ${i}`)) return `${stem} ${i}`;
    }
  }

  function duplicate(name: string): void {
    const copy = uniqueName(`${themeLabel(name)} copy`);
    saveTheme(copy, { ...settings.themes[name] }, false);
    notice = `Created ${copy}.`;
  }

  function edit(name: string): void {
    editing = {
      name,
      colors: { ...settings.themes[name] },
      readonly: settings.builtinThemes.includes(name),
    };
  }

  function newTheme(): void {
    const base = settings.themes[settings.activeTheme] ?? entries[0]?.colors;
    if (!base) return;
    editing = { name: null, colors: { ...base }, readonly: false };
  }

  function remove(name: string): void {
    if (!confirm(`Delete the theme “${themeLabel(name)}”? This cannot be undone.`)) return;
    deleteTheme(name);
    notice = `Deleted ${themeLabel(name)}.`;
  }

  function onEditorSave(name: string, colors: ThemeColors, apply: boolean): void {
    if (apply) previous = settings.activeTheme;
    saveTheme(name, colors, apply);
    notice = apply ? `Saved and applied ${themeLabel(name)}.` : `Saved ${themeLabel(name)}.`;
    editing = null;
  }

  /** Grid keyboard model: arrows move focus, Enter/Space applies. */
  function onGridKeydown(e: KeyboardEvent): void {
    const count = entries.length;
    if (!count) return;
    const columns = gridColumns();
    let next: number | null = null;
    if (e.key === "ArrowRight") next = Math.min(focusedIndex + 1, count - 1);
    else if (e.key === "ArrowLeft") next = Math.max(focusedIndex - 1, 0);
    else if (e.key === "ArrowDown") next = Math.min(focusedIndex + columns, count - 1);
    else if (e.key === "ArrowUp") next = Math.max(focusedIndex - columns, 0);
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = count - 1;
    else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      select(entries[focusedIndex].name);
      return;
    }
    if (next === null) return;
    e.preventDefault();
    focusedIndex = next;
    document.getElementById(`theme-card-${entries[next].name}`)?.focus();
  }

  /** Read the real column count off the grid so arrow keys match the layout. */
  function gridColumns(): number {
    const grid = document.getElementById("theme-gallery");
    if (!grid) return 1;
    const cols = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
    return Math.max(1, cols);
  }
</script>

<div class="card">
  <div class="theme-toolbar">
    <h3>Theme</h3>
    <div class="filter-chips" role="group" aria-label="Filter themes">
      {#each FILTERS as f (f.id)}
        <button
          type="button"
          class="chip-btn"
          class:active={filter === f.id}
          aria-pressed={filter === f.id}
          onclick={() => (filter = f.id)}
        >{f.label}</button>
      {/each}
    </div>
    <input
      type="search"
      class="theme-search"
      placeholder="Search themes…"
      aria-label="Search themes"
      bind:value={query}
    />
    <button type="button" class="btn primary" onclick={newTheme}>New theme</button>
  </div>

  <p class="hint">
    Applies to the dictionary window immediately — the settings window keeps
    Anki's own styling.
  </p>

  {#if !settings.themesLoaded}
    <p class="hint">Loading themes…</p>
  {:else if entries.length === 0}
    <p class="hint">No themes match “{query}”.</p>
  {:else}
    <div
      id="theme-gallery"
      class="theme-gallery"
      role="listbox"
      aria-label="Available themes"
      tabindex="-1"
      onkeydown={onGridKeydown}
    >
      {#each entries as t, i (t.name)}
        <div class="theme-card" class:active={t.name === settings.activeTheme}>
          <button
            type="button"
            role="option"
            id={`theme-card-${t.name}`}
            class="theme-card-hit"
            aria-selected={t.name === settings.activeTheme}
            tabindex={i === focusedIndex ? 0 : -1}
            onfocus={() => (focusedIndex = i)}
            onclick={() => select(t.name)}
          >
            <div class="theme-thumb">
              <ThemePreview theme={t.colors} scale={6.5} />
              {#if t.name === settings.activeTheme}
                <span class="active-check" aria-hidden="true">✓</span>
              {/if}
            </div>
            <span class="theme-card-meta">
              <span class="theme-card-name">{themeLabel(t.name)}</span>
              <span class="badge">{t.dark ? "Dark" : "Light"}</span>
              {#if !t.builtin}<span class="badge custom">Custom</span>{/if}
            </span>
          </button>
          <div class="theme-card-actions">
            <button type="button" class="btn small" onclick={() => edit(t.name)}>
              {t.builtin ? "Customize" : "Edit"}
            </button>
            <button type="button" class="btn small" onclick={() => duplicate(t.name)}>
              Duplicate
            </button>
            {#if !t.builtin}
              <button type="button" class="btn small danger" onclick={() => remove(t.name)}>
                Delete
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if notice}
    <div class="theme-notice" role="status">
      <span>{notice}</span>
      {#if previous}
        <button type="button" class="btn small" onclick={undo}>
          Undo (back to {themeLabel(previous)})
        </button>
      {/if}
      <button type="button" class="icon-btn" aria-label="Dismiss" onclick={() => (notice = "")}>
        ✕
      </button>
    </div>
  {/if}
</div>

{#if editing}
  <ThemeEditorModal
    name={editing.name}
    colors={editing.colors}
    readonlyName={editing.readonly}
    existingNames={allNames}
    onsave={onEditorSave}
    oncancel={() => (editing = null)}
  />
{/if}
