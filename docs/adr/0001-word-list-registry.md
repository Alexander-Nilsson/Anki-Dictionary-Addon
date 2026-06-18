# WordListRegistry — unified seam for all rank and level data

**Status:** accepted

Frequency-rank and word-level data was split across `frequency/` and `hsk/` directories with separate loading paths,
Chinese-language detection, and hardcoded HSK display logic. Users could not add custom word lists without editing code.

We decided to consolidate all word-list data into a `word_lists/` directory behind a single `WordListRegistry` module.
The registry exposes `Provider` objects with a `.lookup(term, reading)` interface that abstracts over two preserved
formats (simple dict and compound list). Type discrimination (rank vs level) comes from the server `index.json` section
name — `frequency_lists` for rank, `word_lists` for level. The `frequency_url` key is removed from the server index.

**Considered Options**

- **Explicit `type` field** in each index entry — rejected in favour of section names, which keep the server index simpler
  and avoid duplication (every entry in `frequency_lists` is rank, every entry in `word_lists` is level)
- **Normalising all formats to one dict** — rejected; the compound format carries readings and multiple levels per term
  that are useful for display and would be lost in flattening
- **Keeping the legacy split** — rejected because each new word-list type (JLPT, TOPIK, TOCFL, Wanikani) would
  require a new loading path and new settings UI code

**Consequences**

- Old `frequency/` and `hsk/` directories are migrated once on first load (copy then delete originals)
- Per-list visibility checkboxes replace single `show_hsk` toggle in settings
- `entry["hskLevel"]` renamed to `entry["levelLabels"]` (type `list[str]`); CSS class `.hsk-level` → `.level-label`
- Conjugation data stays in `conjugation/` — it is grammar inflection rules, not word-level metadata
