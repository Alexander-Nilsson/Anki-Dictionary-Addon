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
    >✂</div>
    <div
      role="button"
      tabindex="0"
      aria-label="Send to field"
      class="sendToField"
      data-key-handled
      onclick={(e) => handleSend(e, block)}
      onkeydown={(e) => onToolKey(e, (ev) => handleSend(ev, block))}
    >➞</div>
    <div class="defNav">
      <div
        role="button"
        tabindex="0"
        aria-label="Previous definition"
        class="prevDef"
        data-key-handled
        onclick={(e) => navigateDef(e, false)}
        onkeydown={(e) => onNavKey(e, false)}
      >▲</div>
      <div
        role="button"
        tabindex="0"
        aria-label="Next definition"
        class="nextDef"
        data-key-handled
        onclick={(e) => navigateDef(e, true)}
        onkeydown={(e) => onNavKey(e, true)}
      >▼</div>
    </div>
  </div>
</div>