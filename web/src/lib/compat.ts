/**
 * Compat layer: keeps Python-generated HTML working inside the Svelte shell.
 *
 * The Python renderer emits content with inline `onclick`/`onmousedown`
 * attributes referencing global functions (`ankiExport`, `clipText`, ...).
 * These globals are redefined here — ported from the legacy
 * `assets/scripts/dictionary.js` — so injected `{@html}` stays fully
 * interactive while the shell is Svelte-owned. Future phases move content
 * rendering into components and delete most of this file.
 */
import {
  cleanTermDef,
  collectSelectedImageUrls,
  findDictionaryBlock,
  getDefinitionWord,
  getMainWords,
  getSelectionText,
  getWordPron,
  navigate,
} from "./dom";
import { CMD, pycmd } from "./pycmd";
import { showToast } from "./toast.svelte";

// ── keyboard accessibility ─────────────────────────
// The Python renderer marks tool/icon buttons with role="button" and
// tabindex="0"; make Enter/Space trigger their inline onclick handlers, the
// same way a native <button> works.

document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const target = e.target as HTMLElement | null;
  if (!target || target.getAttribute("role") !== "button") return;
  e.preventDefault();
  target.click();
});

// ── clipboard / export ─────────────────────────────

function getDefExport(ev: Event, dictName: string): void {
  const target = ev.target as HTMLElement;
  const definition = getSelectionText();
  const termTitle = target.closest(".termPronunciation") as HTMLElement | null;
  if (!termTitle) return;
  const termBody = termTitle.nextElementSibling as HTMLElement | null;
  const dictionaryElement = findDictionaryBlock(termTitle);
  if (!termBody || !dictionaryElement) return;

  const { word, definition: wordDefinition } = getDefinitionWord(termBody, termTitle);
  let text: string;
  if (!definition) {
    text = wordDefinition;
  } else {
    text =
      cleanTermDef(termTitle.textContent ?? "", "<br>") +
      "<br>" +
      definition.replace(/\n/g, "<br>");
  }
  pycmd(CMD.addDef(dictName, word, text));
  showToast("Added to export window");
}

function getImageExport(ev: Event, _dictName: string): void {
  const target = ev.target as HTMLElement;
  const termTitle = target.closest(".termPronunciation") as HTMLElement | null;
  if (!termTitle) return;
  const defBlock = termTitle.nextElementSibling as HTMLElement | null;
  if (!defBlock) return;
  const word = getMainWords(termTitle);
  const urls = collectSelectedImageUrls(defBlock);
  if (urls.length > 0) {
    pycmd(CMD.imgExport(word, urls));
    showToast("Added images to export window");
  }
}

/** Route export by dictionary type (images vs. definitions). */
function ankiExport(ev: Event, dictName: string): void {
  if (dictName === "Images") getImageExport(ev, dictName);
  else getDefExport(ev, dictName);
}

function clipText(ev: Event): void {
  const target = ev.target as HTMLElement;
  const definition = getSelectionText();
  const termTitle = target.closest(".termPronunciation") as HTMLElement | null;
  if (!termTitle) return;
  const termBody = termTitle.nextElementSibling as HTMLElement | null;
  if (!termBody) return;

  const dictionaryElement = findDictionaryBlock(termTitle);
  const isImages =
    dictionaryElement
      ?.querySelector(".dictionaryTitle")
      ?.textContent?.trim() === "Images";

  if (isImages) {
    const urls = collectSelectedImageUrls(termBody);
    if (urls.length > 0) {
      pycmd(CMD.clippedImages(urls));
      showToast("Images copied");
      return;
    }
  }

  let text: string;
  if (!definition) {
    text = getDefinitionWord(termBody, termTitle).definition;
  } else {
    text = getWordPron(termTitle) + definition;
  }
  pycmd(CMD.clipped(text));
  showToast("Copied to clipboard");
}

