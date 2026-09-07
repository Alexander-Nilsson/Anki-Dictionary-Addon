/**
 * DOM helpers and text-extraction utilities ported from the legacy
 * `assets/scripts/dictionary.js`. These are used by the compat layer that keeps
 * Python-generated HTML (which references globals like `getDefinitionWord`)
 * working inside the Svelte shell.
 */

/** The scrollable results pane. */
export function getDefBox(): HTMLElement | null {
  return document.getElementById("defBox");
}

/** Scroll offset of `el` relative to `ancestor` (mirrors legacy loop).
 *
 * Sticky dictionary headers report their displaced (stuck) position through
 * `offsetTop`, so navigating from or to one while scrolled yields garbage
 * offsets and the arrows appear dead. A sticky box still occupies its static
 * space in the flow, so measuring it as `static` doesn't reflow siblings —
 * just the one forced reflow for the read.
 */
export function offsetTopRelative(el: HTMLElement, ancestor: HTMLElement): number {
  let restored: string | null = null;
  if (getComputedStyle(el).position === "sticky") {
    restored = el.style.position;
    el.style.position = "static";
  }
  try {
    let offsetTop = 0;
    let current: HTMLElement | null = el;
    while (current && current !== ancestor) {
      offsetTop += current.offsetTop;
      current = current.offsetParent as HTMLElement | null;
    }
    return offsetTop;
  } finally {
    if (restored !== null) el.style.position = restored;
  }
}

/** Height of the dictionary header(s) currently stuck to the pane top.
 *
 * In doc-mode the title blocks are `position: sticky`, so they sit over the
 * scrolled content in an opaque band. Anything scrolled to exactly the pane
 * top would hide underneath them (and during a sticky handoff two headers
 * can overlap) — navigation targets must land below this band. 0 on the
 * legacy page, which has no sticky headers.
 */
export function stuckHeaderHeight(): number {
  const w = getDefBox();
  if (!w) return 0;
  const titles = Array.from(
    document.querySelectorAll<HTMLElement>(".dictionaryTitleBlock"),
  );
  if (titles.length === 0) return 0;
  // Legacy/unstuck shells keep exact offsets — there is no covering band.
  if (getComputedStyle(titles[0]).position !== "sticky") return 0;
  const top = w.getBoundingClientRect().top;
  let height = 0;
  for (const t of titles) {
    const r = t.getBoundingClientRect();
    if (Math.abs(r.top - top) < 4) height = Math.max(height, r.height);
  }
  if (height === 0) {
    // Nothing stuck (e.g. sitting at the very top): the first header sticks
    // as soon as we scroll past it and covers the same band.
    height = titles[0].getBoundingClientRect().height;
  }
  return height;
}

/** Scroll position that would bring `el` (layout top `top`) into view.
 *
 * Extracted from {@link scrollToElement} so navigation can compare candidate
 * targets without scrolling.
 */
export function scrollTargetFor(
  el: HTMLElement,
  top: number,
  w: HTMLElement,
): number {
  if (el.classList.contains("dictionaryTitleBlock")) {
    const max = w.scrollHeight - w.clientHeight;
    return top <= max ? top : Math.max(top - stuckHeaderHeight(), 0);
  }
  return Math.max(top - stuckHeaderHeight(), 0);
}

/** Scroll `el` into view within the results container.
 *
 * Entry targets land below the stuck header band; dictionary title blocks
 * keep the exact offset because they stick to the pane top themselves —
 * except near the content end, where the exact offset is past the scroll
 * limit: clamping there would pin the target underneath the stuck header (or
 * not move at all), so those land just below the band instead.
 */
export function scrollToElement(el: HTMLElement): void {
  const w = getDefBox();
  if (!w) return;
  w.scrollTop = scrollTargetFor(el, offsetTopRelative(el, w), w);
}

/** Minimum scroll change (px) for a navigation step to count as a move.
 *
 * Near the content end the adjacent section can already be (almost) fully
 * visible — e.g. a one-item Forvo block — so scrolling to it shifts the view
 * by a few pixels and the arrows look dead.
 */
const NAV_MIN_DELTA = 24;

