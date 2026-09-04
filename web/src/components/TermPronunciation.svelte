<script lang="ts">
  import type { DictDocument, TermPronunciationBlockData } from "../lib/types";
  import {
    cleanTermDef,
    fontFamilyFromAttr,
    getMainWordsFromFragment,
    getSelectionText,
    navigate,
  } from "../lib/dom";
  import { CMD, pycmd } from "../lib/pycmd";
  import { showToast } from "../lib/toast.svelte";

  const {
    doc,
    block,
  }: { doc: DictDocument; block: TermPronunciationBlockData } = $props();
  const fontFamily = $derived(fontFamilyFromAttr(block.font));

  /** tpCont text as the legacy `termTitle.textContent` produced (stars etc.). */
  function tpContRaw(b: TermPronunciationBlockData): string {
    const parts = [b.headerHtml, b.stars];
    if (b.rank) parts.push(b.rank.label);
    if (b.levels) parts.push(...b.levels.map((l) => l.label));
    return parts.join(" ");
  }

  /** Full definition text (processed + highlighted HTML, tags stripped). */
  function definitionText(b: TermPronunciationBlockData): string {
    return cleanTermDef(b.definitionHtml, "<br>");
  }

  /** Word pronoun line: tpCont text + newline (legacy `getWordPron` parity). */
  function wordPronText(b: TermPronunciationBlockData): string {
    return tpContRaw(b) + "\n";
  }

  function handleExport(_ev: Event, b: TermPronunciationBlockData): void {
    const selection = getSelectionText() || "";
    const word = getMainWordsFromFragment(b.headerHtml);
    let text: string;
    if (selection) {
      text =
        cleanTermDef(tpContRaw(b), "<br>") +
        "<br>" +
        selection.replace(/\n/g, "<br>");
    } else {
      text = wordPronText(b) + "<br>" + definitionText(b);
    }
    pycmd(CMD.addDef(b.cleanName, word, text));
    showToast("Added to export window");
  }

  function handleClip(_ev: Event, b: TermPronunciationBlockData): void {
    const selection = getSelectionText() || "";
    let text: string;
    if (selection) {
      text = wordPronText(b) + selection;
    } else {
      text = wordPronText(b) + "<br>" + definitionText(b);
    }
    pycmd(CMD.clipped(text));
    showToast("Copied to clipboard");
  }

  function handleSend(_ev: Event, b: TermPronunciationBlockData): void {
    const selection = getSelectionText() || "";
    let text: string;
    if (selection) {
      text =
        cleanTermDef(tpContRaw(b), "<br>") +
        "<br>" +
        selection.replace(/\n/g, "<br>");
    } else {
      text = wordPronText(b) + "<br>" + definitionText(b);
    }
    pycmd(CMD.sendToField(b.cleanName, text));
    showToast("Sent to field");
  }

  function navigateDef(ev: Event, next: boolean): void {
    const el = (ev.currentTarget as HTMLElement).closest(
      ".termPronunciation",
    ) as HTMLElement | null;
    if (el) navigate(el, next, "termPronunciation");
  }

  function onToolKey(ev: KeyboardEvent, fn: (ev: Event) => void): void {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      fn(ev);
    }
  }

  function onNavKey(ev: KeyboardEvent, next: boolean): void {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      navigateDef(ev, next);
    }
  }

  // QW1: crisp inline SVG action icons (the legacy glyph set ✂➞▲▼ doesn't
  // scale on HiDPI). Scissors/copy, send, and chevron nav.
  const ICONS = {
    clip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>',
    next: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
    prev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>',
  };
</script>

<div class="termPronunciation" data-index={block.dataIndex}>
  <span class="tpCont" style:font-family={fontFamily}>
    {@html block.headerHtml}{" "}
    {#if block.stars}
      <span class="starcount" title={block.starTip || undefined}>{block.stars}</span>
    {/if}
    {#if block.rank}
      {" "}<span class="starcount frequency-rank" title={block.rank.tip || undefined}>{block.rank.label}</span>
    {/if}
    {#if block.levels}
      {#each block.levels as level (level.label)}
        {" "}<span class="starcount level-label" title={level.source || undefined}>{level.label}</span>
      {/each}
    {/if}
  </span>
  <div class="defTools">
    <div
      role="button"
      tabindex="0"
      aria-label="Export to Anki"
      class="ankiExportButton"
      data-key-handled
      onclick={(e) => handleExport(e, block)}
      onkeydown={(e) => onToolKey(e, (ev) => handleExport(ev, block))}
    >
      <img src={doc.ankiIcon} alt="" />
    </div>
    <div
      role="button"
      tabindex="0"
      aria-label="Copy to clipboard"
      class="clipper"
      data-key-handled
      onclick={(e) => handleClip(e, block)}
      onkeydown={(e) => onToolKey(e, (ev) => handleClip(ev, block))}
    >{@html ICONS.clip}</div>
    <div
      role="button"
      tabindex="0"
      aria-label="Send to field"
      class="sendToField"
      data-key-handled
      onclick={(e) => handleSend(e, block)}
      onkeydown={(e) => onToolKey(e, (ev) => handleSend(ev, block))}
    >{@html ICONS.send}</div>
    <div class="defNav">
      <div
        role="button"
        tabindex="0"
        aria-label="Previous definition"
        class="prevDef"
        data-key-handled
        onclick={(e) => navigateDef(e, false)}
        onkeydown={(e) => onNavKey(e, false)}
      >{@html ICONS.prev}</div>
      <div
        role="button"
        tabindex="0"
        aria-label="Next definition"
        class="nextDef"
        data-key-handled
        onclick={(e) => navigateDef(e, true)}
        onkeydown={(e) => onNavKey(e, true)}
      >{@html ICONS.next}</div>
    </div>
  </div>
</div>