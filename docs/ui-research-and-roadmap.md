# UI & Addon Improvement Research — 2026-09-04

Research into how the dictionary UI and the addon overall could look and work
better, with a prioritized roadmap. Companion to the interactive prototype at
[`web/prototype/ui-variants.html`](../web/prototype/ui-variants.html) (4 modes,
open in any browser, `?variant=` + floating bar to switch).

---

## 1. Method

Audited the live codebase (web shell, Qt chrome, settings, history, async
services), the shipped config, and external references (Yomitan + community
CSS themes, Migaku popup, modern read-it-later UIs). No code was changed —
this is analysis + a throwaway prototype.

## 2. Current state — what exists today

**Web shell (Svelte 5, Phase 2 structured doc):**

| Area | How it works today |
|---|---|
| Results | Flat sibling blocks: `dictionaryTitleBlock` → `termPronunciation`(s) → `definitionBlock`(s), per dictionary. Entries carry stars / rank `[3k]` / JLPT levels as inline spans. |
| Styles | `legacy.css` (1,200+ lines inherited verbatim from the old `dictionary.html`) + thin `app.css`. All components style against legacy selectors. |
| Tools | Per-entry `defTools`: text-glyph buttons (`⇩ ✂ ➞ ▲ ▼`) rendered by Python, plus per-dictionary title-block dropdowns (override mode / target fields). |
| Sidebar | `Sidebar.svelte` — dictionary list + matched terms, resize bar, scrollspy pairing (fixed in Phase 2 slice 1). |
| Async | Images / LLM / Forvo render as opaque `<LoaderBlock>` placeholder `{@html}` until the Python side injects content (`loadImageHtml`, `appendNewImages`, …). |
| Feedback | `Toaster` for copy / send-to-field / export confirmation; toasts auto-dismiss in 1.8 s. |
| No-results | Icon + message, centered via `.vertical-center`. |

**Qt chrome (native, around the web view):** toolbar with ~10 small buttons
(dict group combo, search mode combo, **100 px search field**, search button,
sidebar toggle, font −/+, one-tab toggle, history browser, conjugation toggle,
theme, settings). History lives in a separate Qt dialog (`HistoryBrowser`)
backed by `_searchHistory.json` in the media dir. Search itself is
`QLineEdit.returnPressed → initSearch`.

**Async services:** DuckDuckGo images, LLM summary, Forvo audio — all
background-threaded, injected into the web view when ready.

**Settings:** PyQt6 tabbed dialog — dict groups (+ per-dict fonts), frequency,
LLM, Forvo, export templates, theme editor, dictionary manager/import wizard.

## 3. Friction points found (grounded)

### Visual (web shell)
1. **Text-glyph tool buttons** (`⇩ ✂ ➞ ▲ ▼`) are uneven, tiny, and rasterize
   badly on HiDPI; no hit-area padding, no hover affordance beyond a color
   change (renderer emits them, `legacy.css` styles them).
2. **Every entry shows its tools simultaneously** — 5 glyphs × N entries = a
   noisy column; actions only matter for the entry the user is looking at.
3. **Dictionary headers are not sticky** — scroll two screens deep and you
   lose which dictionary/entry you're in.
4. **Loading states are text** ("Loading images…", "thinking…") in `LoaderBlock`
   — no visual progress, no skeletons, no error/duration info.
5. **Badges are plain inline spans** — stars/rank/JLPT levels are the most
   informative data in the header and have the least visual weight.
6. **Two stylesheets** — `legacy.css` carries hardcoded colors/spacing from the
   old template; CSS variables only partially cover the shell. Debt grows with
   every Svelte component that matches legacy selectors.