function getDefForField(ev: Event, dictName: string): void {
  const target = ev.target as HTMLElement;
  const definition = getSelectionText();
  const termTitle = target.closest(".termPronunciation") as HTMLElement | null;
  if (!termTitle) return;
  const termBody = termTitle.nextElementSibling as HTMLElement | null;
  const dictionaryElement = findDictionaryBlock(termTitle);
  if (!termBody || !dictionaryElement) return;

  const { definition: wordDefinition } = getDefinitionWord(termBody, termTitle);
  let text: string;
  if (!definition) {
    text = wordDefinition;
  } else {
    text =
      cleanTermDef(termTitle.textContent ?? "", "<br>") +
      "<br>" +
      definition.replace(/\n/g, "<br>");
  }
  pycmd(CMD.sendToField(dictName, text));
  showToast("Sent to field");
}

function getImageForField(ev: Event, _dictName: string): void {
  const target = ev.target as HTMLElement;
  const termTitle = target.closest(".termPronunciation") as HTMLElement | null;
  if (!termTitle) return;
  const defBlock = termTitle.nextElementSibling as HTMLElement | null;
  if (!defBlock) return;
  const urls = collectSelectedImageUrls(defBlock);
  if (urls.length > 0) {
    pycmd(CMD.sendImgToField(urls));
    showToast("Images sent to field");
  }
}

function sendToField(ev: Event, dictName: string): void {
  if (dictName === "Images") getImageForField(ev, dictName);
  else getDefForField(ev, dictName);
}

// ── navigation ─────────────────────────────────────

function navigateDict(ev: Event, next: boolean, def = false): void {
  const target = ev.target as HTMLElement;
  const start = target.parentElement?.parentElement?.parentElement as
    | HTMLElement
    | null;
  if (!start) return;
  navigate(start, next, def ? "termPronunciation" : "dictionaryTitleBlock");
}

function navigateDef(ev: Event, next: boolean): void {
  navigateDict(ev, next, true);
}

// ── images ─────────────────────────────────────────

function loadMoreImages(tile: HTMLElement, term: string): void {
  const reset = (): void => {
    const icon = tile.querySelector(".loadMoreIcon");
    const text = tile.querySelector(".loadMoreText");
    if (icon) icon.textContent = "+";
    if (text) text.textContent = "Load More";
    tile.classList.remove("loading");
  };
  try {
    tile.classList.add("loading");
    const icon = tile.querySelector(".loadMoreIcon");
    const text = tile.querySelector(".loadMoreText");
    if (icon) icon.textContent = "...";
    if (text) text.textContent = "Loading";
    if (typeof window.pycmd === "function") {
      pycmd(CMD.getMoreImages(term));
    } else {
      console.error("pycmd not available");
      reset();
    }
  } catch (err) {
    console.error("Error in loadMoreImages:", err);
    reset();
  }
}

function toggleImageSelect(element: HTMLElement): void {
  try {
    const imgBox = element.closest(".imgBox");
    if (!imgBox) return;
    if (imgBox.classList.contains("selected")) {
      imgBox.classList.remove("selected");
      element.classList.remove("selectedImage");
      element.style.background = "";
    } else {
      imgBox.classList.add("selected");
      element.classList.add("selectedImage");
    }
  } catch (err) {
    console.error("Error in toggleImageSelect:", err);
  }
}

/** Inject image result HTML into a placeholder block, e.g. `#gcon<ts>`. */
export function loadImageHtml(html: string, idName: string): void {
  const target = document.getElementById(idName);
  if (target) {
    target.innerHTML = html;
    // The "Loading..." state is over once real content arrives.
    target.classList.remove("is-loading");
  } else {
    console.warn("Target element not found:", idName);
  }
}

