<script lang="ts">
  import { settings, deleteWordList } from "../lib/settings.svelte";
  import type { WordListProvider } from "../lib/settings.svelte";

  const cfg = {
    get: (k: string, d: unknown) => settings.dirty[k] ?? d,
    set: (k: string, v: unknown) => {
      settings.dirty[k] = v;
      settings.dirty = settings.dirty;
    },
  };

  const DEFAULT_DISPLAY_NAMES: Record<string, string> = {
    hsk: "HSK³",
    jlpt: "JLPT",
    cefr: "CEFR",
  };

  function thresholds(): number[] {
    const t = cfg.get("star_thresholds", [1501, 5001, 15001, 30001, 60001]);
    return Array.isArray(t) ? (t as number[]) : [1501, 5001, 15001, 30001, 60001];
  }

  let thresh = $state<number[]>(thresholds());
  function setThreshold(i: number, v: number): void {
    thresh[i] = v;
    cfg.set("star_thresholds", [...thresh]);
  }

  function displayNameFor(name: string): string {
    const lower = name.toLowerCase();
    for (const [k, v] of Object.entries(DEFAULT_DISPLAY_NAMES)) {
      if (lower.includes(k)) return v;
    }
    return name;
  }

  function providerRoles(): Record<string, string> {
    const r = cfg.get("provider_roles", {});
    return typeof r === "object" && r ? (r as Record<string, string>) : {};
  }
  function roleFor(key: string): string {
    return providerRoles()[key] ?? "off";
  }
  function setRole(key: string, role: string): void {
    const r = providerRoles();
    r[key] = role;
    cfg.set("provider_roles", r);
  }

  function displayNames(): Record<string, Record<string, string>> {
    const d = cfg.get("word_list_display_names", {});
    return typeof d === "object" && d ? (d as Record<string, Record<string, string>>) : {};
  }
  function displayNameForProvider(p: WordListProvider): string {
    return displayNames()[p.lang]?.[p.name] ?? displayNameFor(p.name);
  }
  function setDisplayName(p: WordListProvider, value: string): void {
    const all = displayNames();
    const v = value.trim();
    if (!v || v === displayNameFor(p.name)) {
      delete all[p.lang]?.[p.name];
    } else {
      all[p.lang] = { ...(all[p.lang] ?? {}), [p.name]: v };
    }
    cfg.set("word_list_display_names", all);
  }

  const RANK_ROLES = [
    { value: "stars_rank", label: "Stars + Rank" },
    { value: "stars", label: "Stars only" },
    { value: "rank", label: "Rank only" },
    { value: "off", label: "Off" },
  ];
  const LEVEL_ROLES = [
    { value: "level", label: "Level" },
    { value: "off", label: "Off" },
  ];

  const rankProviders = $derived(settings.providers.filter((p) => p.type === "rank"));
  const levelProviders = $derived(settings.providers.filter((p) => p.type === "level"));

  // ── Live preview ─────────────────────────────────────────────
  // Mirrors the old PyQt tab: renders the star/rank/level bits that would
  // appear next to an example entry, driven by the current settings.
  const MOCK_FREQS = [1501, 4000, 12000, 28000, 55000, 120000];

  function starChart(count: number): string {
    return String(cfg.get("star_char", "★")).repeat(count);
  }

  function formatFreqK(freq: number): string {
    if (freq >= 10000) return `${Math.floor(freq / 1000)}k`;
    const whole = Math.floor(freq / 1000);
    const frac = Math.floor((freq % 1000) / 100);
    return frac ? `${whole}.${frac}k` : `${whole}k`;
  }

  const preview = $derived.by(() => {
    const showStars = !!cfg.get("show_stars", true);
    const showRank = !!cfg.get("show_rank", false);
    const showLabels = !!cfg.get("show_level_labels", true);
    const thresholds = thresh;
    const roles = providerRoles();

    let idx = 0;
    let starFreq: number | null = null;
    const ranks: string[] = [];
    const levels: string[] = [];

    for (const p of [...settings.providers].sort((a, b) => a.key.localeCompare(b.key))) {
      const role = roles[p.key] ?? "off";
      if (role === "off") continue;
      const mock = MOCK_FREQS[Math.min(idx, MOCK_FREQS.length - 1)];
      idx += 1;
      if (p.type === "rank") {
        if (role === "stars_rank" || role === "stars") {
          if (starFreq === null || mock < starFreq) starFreq = mock;
        }
        if ((role === "stars_rank" || role === "rank") && showRank) {
          ranks.push(formatFreqK(mock));
        }
      } else if (p.type === "level" && role === "level" && showLabels) {
        levels.push(`${displayNameForProvider(p)}:N3`);
      }
    }

    const stars =
      showStars && starFreq !== null
        ? starChart(getStarCountStars(starFreq, thresholds))
        : "";
    return { stars, ranks, levels };
  });

  function getStarCountStars(freq: number, thresholds: number[]): number {
    if (freq < thresholds[0]!) return 5;
    if (freq < thresholds[1]!) return 4;
    if (freq < thresholds[2]!) return 3;
    if (freq < thresholds[3]!) return 2;
    if (freq < thresholds[4]!) return 1;
    return 0;
  }