7. **No "back to top"**, no expand/collapse for long definitions, no way to
   jump to a dictionary from the sidebar (sidebar entries are for terms, and
   they're scrollspy — not clickable to navigate).

### Workflow (addon overall)
8. **Search field is a 100 px Qt `QLineEdit`** — cramped, no history
   autocomplete, no global shortcut, and it lives *outside* the web view, so
   the two halves of the workflow ("type here, read there") are visually
   disconnected.
9. **History is a separate Qt dialog** — not discoverable from the web UI;
   no re-search-from-history in context; JSON file never pruned.
10. **No-results is a dead end** — no "did you mean", no deinflection hint
    (deinflect exists but is buried in the toolbar), no example searches.
11. **No search-source feedback** — clipboard monitoring (ClipThread) drives a
    lot of searches; the UI doesn't say *why* a search happened or let you
    pause it in place.
12. **Unused chrome in the Qt toolbar overlaps with web features** — once the
    web shell matures, several toolbar buttons (font size, theme, search mode)
    could live in the web view itself.
13. **Settings is a big tabbed dialog** with no search — frequency settings
    alone is a table of per-dictionary rows; finding a setting is slow.

### Addon-level / infra
14. **All tabs stay in the DOM** — inactive tabs are `display:none` but keep
    their image grids/LLM text; many searches → memory creep in the web view.
15. **Scrollspy listens to every scroll event** (added a document-level scroll
    listener in Phase 2) — cheap now, worth an `IntersectionObserver` once the
    doc gets bigger.
16. **Onboarding is a static welcome template** — users don't know the addon
    can watch the clipboard, export cards, or search images until they find it
    in settings/docs.
17. **No session restore** — close the dictionary window and your 6 open tabs
    are gone (`dictOnStart` only reopens the window).
18. **Accessibility gaps** — image tiles and several tool glyphs lack
    keyboard interaction/`aria-label` parity (Phase 1 fixed a batch of these).

## 4. External inspiration

- **Yomitan** — community CSS themes ("make it yours") prove users will
  restyle aggressively; tag pills (frequency/JLPT) and inline audio replay are
  the pattern our header badges are converging on.
- **Yomitan/Migaku popups** — actions live in a footer/overflow menu, not
  scattered beside the term; density is high but scannable.
- **Read-it-later apps** (Readwise/Omnivore) — focus/reader modes show that a
  single centered column with keyboard-first actions feels calmer than a
  toolbar-heavy surface.

## 5. Roadmap (prioritized)

### Quick wins — web-only, low risk, high visible value
- **QW1 SVG action icons + hover-reveal**: replace glyph tools with an SVG
  icon set, group into a hover-reveal action cluster (icons inherit current
  color, scale on HiDPI). Small Python change (renderer emits SVG) + CSS.
- **QW2 Sticky dictionary headers + back-to-top**: `position: sticky` on the
  title block with a blurred backdrop; floating back-to-top button after
  ~2 viewport heights.
- **QW3 Skeleton loaders for Images/LLM/Forvo**: replace `LoaderBlock` text
  with a shimmer placeholder; keep the `{@html}` contract — swap the placeholder
  markup only. (Already demonstrated in the prototype.)
- **QW4 Badge pills + example cards**: restyle stars/rank/levels as pills with
  tooltips; style example sentences as an indented card under the sense.
- **QW5 Collapse long definitions**: max-height + "expand" toggle on the
  definition block (opt-in via config?).

### Next — workflow
- **U1 Search box in the web view**: the biggest UX win. A slim chrome strip
  (search field + group select + theme toggle) inside the web shell. New
  bridge command `searchTerm:<term>` routes to the existing `initSearch`;
  history autocomplete driven by the same `_searchHistory.json`. Global
  shortcut (Ctrl/⌘+K or `/`) focuses it.
- **U2 Search source + pause pill**: "searched from clipboard/browser/field"
  chip + one-click pause for clipboard snooping.
- **U3 History in the sidebar**: recent searches (with dates), click to
  re-search, prune button; replaces/augments the Qt dialog.
- **U4 No-results suggestions**: fuzzy "did you mean", deinflection hint,
  example searches.
- **U5 Keyboard map**: Tab/arrows for dictionary & entry nav, E=export,
  C=copy, ?=cheat sheet (currently all actions are mouse-first).

### Addon-level
- **A1 Settings search** — filter tabs + fields, highlight matches.
- **A2 First-run onboarding** — 3-step guide in the welcome screen (search /
  export a card / image search), dismissible, with a "try it" button.
- **A3 Lazy tabs + pruning** — render inactive tabs on activation;
  LRU cap with a close-toast; debounce/IO-based scrollspy.
- **A4 History pruning** (keep last N entries) + search-in-history.
- **A5 Session restore** — persist open tabs, restore on `dictOnStart`.
- **A6 Legacy CSS de-debt** — after full compat removal (Phase 3), move
  remaining hardcoded values into CSS variables; trim dead rules.

## 6. The prototype

`web/prototype/ui-variants.html` — open directly in a browser (no build):

```
xdg-open web/prototype/ui-variants.html            # defaults to ?variant=baseline
xdg-open "web/prototype/ui-variants.html?variant=c" # jump straight to a mode
```

Four modes, switched with the floating bar (or ←/→ when not typing):

| Mode | Idea |
|---|---|
| **Baseline** | Faithful recreation of today's view. The in-web chrome strip shown above it is *proposed* — search currently lives in the Qt toolbar. |
| **A — Refined** | Same structure, polished: sticky headings, hover-reveal SVG actions, badge pills, skeleton loaders, example cards, back-to-top. |
| **B — Split panels** | Dictionary tabs + entry cards on the left; a right media rail (Images/LLM/Forvo) with inline audio. |
| **C — Focus** | Keyboard-first reader: big term hero, centered cards, image strip, shortcut cheat sheet. |

Interactions wired: search field (Enter toasts a mock result, history
autocomplete with ↑/↓), theme toggle (dark/light), working copy button,
skeleton→image hydration, sticky behavior, back-to-top.

Screenshots of each mode are at `build/proto-{baseline,a,b,c}.png` (generated
by the harness in `/tmp/opencode/check_proto_ui.py`, `build/` is gitignored).

## 7. Suggested next step

Recommendation: ship **QW1–QW4 + U1** as one "polish" slice — it's almost
entirely web-shell work on the existing doc architecture (no Python contract
changes except the renderer emitting SVG/placeholder markup and one new bridge
command), and it's demoable end-to-end in the existing harness.

Open questions for the user:

1. Which visual direction — **A (refined)**, **B (split panels)**, or **C
   (focus/reader)** — or a mix (e.g., A's polish + C's search chrome)?
2. Should the in-web search chrome replace the Qt toolbar search field, or
   coexist with it?
3. Scope: quick wins only (QW1–QW5), or include U1 (search-in-web) in the
   first slice?