/** Append more image boxes to the existing gallery (legacy load-more path). */
export function appendNewImages(html: string): void {
  try {
    const container = document.querySelector(".imageCont.horizontal-layout");
    if (!container) {
      console.error("Image container not found");
      return;
    }
    const scrollContainer =
      container.closest<HTMLElement>("#defBox") ?? container.parentElement;
    const currentScrollTop = scrollContainer ? scrollContainer.scrollTop : 0;

    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = html;
    const newImages = tempDiv.querySelectorAll(".imgBox");

    container.querySelector(".imageLoader")?.remove();

    newImages.forEach((img, index) => {
      (img as HTMLElement).style.animationDelay = `${(index + 1) * 0.1}s`;
      container.appendChild(img);
    });

    // Re-add a fresh load-more tile, preserving the term from the old one.
    const loadMoreTile = document.createElement("div");
    loadMoreTile.className = "imgBox imageLoader";
    loadMoreTile.innerHTML =
      '<div class="imageHighlight"></div><div class="loadMoreIcon">+</div><div class="loadMoreText">Load More</div>';
    const existingTile = document.querySelector(".imageLoader");
    const match = existingTile
      ?.getAttribute("onclick")
      ?.match(/loadMoreImages\(this,\s*['"](.+?)['"]\)/);
    if (match) {
      loadMoreTile.setAttribute(
        "onclick",
        `loadMoreImages(this, '${match[1]}')`,
      );
    }
    container.appendChild(loadMoreTile);

    if (scrollContainer) {
      scrollContainer.style.overflowY = "auto";
      scrollContainer.style.overflowX = "hidden";
      scrollContainer.scrollTop = currentScrollTop;
    }
  } catch (err) {
    console.error("Error in appendNewImages:", err);
  }
}

// ── audio (Forvo) ──────────────────────────────────

function playAudio(url: string): void {
  if (url) pycmd(CMD.playAudio(url));
}

function ankiAudioExport(word: string, url: string): void {
  if (word && url) pycmd(CMD.audioExport(word, url));
}

function sendAudioToField(url: string): void {
  if (url) pycmd(CMD.sendAudioToField(url));
}

function showMoreForvo(btn: HTMLElement): void {
  const container = btn.parentElement;
  if (!container) return;
  container.querySelectorAll<HTMLElement>(".forvo-extra").forEach((item) => {
    item.style.display = "flex";
  });
  btn.style.display = "none";
}

function animateForvoPlay(btn: HTMLElement): void {
  if (!btn) return;
  document
    .querySelectorAll(".forvo-playing")
    .forEach((el) => el.classList.remove("forvo-playing"));
  btn.classList.add("forvo-playing");
  setTimeout(() => btn.classList.remove("forvo-playing"), 2500);
}

// ── field / overwrite dropdowns ────────────────────

function closeAllDropdowns(): void {
  document
    .querySelectorAll(".open")
    .forEach((el) => el.classList.remove("open"));
  document
    .querySelectorAll(".has-open-dropdown")
    .forEach((el) => el.classList.remove("has-open-dropdown"));
  document.body.classList.remove("dropdown-open");
}

function showCheckboxes(ev: Event): void {
  try {
    ev.stopPropagation();
    const target = ev.target as HTMLElement;
    const container = target.closest<HTMLElement>(
      ".fieldSelectCont, .overwriteSelectCont",
    );
    if (!container) return;
    const isOpen = container.classList.contains("open");
    closeAllDropdowns();
    if (!isOpen) {
      container.classList.add("open");
      container
        .closest(".dictionaryTitleBlock")
        ?.classList.add("has-open-dropdown");
      container.closest(".mainDictDisplay")?.classList.add("has-open-dropdown");
      container.closest(".tabContent")?.classList.add("has-open-dropdown");
      document.body.classList.add("dropdown-open");
    }
  } catch (err) {
    console.error("Error in showCheckboxes:", err);
  }
}

function collectCheckedFields(container: HTMLElement): string[] {
  const checkboxes = container.querySelectorAll<HTMLInputElement>(
    'input[type="checkbox"]:checked',
  );
  return Array.from(checkboxes).map((cb) => cb.value);
}

function handleFieldCheck(checkbox: HTMLInputElement): void {
  try {
    const container = checkbox.closest<HTMLElement>(".fieldCheckboxes");
    if (!container) return;
    const dictName = container.getAttribute("data-dictname");
    if (dictName) {
      pycmd(CMD.fieldsSetting(dictName, collectCheckedFields(container)));
    }
  } catch (err) {
    console.error("Error in handleFieldCheck:", err);
  }
}

/** Same as handleFieldCheck but also updates the compact count label. */
function handleFieldCheckbox(checkbox: HTMLInputElement): void {
  const container = checkbox.closest<HTMLElement>(".fieldCheckboxes");
  if (!container) return;
  const dictName = container.getAttribute("data-dictname");
  const selected = collectCheckedFields(container);
  const selectDiv = container.previousElementSibling as HTMLElement | null;
  if (selectDiv && selectDiv.classList.contains("fieldSelect")) {
    selectDiv.innerHTML =
      selected.length > 0
        ? `&nbsp;${selected.length} Selected`
        : "&nbsp;Select Fields ▾";
  }
  if (dictName) pycmd(CMD.fieldsSetting(dictName, selected));
}

function handleAddTypeCheck(radio: HTMLInputElement): void {
  try {
    const dictName = radio.className.match(/radio([^\s]+)/)?.[1];
    if (!dictName) return;
    pycmd(CMD.overwriteSetting(dictName, radio.value));
  } catch (err) {
    console.error("Error in handleAddTypeCheck:", err);
  }
}

function filterFieldOptions(input: HTMLInputElement): void {
  const filter = input.value.toLowerCase();
  const container = input.closest<HTMLElement>(".fieldCheckboxes");
  if (!container) return;
  container
    .querySelectorAll<HTMLElement>(".fieldCheckboxLabel")
    .forEach((label) => {
      label.style.display = (label.textContent ?? "").toLowerCase().includes(filter)
        ? ""
        : "none";
    });
}

// ── sidebar resize ─────────────────────────────────

let hresizeInt: number | undefined;
let mouseX = 0;
let resizing = false;

document.addEventListener("mousemove", (e) => {
  mouseX = e.pageX;
});

function hresize(_ev: Event): void {
  const userSelect = document.getElementById("userSelect");
  if (userSelect) {
    userSelect.textContent =
      "body{-webkit-touch-callout: none;  -webkit-user-select: none;-khtml-user-select: none;-moz-user-select: none;-ms-user-select: none;user-select: none;}";
  }
  resizing = true;
  hresizeInt = window.setInterval(() => {
    const ws = document.getElementById("widthSpecs");
    if (ws) {
      ws.textContent = `.sidebarOpenedDisplay{margin-left:${mouseX}px !important;}.sidebarOpenedSideBar{width:${mouseX}px;}`;
    }
  }, 10);
}

function stopResize(): void {
  window.clearInterval(hresizeInt);
  hresizeInt = undefined;
  const userSelect = document.getElementById("userSelect");
  if (userSelect) userSelect.textContent = "";
  if (!resizing) return;
  resizing = false;
  const ws = document.getElementById("widthSpecs");
  if (!ws) return;
  let width = mouseX;
  if (width > window.innerWidth) width = window.innerWidth - 20;
  if (width < 20) width = 20;
  ws.textContent =
    `.sidebarOpenedDisplay{margin-left:${width}px !important;}.sidebarOpenedSideBar{width:${width}px;}`;
  // Persist so the width survives a dictionary reopen.
  pycmd(CMD.saveSidebarWidth(width));
}

window.addEventListener("mouseup", stopResize);

// ── fonts ──────────────────────────────────────────

/** Inject an @font-face for languages that need a bundled font file. */
export function addCustomFont(fontFile: string, fontName: string): void {
  try {
    const style = document.createElement("style");
    style.textContent = `
            @font-face {
                font-family: '${fontName}';
                src: url('${fontFile}');
            }
        `;
    document.head.appendChild(style);
  } catch (err) {
    console.error("Error adding custom font:", err);
  }
}

// ── expose on window (content-level compat) ────────

export function initCompatGlobals(): void {
  const w = window as unknown as Record<string, unknown>;
  Object.assign(w, {
    ankiExport,
    clipText,
    sendToField,
    navigateDict,
    navigateDef,
    loadMoreImages,
    toggleImageSelect,
    loadImageHtml,
    appendNewImages,
    playAudio,
    ankiAudioExport,
    sendAudioToField,
    showMoreForvo,
    animateForvoPlay,
    closeAllDropdowns,
    showCheckboxes,
    handleFieldCheck,
    handleFieldCheckbox,
    handleAddTypeCheck,
    filterFieldOptions,
    hresize,
    stopResize,
    addCustomFont,
    getSelectionText,
    cleanTermDef,
    getMainWords,
  });
}