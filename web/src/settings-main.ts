import { mount } from "svelte";
import "./settings.css";
import SettingsApp from "./settings/SettingsApp.svelte";
import { initSettingsBridge } from "./lib/settings-bridge";
import { wireSettingsReplies } from "./lib/settings.svelte";

// Install the `window.SETTINGS` reply surface before mounting and connect it
// to the reactive store. Python's `AnkiWebView.eval` targets these globals.
initSettingsBridge();
wireSettingsReplies();

const target = document.getElementById("app");
if (!target) {
  console.error("Settings mount target #app not found");
} else {
  mount(SettingsApp, { target });
}