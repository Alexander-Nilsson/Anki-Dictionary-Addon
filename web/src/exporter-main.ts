import { mount } from "svelte";
import "./exporter.css";
import ExporterApp from "./exporter/ExporterApp.svelte";
import { initExporterBridge } from "./lib/exporter-bridge";
import { wireExporterReplies } from "./lib/exporter.svelte";

// Install the `window.EXPORTER` reply surface before mounting and connect it
// to the reactive store. Python's `AnkiWebView.eval` targets these globals.
initExporterBridge();
wireExporterReplies();

const target = document.getElementById("app");
if (!target) {
  console.error("Exporter mount target #app not found");
} else {
  mount(ExporterApp, { target });
}
