<script lang="ts">
  import { ui } from "../lib/tabs.svelte";

  const shortcuts = [
    { keys: "? /", action: "Show or hide this keyboard map" },
    { keys: "E", action: "Export the current entry to Anki" },
    { keys: "C", action: "Copy the current entry to the clipboard" },
    { keys: "↑ / ↓", action: "Previous / next entry" },
    { keys: "Tab / ⇧+Tab", action: "Previous / next dictionary" },
    { keys: "Ctrl/⌘ + K", action: "Open the command palette" },
    { keys: "/", action: "Focus the search box" },
    { keys: "Esc", action: "Close this help" },
  ];

  let backdrop: HTMLDivElement | undefined = $state();

  function close(): void {
    ui.showKeymap = false;
  }

  // The dialog takes focus on open so Escape/arrow handling is coherent even
  // before the user clicks inside (the global keymap also closes it via Esc).
  $effect(() => {
    if (ui.showKeymap) backdrop?.focus();
  });
</script>

{#if ui.showKeymap}
  <div
    bind:this={backdrop}
    class="keymap-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label="Keyboard shortcuts"
    tabindex="-1"
    onclick={(e) => {
      // Only the dimmed backdrop itself dismisses; clicks inside the card keep
      // the overlay open.
      if (e.target === e.currentTarget) close();
    }}
    onkeydown={(e) => {
      if (e.key === "Escape") close();
    }}
  >
    <div class="keymap-card">
      <h2>Keyboard shortcuts</h2>
      <table>
        <tbody>
          {#each shortcuts as s (s.keys)}
            <tr>
              <td class="keys"><kbd>{s.keys}</kbd></td>
              <td>{s.action}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      <button type="button" class="keymap-close" onclick={close}>
        Close
      </button>
    </div>
  </div>
{/if}