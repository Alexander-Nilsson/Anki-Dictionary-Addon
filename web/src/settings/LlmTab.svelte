<script lang="ts">
  import { settings, testLLM } from "../lib/settings.svelte";

  const cfg = {
    get: (k: string, d: unknown) => settings.dirty[k] ?? d,
    set: (k: string, v: unknown) => {
      settings.dirty[k] = v;
      settings.dirty = settings.dirty;
    },
  };

  interface PromptRow {
    text: string;
    active: boolean;
  }

  function prompts(): PromptRow[] {
    const raw = cfg.get("llm_prompts", null);
    if (Array.isArray(raw)) {
      return (raw as unknown[]).map((p) => {
        if (typeof p === "string") return { text: p, active: true };
        const o = p as { text?: string; active?: boolean };
        return { text: o.text ?? "", active: o.active ?? true };
      });
    }
    const single = cfg.get("llm_prompt", "Provide a concise dictionary definition for the word: {term}");
    return [{ text: single as string, active: true }];
  }

  let rows = $state<PromptRow[]>(prompts());

  function addRow(): void {
    rows = [...rows, { text: "", active: true }];
  }
  function removeRow(i: number): void {
    if (rows.length <= 1) return;
    rows = rows.filter((_, idx) => idx !== i);
  }
  function syncRows(): void {
    cfg.set("llm_prompts", rows);
    const first = rows.find((r) => r.active && r.text.trim())?.text ?? "";
    cfg.set("llm_prompt", first);
  }
</script>

<div class="card">
  <h3>LLM Configuration</h3>
  <p class="hint">
    Configure an OpenAI-compatible LLM to get AI-generated definitions.
  </p>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("llm_enabled", false)} onchange={(e) => cfg.set("llm_enabled", e.currentTarget.checked)} />
    Enable LLM Dictionary
  </label>
  <div class="field">
    <label for="llmApiKey">API Key</label>
    <input id="llmApiKey" type="password" value={cfg.get("llm_api_key", "")} oninput={(e) => cfg.set("llm_api_key", e.currentTarget.value)} />
  </div>
  <div class="field">
    <label for="llmBaseUrl">Base URL</label>
    <input id="llmBaseUrl" type="text" value={cfg.get("llm_base_url", "https://api.openai.com/v1/chat/completions")} oninput={(e) => cfg.set("llm_base_url", e.currentTarget.value)} />
  </div>
  <p class="hint">
    Supports Ollama (e.g. http://localhost:11434/api/chat) or OpenAI-style endpoints.
  </p>
  <div class="field">
    <label for="llmModel">Model</label>
    <input id="llmModel" type="text" value={cfg.get("llm_model", "gpt-3.5-turbo")} oninput={(e) => cfg.set("llm_model", e.currentTarget.value)} />
  </div>
  <div class="field">
    <label for="llmTemp">Temperature</label>
    <input id="llmTemp" type="number" step="0.1" min="0" max="2" value={Number(cfg.get("llm_temperature", 0.3))} oninput={(e) => cfg.set("llm_temperature", Number(e.currentTarget.value))} />
  </div>
  <div class="field">
    <label for="llmKeepAlive">Keep Alive</label>
    <input id="llmKeepAlive" type="text" value={cfg.get("llm_keep_alive", "30m")} oninput={(e) => cfg.set("llm_keep_alive", e.currentTarget.value)} />
  </div>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("llm_think", false)} onchange={(e) => cfg.set("llm_think", e.currentTarget.checked)} />
    Enable Thinking
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("llm_stream", false)} onchange={(e) => cfg.set("llm_stream", e.currentTarget.checked)} />
    Enable Streaming
  </label>
  <label class="check">
    <input type="checkbox" checked={!!cfg.get("llm_get_pronunciation", false)} onchange={(e) => cfg.set("llm_get_pronunciation", e.currentTarget.checked)} />
    Get pronunciation from first dictionary entry
  </label>
</div>

<div class="card">
  <h3>Prompt Templates</h3>
  <p class="hint">
    Each prompt becomes a separate request. Responses are joined as independent
    definitions. Use {"{term}"} as a placeholder for the word being searched.
  </p>
  {#each rows as row, i (i)}
    <div class="field">
      <input
        type="checkbox"
        aria-label="Enable prompt"
        checked={row.active}
        onchange={(e) => { rows[i] = { ...row, active: e.currentTarget.checked }; }}
      />
      <textarea
        rows="3"
        value={row.text}
        placeholder={"Prompt text — use {term} as the placeholder for the word being searched"}
        oninput={(e) => { rows[i] = { ...row, text: e.currentTarget.value }; }}
      ></textarea>
      <button type="button" class="btn danger" onclick={() => removeRow(i)} title="Remove prompt">&#x2715;</button>
    </div>
  {/each}
  <button type="button" class="btn" onclick={addRow}>+ Add Prompt</button>
</div>

<div class="card">
  <h3>Test Connection</h3>
  <div style="display:flex;gap:10px;align-items:center">
    <button type="button" class="btn primary" disabled={settings.llmTestPending} onclick={() => { syncRows(); testLLM(); }}>
      {settings.llmTestPending ? "Testing…" : "Test API Connection"}
    </button>
    {#if settings.llmTest}
      <span class:status={true} class:ok={settings.llmTest.ok} class:bad={!settings.llmTest.ok}>
        {settings.llmTest.message}
      </span>
    {/if}
  </div>
</div>
