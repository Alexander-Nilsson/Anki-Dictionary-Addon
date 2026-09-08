/**
 * HTML entry headers for card export.
 *
 * By default the exporter ships plain-text headers (`tpCont.textContent`
 * stripped of tags), so frequency stars lose their golden badge styling.
 * When the `exportHeaderHtml` setting is on, these helpers build an HTML
 * header instead. Badge colors are inlined (rather than relying on the
 * dictionary page's CSS) so the formatting survives inside Anki notes,
 * whose card templates don't load the dictionary styles.
 */
import type { TermPronunciationBlockData } from "./types";

/** Golden star color — mirrors `.tpCont .starcount` in app.css/legacy.css. */
export const STAR_GOLD = "#e0a800";

/** Whether styled HTML headers are enabled (Python injects the flag). */
export function exportHeaderEnabled(): boolean {
  return (
    typeof window !== "undefined" && window.exportHeaderHtml === true
  );
}

function escAttr(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Add inline badge styling to a rendered `.tpCont` fragment.
 *
 * Used by the legacy/compat export paths, where the header already exists
 * as HTML (Python-rendered or Svelte-rendered) but the badge colors live in
 * page CSS. Star badges get the golden color; rank/level badges keep their
 * theme-relative look with a pill fallback that reads without the page CSS.
 */
export function inlineHeaderBadges(tpContHtml: string): string {
  const tpl = document.createElement("template");
  tpl.innerHTML = tpContHtml.trim();
  const badges = tpl.content.querySelectorAll(".starcount");
  for (const badge of Array.from(badges)) {
    const el = badge as HTMLElement;
    const cls = el.classList;
    const existing = el.getAttribute("style") ?? "";
    if (cls.contains("frequency-rank")) {
      if (!/font-weight/.test(existing)) {
        el.setAttribute(
          "style",
          `${existing}font-weight:600;`.replace(/^;/, ""),
        );
      }
    } else if (cls.contains("level-label")) {
      if (!/font-weight/.test(existing)) {
        el.setAttribute(
          "style",
          `${existing}font-weight:600;`.replace(/^;/, ""),
        );
      }
    } else if (!new RegExp(STAR_GOLD, "i").test(existing)) {
      el.setAttribute(
        "style",
        `${existing}color:${STAR_GOLD};font-weight:600;`.replace(/^;/, ""),
      );
    }
  }
  const wrap = document.createElement("div");
  wrap.appendChild(tpl.content);
  return wrap.innerHTML;
}

/**
 * HTML header for a structured entry block (Svelte shell).
 *
 * `headerHtml` is Python's highlighted headword fragment; stars/rank/levels
 * arrive as structured data, so the badges are serialized here with inline
 * styles included from the start.
 */
export function headerHtmlForExport(
  b: TermPronunciationBlockData,
): string {
  let html = b.headerHtml;
  if (b.stars) {
    const tip = b.starTip ? ` title="${escAttr(b.starTip)}"` : "";
    html +=
      ` <span class="starcount" style="color:${STAR_GOLD};` +
      `font-weight:600;"${tip}>${escAttr(b.stars)}</span>`;
  }
  if (b.rank) {
    const tip = b.rank.tip ? ` title="${escAttr(b.rank.tip)}"` : "";
    html +=
      ` <span class="starcount frequency-rank" style="font-weight:600;"${tip}>` +
      `${escAttr(b.rank.label)}</span>`;
  }
  if (b.levels) {
    for (const level of b.levels) {
      const tip = level.source ? ` title="${escAttr(level.source)}"` : "";
      html +=
        ` <span class="starcount level-label" style="font-weight:600;"${tip}>` +
        `${escAttr(level.label)}</span>`;
    }
  }
  return html;
}