/** Extract a font-family from Python's font attribute (`" "` when unset). */
export function fontFamilyFromAttr(font: string): string | undefined {
  const m = /font-family:\s*([^;"']+);?/.exec(font);
  if (!m) return undefined;
  const family = m[1].trim();
  return family || undefined;
}

/** Main words (max 2, ", "-joined) parsed from a headword HTML fragment. */
export function getMainWordsFromFragment(headerHtml: string): string {
  const div = document.createElement("div");
  div.innerHTML = headerHtml;
  return getMainWords(div);
}

/** Selected text in the page (false when nothing is selected). */
export function getSelectionText(): string | false {
  let text = "";
  if (window.getSelection) {
    text = window.getSelection()?.toString() ?? "";
  }
  if (text === "") return false;
  return text.replace(/\n✂➠\n▲\n▼\n/g, "\n");
}

/** Strip HTML from `text`, converting <br> variants to `rep`. */
export function cleanTermDef(text: string, rep: string): string {
  let result = text.replace(/<br\s*\/?>/gi, "---NL---");
  result = result
    .replace(/<[^>]+>/g, "")
    .replace("✂", "")
    .replace("➠", "")
    .replace("▲", "")
    .replace("▼", "");
  result = result.replace(/---NL---/g, rep);
  const escapedRep = rep.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const leadingRegex = new RegExp(`^(${escapedRep}|\\s)+`, "g");
  const trailingRegex = new RegExp(`(${escapedRep}|\\s)+$`, "g");
  return result.replace(leadingRegex, "").replace(trailingRegex, "");
}

/** The main word(s) for a definition block (joined with ", "). */
export function getMainWords(termTitle: HTMLElement): string {
  let terms = termTitle.getElementsByClassName("mainword");
  if (terms.length === 0) {
    terms = termTitle.getElementsByClassName("terms");
  }
  const texts: string[] = [];
  for (const term of Array.from(terms)) {
    const t = term.textContent ?? "";
    if (t !== "") texts.push(t);
  }
  return texts.slice(0, 2).join(", ");
}

export interface WordDefinition {
  word: string;
  definition: string;
}

/**
 * Word + cleaned definition text for a block, mirroring the legacy
 * `getDefinitionWord(dictEl, termBody, termTitle)`.
 */
export function getDefinitionWord(
  termBody: HTMLElement,
  termTitle: HTMLElement,
): WordDefinition {
  const definition = cleanTermDef(termBody.innerHTML, "<br>");
  const word = getMainWords(termTitle);
  const tpCont = termTitle.querySelector(".tpCont");
  const wordPron = tpCont ? tpCont.textContent ?? "" : "";
  return { word, definition: `${wordPron}<br>${definition}` };
}

/** Word + pronunciation preview for clipboard use (legacy `getWordPron`). */
export function getWordPron(termTitle: HTMLElement): string {
  const tpCont = termTitle.querySelector(".tpCont");
  return `${tpCont ? tpCont.textContent ?? "" : ""}\n`;
}

/**
 * Navigate between blocks (dictionaries or entries) inside the results pane.
 * Mirrors legacy `navigateDict` / `navigateDef`.
 *
 * Traversal is in document order within the current tab — not by siblings —
 * so it crosses dictionary boundaries, including the Images/LLM/Forvo
 * service sections whose blocks are nested inside loader wrappers.
 *
 * Focus travels with the navigation: it lands on the target block's matching
 * arrow, so repeated presses (or Enter/Space on the focused button) continue
 * from the newly visible entry/dictionary instead of the old one.
 */
export function navigate(
  startEl: HTMLElement,
  next: boolean,
  wantedClass: string,
): void {
  const w = getDefBox();
  if (!w) return;
  const buttonClass =
    wantedClass === "dictionaryTitleBlock"
      ? next
        ? "nextDict"
        : "prevDict"
      : next
        ? "nextDef"
        : "prevDef";
  const scope = startEl.closest(".tabContent") ?? w;
  const blocks = Array.from(scope.querySelectorAll<HTMLElement>(`.${wantedClass}`));
  const idx = blocks.indexOf(startEl);
  if (idx === -1) return;
  // Short trailing sections (e.g. a one-item Forvo block) can already be
  // fully visible while a neighbour is current: scrolling to the adjacent
  // block then changes nothing and the arrows look dead. Keep stepping the
  // same direction until a step would visibly move the view — going back up
  // always lands somewhere new. If no further block would (true first/last
  // with everything in view), fall back to the adjacent block so focus still
  // travels; with no adjacent block, stay put.
  const tops = blocks.map((b) => offsetTopRelative(b, w));
  const current = w.scrollTop;
  const step = next ? 1 : -1;
  const adjacent = idx + step >= 0 && idx + step < blocks.length ? idx + step : -1;
  let target = -1;
  for (let j = idx + step; j >= 0 && j < blocks.length; j += step) {
    if (Math.abs(scrollTargetFor(blocks[j], tops[j], w) - current) >= NAV_MIN_DELTA) {
      target = j;
      break;
    }
  }
  if (target === -1) {
    if (adjacent === -1) return;
    target = adjacent;
  }
  const el = blocks[target];
  scrollToElement(el);
  el.querySelector<HTMLElement>(`.${buttonClass}`)?.focus({
    preventScroll: true,
  });
}

/** Find the dictionary title block preceding a term block. */
export function findDictionaryBlock(el: HTMLElement): HTMLElement | null {
  let dict = el.previousElementSibling as HTMLElement | null;
  while (dict && !dict.classList.contains("dictionaryTitleBlock")) {
    dict = dict.previousElementSibling as HTMLElement | null;
  }
  return dict;
}

/** Collected (de-duplicated) image URLs from selected images in a block. */
export function collectSelectedImageUrls(block: HTMLElement): string[] {
  const selected = block.querySelectorAll(
    ".selectedImage, .imgBox.selected .imageHighlight",
  );
  const urls: string[] = [];
  for (const el of Array.from(selected)) {
    // `data-full-url` is the original image; `data-url` is the inlined grid
    // thumbnail, kept as the fallback for HTML rendered by older builds.
    const data = (el as HTMLElement).dataset;
    const url = data?.fullUrl || data?.url;
    if (url && !urls.includes(url)) urls.push(url);
  }
  return urls;
}