</script>

<div class="card">
  <h3>Preview</h3>
  <p class="hint">
    Preview of how frequency stars, rank, and level labels will render.
  </p>
  <div class="freq-preview">
    <span class="preview-word">例文</span>
    <span class="preview-reading">れいぶん</span>
    {#if preview.stars}
      <span class="preview-stars">{preview.stars}</span>
    {/if}
    {#each preview.ranks as r (r)}
      <span class="preview-rank">[{r}]</span>
    {/each}
    {#each preview.levels as l (l)}
      <span class="preview-level">{l}</span>
    {/each}
    {#if preview.stars === "" && preview.ranks.length === 0 && preview.levels.length === 0}
      <span class="preview-empty">Nothing to show yet — enable stars, rank, or level labels above.</span>
    {/if}
  </div>
</div>

<div class="card">
  <h3>Rank (Frequency) Lists</h3>
  <p class="hint">
    Smaller rank number = more common word. Displayed as e.g. 1.5k
    (= 1,500th most common).
  </p>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("show_stars", true)} onchange={(e) => cfg.set("show_stars", e.currentTarget.checked)} />
    Display Stars
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("show_rank", false)} onchange={(e) => cfg.set("show_rank", e.currentTarget.checked)} />
    Display Frequency Rank
  </label>

  {#if rankProviders.length > 0}
    {#each rankProviders as p (p.key)}
      <div class="field">
        <select value={roleFor(p.key)} onchange={(e) => setRole(p.key, e.currentTarget.value)}>
          {#each RANK_ROLES as r (r.value)}
            <option value={r.value}>{r.label}</option>
          {/each}
        </select>
        <span class="grow">{p.lang}: {p.name}</span>
        <input type="text" style="width:150px" value={displayNameForProvider(p)} placeholder={displayNameFor(p.name)} onchange={(e) => setDisplayName(p, e.currentTarget.value)} />
      </div>
    {/each}
  {:else}
    <p class="hint">No rank-based word lists found for your languages.</p>
  {/if}
</div>

<div class="card">
  <h3>Level Lists</h3>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("show_level_labels", true)} onchange={(e) => cfg.set("show_level_labels", e.currentTarget.checked)} />
    Display Level Labels
  </label>
  {#if levelProviders.length > 0}
    {#each levelProviders as p (p.key)}
      <div class="field">
        <select value={roleFor(p.key)} onchange={(e) => setRole(p.key, e.currentTarget.value)}>
          {#each LEVEL_ROLES as r (r.value)}
            <option value={r.value}>{r.label}</option>
          {/each}
        </select>
        <span class="grow">{p.lang}: {p.name}</span>
        <input type="text" style="width:150px" value={displayNameForProvider(p)} placeholder={displayNameFor(p.name)} onchange={(e) => setDisplayName(p, e.currentTarget.value)} />
      </div>
    {/each}
  {:else}
    <p class="hint">No level-based word lists found for your languages.</p>
  {/if}
</div>

<div class="card">
  <h3>Star Configuration</h3>
  <div class="field">
    <label for="starChar">Star Character</label>
    <input id="starChar" type="text" maxlength="2" style="width:60px" value={String(cfg.get("star_char", "★"))} oninput={(e) => cfg.set("star_char", e.currentTarget.value)} />
  </div>
  <div class="field">
    <span class="field-label" id="threshLabel">Rank Thresholds</span>
    <div style="flex:1;display:flex;gap:6px" role="group" aria-labelledby="threshLabel">
      {#each thresh as t, i (i)}
        <input type="number" min="0" style="flex:1" value={t} oninput={(e) => setThreshold(i, Number(e.currentTarget.value))} />
      {/each}
    </div>
  </div>
  <p class="hint">Rank thresholds for 5, 4, 3, 2, and 1 star(s) respectively.</p>
</div>

<div class="card">
  <h3>Installed Word List Files</h3>
  {#each settings.wordListFiles as langGroup (langGroup.lang)}
    <details>
      <summary><strong>{langGroup.lang}</strong> ({langGroup.files.length})</summary>
      <div class="list">
        {#each langGroup.files as f (f.name)}
          <div class="list-row">
            <span class="name">{f.name}</span>
            <span class="sub">{f.type}</span>
            <span class:status={true} class:bad={f.status !== "ok"}>{f.status}</span>
            <button
              type="button"
              class="btn danger"
              onclick={() => {
                if (confirm(`Delete "${f.name}"? This cannot be undone.`)) deleteWordList(f.name);
              }}
            >
              Delete
            </button>
          </div>
        {/each}
      </div>
    </details>
  {/each}
  {#if settings.wordListFiles.length === 0}
    <p class="hint">No word list files installed.</p>
  {/if}
</div>
