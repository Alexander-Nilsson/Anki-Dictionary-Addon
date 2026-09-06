<script lang="ts">
  /**
   * Full theme editor: fourteen colors on the right, a live miniature and a
   * WCAG audit on the left. Nothing is written until Save — closing with
   * unsaved edits asks first.
   */
  import ThemePreview from "../ThemePreview.svelte";
  import {
    CONTRAST_PAIRS,
    KEY_GROUPS,
    contrastRatio,
    deriveTheme,
    ensureContrast,
    grade,
    isDarkTheme,
    isValidHex,
    normalizeHex,
    themeLabel,
    themesEqual,
    type ThemeColors,
    type ThemeKey,
  } from "../../lib/theme";

  interface Props {
    /** Theme id being edited; null when creating a brand-new theme. */
    name: string | null;
    colors: ThemeColors;
    /** Ids already taken — used to validate the name field. */
    existingNames: string[];
    /** Built-ins are edited as a copy: the name field is required. */
    readonlyName: boolean;
    onsave: (name: string, colors: ThemeColors, apply: boolean) => void;
    oncancel: () => void;
  }

  let { name, colors, existingNames, readonlyName, onsave, oncancel }: Props = $props();

  // The name/colors props are one-shot initializers: the modal remounts fresh
  // for each edit (via {#if}), so snapshotting them here is intentional.
  // svelte-ignore state_referenced_locally
  const original: ThemeColors = { ...colors };
  // svelte-ignore state_referenced_locally
  let draft = $state<ThemeColors>({ ...colors });
  // svelte-ignore state_referenced_locally
  let draftName = $state(name && !readonlyName ? name : suggestName(name));
  /** Raw text per field, so a half-typed hex doesn't wipe the color. */
  // svelte-ignore state_referenced_locally
  let text = $state<Record<string, string>>({ ...colors });
  // svelte-ignore state_referenced_locally
  let baseColor = $state(colors.header_background);
  // svelte-ignore state_referenced_locally
  let accentColor = $state(colors.search_term);
  let importText = $state("");
  let importError = $state("");

  const dirty = $derived(
    !themesEqual(draft, original) ||
      // A rename counts as a change only when there is a name to rename from;
      // a brand-new theme starts with a suggested name and no edits.
      (name !== null && !readonlyName && draftName !== name),
  );
  const dark = $derived(isDarkTheme(draft));
  const audit = $derived(
    CONTRAST_PAIRS.map((pair) => {
      const ratio = contrastRatio(draft[pair.fg], draft[pair.bg]);
      return { ...pair, ratio, grade: grade(ratio) };
    }),
  );
  /** Anything under AA for body text — "AA Large" still fails a definition. */
  const failing = $derived(audit.filter((a) => a.ratio < 4.5));
  const nameTaken = $derived(
    draftName !== name && existingNames.includes(draftName.trim()),
  );
  const nameValid = $derived(draftName.trim().length > 0 && !nameTaken);

  function suggestName(base: string | null): string {
    const stem = base ? `${base} copy` : "My theme";
    if (!existingNames.includes(stem)) return stem;
    for (let i = 2; ; i++) {
      const candidate = `${stem} ${i}`;
      if (!existingNames.includes(candidate)) return candidate;
    }
  }

  function setColor(key: ThemeKey, value: string): void {
    text[key] = value;
    if (isValidHex(value)) draft[key] = normalizeHex(value);
  }

  function commitText(key: ThemeKey): void {
    // Snap the field back to the last valid color when the user typed junk.
    text[key] = draft[key];
  }

  function resetKey(key: ThemeKey): void {
    draft[key] = original[key];
    text[key] = original[key];
  }

  function revertAll(): void {
    draft = { ...original };
    text = { ...original };
  }

  /** Rebuild every color from a background + accent pair. */
  function autoFill(): void {
    draft = deriveTheme(baseColor, accentColor);
    text = { ...draft };
  }

  /** Nudge only the foregrounds that fail WCAG AA until they pass. */
  function fixContrast(): void {
    for (const pair of CONTRAST_PAIRS) {
      if (contrastRatio(draft[pair.fg], draft[pair.bg]) >= 4.5) continue;
      draft[pair.fg] = ensureContrast(draft[pair.fg], draft[pair.bg], 4.5);
      text[pair.fg] = draft[pair.fg];
    }
  }

  function copyJson(): void {
    void navigator.clipboard?.writeText(JSON.stringify(draft, null, 2));
  }

  function importJson(): void {
    importError = "";
    try {
      const parsed = JSON.parse(importText) as Record<string, unknown>;
      const next = { ...draft };
      let applied = 0;
      for (const key of Object.keys(next) as ThemeKey[]) {
        const v = parsed[key];
        if (typeof v === "string" && isValidHex(v)) {
          next[key] = normalizeHex(v);
          applied++;
        }
      }
      if (!applied) {
        importError = "No theme colors found in that JSON.";
        return;
      }
      draft = next;
      text = { ...next };
      importText = "";
    } catch {
      importError = "That isn't valid JSON.";
    }
  }

  function save(apply: boolean): void {
    if (!nameValid) return;
    onsave(draftName.trim(), { ...draft }, apply);
  }

  /** Leaving with unsaved edits throws work away — ask first. */
  function cancel(): void {
    if (dirty && !confirm("Discard unsaved changes?")) return;
    oncancel();
  }

  function onKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") {
      e.stopPropagation();
      cancel();
    }
  }

  function autofocus(el: HTMLInputElement): void {
    el.focus();
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="modal-backdrop">
  <div class="modal theme-modal" role="dialog" aria-modal="true" aria-label="Theme editor">
    <div class="modal-header">
      <h3>{name ? `Edit ${themeLabel(name)}` : "New theme"}</h3>
      <span class="badge">{dark ? "Dark" : "Light"}</span>
      {#if dirty}<span class="badge dirty">Unsaved</span>{/if}
    </div>

    <div class="modal-body theme-editor">
      <!-- Left rail: what the theme actually looks like, plus its audit. -->
      <div class="theme-editor-preview">
        <ThemePreview theme={draft} scale={11} term="辞書" />

        <div class="audit">
          <div class="audit-head">
            <h4>Readability</h4>
            {#if failing.length}
              <button type="button" class="btn small" onclick={fixContrast}>
                Fix {failing.length} issue{failing.length === 1 ? "" : "s"}
              </button>
            {:else}
              <span class="status ok">Every pair passes AA</span>
            {/if}
          </div>
          <ul class="audit-list">
            {#each audit as row (row.label)}
              <li>
                <span
                  class="audit-swatch"
                  style="background:{draft[row.bg]}; color:{draft[row.fg]}; border-color:{draft.border}"
                >Aa</span>
                <span class="audit-label">{row.label}</span>
                <span class="audit-ratio">{row.ratio.toFixed(1)}:1</span>
                <span class="chip {row.grade === 'Fail' ? 'bad' : row.grade === 'AA Large' ? 'warn' : 'good'}">
                  {row.grade}
                </span>
              </li>
            {/each}
          </ul>
        </div>
      </div>

      <!-- Right rail: the colors themselves. -->
      <div class="theme-editor-fields">
        <div class="field">
          <label for="theme-name">Name</label>
          <input
            id="theme-name"
            type="text"
            class="grow"
            bind:value={draftName}
            use:autofocus
            aria-invalid={!nameValid}
          />
        </div>
        {#if nameTaken}
          <p class="hint bad-text">A theme called “{draftName.trim()}” already exists.</p>
        {:else if readonlyName && name}
          <p class="hint">
            {themeLabel(name)} ships with the addon, so your edits are saved as a new theme.
          </p>
        {/if}

        <details class="generator">
          <summary>Generate from two colors</summary>
          <p class="hint">
            Builds all fourteen colors from a background and an accent, stepping
            surfaces by luminance and nudging text until it passes AA.
          </p>
          <div class="gen-row">
            <label class="swatch-label">
              <input type="color" bind:value={baseColor} aria-label="Base background" />
              <span>Background</span>
            </label>
            <label class="swatch-label">
              <input type="color" bind:value={accentColor} aria-label="Accent" />
              <span>Accent</span>
            </label>
            <button type="button" class="btn" onclick={autoFill}>Fill colors</button>
          </div>
        </details>

        {#each KEY_GROUPS as group (group.id)}
          <div class="key-group">
            <h4>{group.label}</h4>
            {#each group.keys as meta (meta.key)}
              <div class="color-row">
                <input
                  type="color"
                  class="swatch"
                  value={draft[meta.key]}
                  oninput={(e) => setColor(meta.key, e.currentTarget.value)}
                  aria-label={`${meta.label} color picker`}
                />
                <span class="color-meta">
                  <span class="color-name">{meta.label}</span>
                  <span class="color-hint">{meta.hint}</span>
                </span>
                <input
                  type="text"
                  class="hex"
                  spellcheck="false"
                  value={text[meta.key]}
                  oninput={(e) => setColor(meta.key, e.currentTarget.value)}
                  onblur={() => commitText(meta.key)}
                  aria-label={`${meta.label} hex value`}
                  aria-invalid={!isValidHex(text[meta.key])}
                />
                <button
                  type="button"
                  class="icon-btn"
                  title="Reset to the saved value"
                  aria-label={`Reset ${meta.label}`}
                  disabled={draft[meta.key] === original[meta.key]}
                  onclick={() => resetKey(meta.key)}
                >↺</button>
              </div>
            {/each}
          </div>
        {/each}

        <details class="generator">
          <summary>Share this theme</summary>
          <div class="gen-row">
            <button type="button" class="btn" onclick={copyJson}>Copy as JSON</button>
          </div>
          <textarea
            class="import-box"
            rows="3"
            placeholder="…or paste a theme JSON here to load it"
            bind:value={importText}
          ></textarea>
          <div class="gen-row">
            <button type="button" class="btn" disabled={!importText.trim()} onclick={importJson}>
              Load pasted JSON
            </button>
            {#if importError}<span class="status bad">{importError}</span>{/if}
          </div>
        </details>
      </div>
    </div>

    <div class="modal-footer">
      <button type="button" class="btn" disabled={!dirty} onclick={revertAll}>Revert</button>
      <div style="flex:1"></div>
      <button type="button" class="btn" onclick={cancel}>Cancel</button>
      <button type="button" class="btn" disabled={!nameValid} onclick={() => save(false)}>
        Save
      </button>
      <button type="button" class="btn primary" disabled={!nameValid} onclick={() => save(true)}>
        Save &amp; Apply
      </button>
    </div>
  </div>
</div>
