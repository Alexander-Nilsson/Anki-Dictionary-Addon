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

/** Scroll offset of `el` relative to `ancestor` (mirrors legacy loop). */
export function offsetTopRelative(el: HTMLElement, ancestor: HTMLElement): number {
  let offsetTop = 0;
  let current: HTMLElement | null = el;
  while (current && current !== ancestor) {
    offsetTop += current.offsetTop;
    current = current.offsetParent as HTMLElement | null;
  }
  return offsetTop;
}

/** Scroll `el` into view within the results container. */
export function scrollToElement(el: HTMLElement): void {
  const w = getDefBox();
  if (!w) return;
  w.scrollTop = offsetTopRelative(el, w);
}

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
 * Navigate between sibling blocks (dictionaries or entries) inside the results
 * pane. Mirrors legacy `navigateDict` / `navigateDef`.
 */
export function navigate(
  startEl: HTMLElement,
  next: boolean,
  wantedClass: string,
): void {
  const w = getDefBox();
  if (!w) return;
  let el: HTMLElement | null = startEl;
  if (next) {
    while ((el = el.nextElementSibling as HTMLElement | null)) {
      if (el.classList && el.classList.contains(wantedClass)) {
        scrollToElement(el);
        break;
      }
    }
  } else {
    while ((el = el.previousElementSibling as HTMLElement | null)) {
      if (el.classList && el.classList.contains(wantedClass)) {
        scrollToElement(el);
        break;
      }
    }
  }
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
    const url = (el as HTMLElement).dataset?.url;
    if (url && !urls.includes(url)) urls.push(url);
  }
  return urls;
}