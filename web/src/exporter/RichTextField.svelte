<script lang="ts">
  /**
   * Contenteditable replacement for the Qt `MITextEdit`.
   *
   * Keeps the behaviours the Qt widget had: Ctrl+B / Ctrl+I / Ctrl+U toggle
   * inline formatting, Ctrl+S searches the selection in the dictionary and
   * Ctrl+F searches it in the Anki browser. Paste is forced to plain text —
   * the Qt widget had `setAcceptRichText(False)`, and pasted markup would
   * otherwise reach the note field verbatim.
   *
   * `value` is HTML owned by Python. It is written into the DOM only when it
   * differs from what the element already holds, so typing is never
   * interrupted by an echoed update.
   */
  import { exporter } from "../lib/exporter.svelte";

  interface Props {
    value: string;
    placeholder?: string;
    minHeight?: number;
    maxHeight?: number;
    fontSize?: string;
    onchange: (html: string) => void;
  }

  let {
    value,
    placeholder = "",
    minHeight = 60,
    maxHeight = 0,
    fontSize = "16px",
    onchange,
  }: Props = $props();

  let el: HTMLDivElement | null = $state(null);

  $effect(() => {
    // Depend on the revision too: a Python push of identical-looking HTML
    // after a clear still has to repaint.
    exporter.revision;
    if (el && el.innerHTML !== value) el.innerHTML = value;
  });

  function selectedText(): string {
    return (window.getSelection()?.toString() ?? "").trim();
  }

  function onkeydown(event: KeyboardEvent) {
    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    const commands: Record<string, string> = {
      b: "bold",
      i: "italic",
      u: "underline",
    };
    if (key in commands) {
      event.preventDefault();
      document.execCommand(commands[key]);
      onchange(el?.innerHTML ?? "");
      return;
    }
    if (key === "s" || key === "f") {
      const text = selectedText();
      if (text) {
        event.preventDefault();
        exporter.search(text, key === "f");
      }
    }
  }

  function onpaste(event: ClipboardEvent) {
    event.preventDefault();
    const text = event.clipboardData?.getData("text/plain") ?? "";
    document.execCommand("insertText", false, text);
    onchange(el?.innerHTML ?? "");
  }
</script>

<div
  bind:this={el}
  class="rich-field"
  class:empty={!value}
  contenteditable="true"
  role="textbox"
  tabindex="0"
  aria-multiline="true"
  aria-label={placeholder}
  data-placeholder={placeholder}
  style:min-height="{minHeight}px"
  style:max-height={maxHeight ? `${maxHeight}px` : "none"}
  style:font-size={fontSize}
  oninput={() => onchange(el?.innerHTML ?? "")}
  {onkeydown}
  {onpaste}
></div>
