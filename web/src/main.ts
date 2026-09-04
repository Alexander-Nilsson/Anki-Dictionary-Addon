import { mount } from "svelte";
import "./app.css";
import App from "./components/App.svelte";
import { initBridge } from "./lib/bridge";
import { awaitPycmdToLoad } from "./lib/pycmd";
import { initFromWindow, initSidebarSync, resizer } from "./lib/tabs.svelte";

// Capture Python-injected settings (font sizes, welcome content) before mount.
initFromWindow();

// Keep the results-pane sidebar highlight in sync with the visible entry.
initSidebarSync();

// Expose the Python + content bridge globals.
initBridge();

// Keep the results pane sized correctly when the window resizes.
window.addEventListener("resize", resizer);

const target = document.getElementById("app");
if (!target) {
  console.error("Svelte mount target #app not found");
} else {
  mount(App, { target });
}

// Announce to Python that the page finished loading (triggers pending searches).
awaitPycmdToLoad();