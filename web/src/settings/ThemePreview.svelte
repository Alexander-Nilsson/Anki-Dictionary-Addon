<script lang="ts">
  /**
   * Miniature of the dictionary window, painted with a theme's fourteen colors.
   *
   * Every element maps to something real in the dictionary UI — header and
   * search field, the tab strip with its gradient active tab, the sidebar, a
   * definition card with the searched term, an example-sentence highlight, a
   * pitch-accent reading and the Anki export button — so what the card shows
   * is what the window will look like.
   *
   * All sizes are in `em` and driven by `scale` (the root font size), so the
   * same markup renders as a 220px gallery thumbnail or a full-width hero.
   */
  import { rgba, type ThemeColors } from "../lib/theme";

  interface Props {
    theme: ThemeColors;
    /** Root font size in px; every dimension is a multiple of it. */
    scale?: number;
    term?: string;
  }

  let { theme, scale = 6, term = "example" }: Props = $props();
</script>

<div
  class="pv"
  style="font-size:{scale}px; background:{theme.header_background}; color:{theme.header_text}; border-color:{theme.border}"
  aria-hidden="true"
>
  <!-- Header: search field + group selector + export target pill -->
  <div class="pv-header" style="border-color:{theme.border}">
    <div
      class="pv-search"
      style="background:{theme.header_background}; border-color:{theme.border}"
    >
      <span class="pv-caret" style="background:{theme.search_term}"></span>
      <span class="pv-line w6" style="background:{rgba(theme.header_text, 0.45)}"></span>
    </div>
    <div
      class="pv-chip"
      style="background:{theme.selector}; border-color:{theme.border}"
    >
      <span class="pv-line w4" style="background:{rgba(theme.header_text, 0.5)}"></span>
    </div>
    <div
      class="pv-btn"
      style="background:linear-gradient({theme.current_tab_gradient_top},{theme.current_tab_gradient_bottom}); border-color:{theme.border}"
    >
      <span class="pv-line w3" style="background:{theme.anki_button_text}"></span>
    </div>
  </div>

  <!-- Tab strip: active (gradient) / hovered / idle -->
  <div class="pv-tabs">
    <div
      class="pv-tab active"
      style="background-image:linear-gradient({theme.current_tab_gradient_top},{theme.current_tab_gradient_bottom});
             border-color:{theme.border}; border-bottom-color:{theme.search_term}"
    >
      <span class="pv-line w5" style="background:{theme.header_text}"></span>
    </div>
    <div class="pv-tab" style="background:{theme.tab_hover}; border-color:{theme.border}">
      <span class="pv-line w4" style="background:{rgba(theme.header_text, 0.65)}"></span>
    </div>
    <div class="pv-tab" style="border-color:{theme.border}">
      <span class="pv-line w3" style="background:{rgba(theme.header_text, 0.4)}"></span>
    </div>
  </div>

  <div class="pv-body">
    <div class="pv-sidebar" style="background:{theme.selector}; border-color:{theme.border}">
      {#each [0.8, 0.55, 0.55, 0.4] as opacity, i (i)}
        <span
          class="pv-line"
          style="width:{80 - i * 12}%; background:{rgba(theme.header_text, opacity)}"
        ></span>
      {/each}
    </div>

    <div class="pv-main">
      <!-- Definition card: the surface most of the reading happens on -->
      <div
        class="pv-card"
        style="background:{theme.definition_background}; border-color:{theme.border};
               color:{theme.definition_text}"
      >
        <div class="pv-term-row">
          <span class="pv-term" style="color:{theme.search_term}">{term}</span>
          <span class="pv-pitch" style="color:{theme.pitch_accent_color}">◌́</span>
          <span class="pv-spacer"></span>
          <span
            class="pv-export"
            style="background:{theme.anki_button_background};
                   border-color:{theme.border}; color:{theme.anki_button_text}"
          >+</span>
        </div>
        <span class="pv-line w10" style="background:{rgba(theme.definition_text, 0.75)}"></span>
        <span class="pv-line w8" style="background:{rgba(theme.definition_text, 0.6)}"></span>
        <div class="pv-example" style="background:{rgba(theme.example_highlight, 0.4)}">
          <span class="pv-line w7" style="background:{rgba(theme.definition_text, 0.7)}"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .pv {
    border: 0.16em solid;
    border-radius: 1.2em;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    aspect-ratio: 16 / 10;
    user-select: none;
  }

  .pv-line {
    display: block;
    height: 0.55em;
    border-radius: 0.3em;
  }
  .w3 { width: 1.6em; }
  .w4 { width: 2.4em; }
  .w5 { width: 3em; }
  .w6 { width: 4.2em; }
  .w7 { width: 70%; }
  .w8 { width: 82%; }
  .w10 { width: 96%; }

  .pv-header {
    display: flex;
    align-items: center;
    gap: 0.6em;
    padding: 0.75em 0.9em;
    border-bottom: 0.14em solid;
  }
  .pv-search {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.4em;
    height: 1.9em;
    padding: 0 0.6em;
    border: 0.14em solid;
    border-radius: 0.6em;
  }
  .pv-caret {
    width: 0.16em;
    height: 0.9em;
    border-radius: 0.1em;
  }
  .pv-chip,
  .pv-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 1.9em;
    padding: 0 0.6em;
    border: 0.14em solid;
    border-radius: 0.6em;
  }

  .pv-tabs {
    display: flex;
    gap: 0.25em;
    padding: 0 0.9em;
    margin-bottom: -0.14em;
  }
  .pv-tab {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 4em;
    height: 1.8em;
    padding: 0 0.5em;
    border: 0.14em solid;
    border-bottom: 0.24em solid transparent;
    border-radius: 0.6em 0.6em 0 0;
  }

  .pv-body {
    flex: 1;
    display: flex;
    gap: 0.7em;
    padding: 0.8em 0.9em 0.9em;
    min-height: 0;
  }
  .pv-sidebar {
    width: 24%;
    display: flex;
    flex-direction: column;
    gap: 0.5em;
    padding: 0.6em 0.5em;
    border: 0.14em solid;
    border-radius: 0.7em;
  }
  .pv-main {
    flex: 1;
    min-width: 0;
  }
  .pv-card {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.55em;
    padding: 0.7em 0.8em;
    border: 0.14em solid;
    border-radius: 0.8em;
    box-shadow: 0 0.3em 0.6em rgba(0, 0, 0, 0.12);
  }
  .pv-term-row {
    display: flex;
    align-items: center;
    gap: 0.4em;
  }
  .pv-term {
    font-size: 1.5em;
    font-weight: 700;
    line-height: 1;
    max-width: 7em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pv-pitch {
    font-size: 1.2em;
    line-height: 1;
  }
  .pv-spacer {
    flex: 1;
  }
  .pv-export {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2em;
    height: 2em;
    border: 0.14em solid;
    border-radius: 0.5em;
    font-size: 1em;
    font-weight: 700;
    line-height: 1;
  }
  .pv-example {
    padding: 0.4em 0.5em;
    border-radius: 0.4em;
  }
</style>
