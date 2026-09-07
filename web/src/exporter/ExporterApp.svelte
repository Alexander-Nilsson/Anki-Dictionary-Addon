<script lang="ts">
  /**
   * Card exporter — the Svelte replacement for the Qt `CardExporter` window.
   *
   * Layout mirrors the old widget top to bottom (template/deck row, sentence,
   * secondary, word, notes, definitions table, audio, image, tags, unknown
   * count, auto-definition row, footer) so the muscle memory of existing users
   * survives the port. Python remains the source of truth: every edit is
   * mirrored over the bridge, and Python pushes state back whenever the
   * dictionary window sends something here.
   */
  import { onMount } from "svelte";
  import { exporter } from "../lib/exporter.svelte";
  import { requestExporterState } from "../lib/exporter.svelte";
  import RichTextField from "./RichTextField.svelte";
  import DefinitionSettingsModal from "./DefinitionSettingsModal.svelte";

  let showDefinitionSettings = $state(false);
  let wordInput: HTMLInputElement | null = $state(null);

  const s = $derived(exporter.state);
  const hasAudio = $derived(s.audioLabel !== "No Audio Selected");
  const hasImage = $derived(s.imageLabel !== "No Image Selected");

  onMount(() => {
    requestExporterState();
    // Esc closes the window, matching the Qt shortcut it replaces.
    const onkeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") exporter.close();
    };
    window.addEventListener("keydown", onkeydown);
    return () => window.removeEventListener("keydown", onkeydown);
  });

  $effect(() => {
    if (exporter.focusRequest === "word" && wordInput) {
      wordInput.focus();
      exporter.focusRequest = "";
    }
  });

  function searchFromInput(event: KeyboardEvent): void {
    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    if (key !== "s" && key !== "f") return;
    const input = event.currentTarget as HTMLInputElement;
    const text = input.value.slice(input.selectionStart ?? 0, input.selectionEnd ?? 0);
    if (text.trim()) {
      event.preventDefault();
      exporter.search(text, key === "f");
    }
  }
</script>

<div class="exporter">
  <header class="exporter-header">
    <label class="inline" for="template">Template</label>
    <select
      id="template"
      title={s.tooltips ? "Select the export template." : ""}
      value={s.template}
      onchange={(e) => exporter.setField("template", e.currentTarget.value)}
    >
      {#each s.templates as name (name)}
        <option value={name}>{name}</option>
      {/each}
    </select>

    <label class="inline" for="deck">Deck</label>
    <select
      id="deck"
      title={s.tooltips ? "Select the deck to export to." : ""}
      value={s.deck}
      onchange={(e) => exporter.setField("deck", e.currentTarget.value)}
    >
      {#each s.decks as name (name)}
        <option value={name}>{name}</option>
      {/each}
    </select>

    <span class="spacer"></span>
    <button
      type="button"
      class="btn"
      title={s.tooltips ? "Clear the card exporter." : ""}
      onclick={() => exporter.clear()}>Clear Current Card</button
    >
  </header>

  <div class="exporter-body">
    <span class="block">Sentence</span>
    <RichTextField
      value={s.sentence}
      placeholder="Sentence"
      maxHeight={120}
      onchange={(html) => exporter.setField("sentence", html)}
    />

    <span class="block">Secondary</span>
    <RichTextField
      value={s.secondary}
      placeholder="Secondary"
      maxHeight={120}
      onchange={(html) => exporter.setField("secondary", html)}
    />

    <label class="block" for="word">Word</label>
    <input
      id="word"
      class="word-input"
      type="text"
      bind:this={wordInput}
      value={s.word}
      oninput={(e) => exporter.setField("word", e.currentTarget.value)}
      onkeydown={searchFromInput}
    />

    <span class="block">User Notes</span>
    <RichTextField
      value={s.notes}
      placeholder="User Notes"
      minHeight={90}
      onchange={(html) => exporter.setField("notes", html)}
    />

    <span class="block">Definitions</span>
    <div class="definitions">
      {#if s.definitions.length === 0}
        <p class="empty-row">No definitions added yet.</p>
      {/if}
      {#each s.definitions as row, i (i)}
        <div class="definition-row">
          <span class="dict-name">{row.name}</span>
          {#if row.thumbs.length}
            <span class="thumbs">
              {#each row.thumbs as thumb (thumb)}
                <img src={thumb} alt="" />
              {/each}
            </span>
          {:else}
            <span class="short-def">{row.short}</span>
          {/if}
          <button
            type="button"
            class="btn danger"
            aria-label="Remove definition"
            onclick={() => exporter.removeDefinition(i)}>&#x2715;</button
          >
        </div>
      {/each}
    </div>

    <span class="block">Audio</span>
    <div class="media-row">
      <span class="media-label">{s.audioLabel}</span>
      {#if hasAudio}
        <button type="button" class="btn" onclick={() => exporter.playAudio()}>Play</button>
      {/if}
    </div>

    <span class="block">Image</span>
    <div class="media-row">
      {#if hasImage && s.imagePreview}
        <img class="image-preview" src={s.imagePreview} alt={s.imageLabel} />
      {:else}
        <span class="media-label">{s.imageLabel}</span>
      {/if}
    </div>

    <label class="block" for="tags">Tags</label>
    <input
      id="tags"
      type="text"
      value={s.tags}
      oninput={(e) => exporter.setField("tags", e.currentTarget.value)}
      onkeydown={searchFromInput}
    />

    <div class="field">
      <label for="unknowns">Number of unknown words to search</label>
      <span class="spacer"></span>
      <input
        id="unknowns"
        type="number"
        min="0"
        max="10"
        style="width:76px;flex:0 0 auto"
        value={s.unknownsToSearch}
        oninput={(e) =>
          exporter.setField("unknownsToSearch", Number(e.currentTarget.value) || 0)}
      />
    </div>

    <div class="field">
      <label class="checkbox">
        <input
          type="checkbox"
          checked={s.autoAddDefinitions}
          onchange={(e) =>
            exporter.setField("autoAddDefinitions", e.currentTarget.checked)}
        />
        Automatically Add Definitions
      </label>
      <span class="spacer"></span>
      <button type="button" class="btn" onclick={() => (showDefinitionSettings = true)}>
        Automatic Definition Settings
      </button>
    </div>
  </div>

  <footer class="exporter-footer">
    <label class="checkbox">
      <input
        type="checkbox"
        checked={s.autoAdd}
        onchange={(e) => exporter.setField("autoAdd", e.currentTarget.checked)}
      />
      Add Extension Cards Automatically
    </label>
    <span class="spacer"></span>
    <button type="button" class="btn" onclick={() => exporter.close()}>Cancel</button>
    <button type="button" class="btn primary" onclick={() => exporter.add()}>Add</button>
  </footer>
</div>

{#if showDefinitionSettings}
  <DefinitionSettingsModal onclose={() => (showDefinitionSettings = false)} />
{/if}
