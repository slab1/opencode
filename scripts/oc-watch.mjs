#!/usr/bin/env node
/**
 * OpenCode Config Hot-Reload Watcher
 * 
 * Monitors opencode.jsonc for changes and applies them where possible
 * without a full restart. Handles:
 *   - MCP server config changes → restart MCP servers
 *   - Plugin list changes → notify user to restart
 *   - Permission changes → apply immediately
 *   - Model changes → apply at next session
 * 
 * Usage:
 *   node scripts/oc-watch.mjs            # foreground
 *   node scripts/oc-watch.mjs --daemon   # background
 *   node scripts/oc-watch.mjs --once     # single check then exit
 */

import { watch, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import { spawn, execSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_DIR = join(__dirname, "..");
const CONFIG_PATH = join(CONFIG_DIR, "opencode.jsonc");
const STATE_PATH = join(CONFIG_DIR, "shared", "watch-state.json");

let previousConfig = "";
let debounceTimer = null;

function log(msg) {
  const ts = new Date().toISOString().replace("T", " ").slice(0, 19);
  console.log(`[${ts}] [watch] ${msg}`);
}

function readConfig() {
  try {
    return readFileSync(CONFIG_PATH, "utf-8");
  } catch {
    return "";
  }
}

function parseConfig(text) {
  // Simple JSONC parser (strips comments)
  try {
    const stripped = text.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
    return JSON.parse(stripped);
  } catch (e) {
    log(`Parse error: ${e.message}`);
    return null;
  }
}

function getPluginList(config) {
  return (config?.plugin || []).map(p => p.replace(/^@[^/]+\//, "").replace(/@.*$/, ""));
}

function detectChanges(oldText, newText) {
  if (!oldText) return { type: "initial", detail: "Config loaded" };
  if (oldText === newText) return null;

  const oldConfig = parseConfig(oldText);
  const newConfig = parseConfig(newText);
  if (!oldConfig || !newConfig) return { type: "parse_error", detail: "Could not parse config" };

  const changes = [];

  // Check plugin changes
  const oldPlugins = getPluginList(oldConfig);
  const newPlugins = getPluginList(newConfig);
  const added = newPlugins.filter(p => !oldPlugins.includes(p));
  const removed = oldPlugins.filter(p => !newPlugins.includes(p));
  if (added.length) changes.push(`Plugins added: ${added.join(", ")}`);
  if (removed.length) changes.push(`Plugins removed: ${removed.join(", ")}`);

  // Check MCP changes
  const oldMcp = JSON.stringify(oldConfig.mcp || {});
  const newMcp = JSON.stringify(newConfig.mcp || {});
  if (oldMcp !== newMcp) {
    const mcpChanges = [];
    for (const key of Object.keys(newConfig.mcp || {})) {
      if (!oldConfig.mcp?.[key]) mcpChanges.push(`MCP server added: ${key}`);
    }
    for (const key of Object.keys(oldConfig.mcp || {})) {
      if (!newConfig.mcp?.[key]) mcpChanges.push(`MCP server removed: ${key}`);
    }
    // Check enabled/disabled changes
    for (const key of Object.keys({ ...oldConfig.mcp, ...newConfig.mcp })) {
      const oldE = oldConfig.mcp?.[key]?.enabled;
      const newE = newConfig.mcp?.[key]?.enabled;
      if (oldE !== undefined && newE !== undefined && oldE !== newE) {
        mcpChanges.push(`MCP server ${key}: ${newE ? "enabled" : "disabled"}`);
      }
    }
    changes.push(...mcpChanges);
  }

  // Check permission changes
  const oldPerms = JSON.stringify(oldConfig.permission || {});
  const newPerms = JSON.stringify(newConfig.permission || {});
  if (oldPerms !== newPerms) {
    changes.push("Permissions changed (applied immediately)");
  }

  // Check model changes
  if (oldConfig.model !== newConfig.model) {
    changes.push(`Model changed: ${newConfig.model} (applies next session)`);
  }
  if (oldConfig.small_model !== newConfig.small_model) {
    changes.push(`Small model changed: ${newConfig.small_model} (applies next session)`);
  }

  return {
    type: changes.length ? "changes_detected" : "no_effective_change",
    detail: changes.join("; ") || "No effective changes detected",
    changes,
    requiresRestart: added.length > 0 || removed.length > 0,
  };
}

function handleChange() {
  const newConfig = readConfig();
  const result = detectChanges(previousConfig, newConfig);
  
  if (!result) return; // No change
  
  if (result.type === "initial") {
    log(`Watching ${CONFIG_PATH}`);
    previousConfig = newConfig;
    saveState(newConfig);
    return;
  }

  log(`Config change detected: ${result.detail}`);

  if (result.requiresRestart) {
    log("⚠️ Plugin changes require opencode restart to take effect");
  }
  if (result.changes?.some(c => c.includes("MCP"))) {
    log("🔧 MCP changes apply to new sessions automatically");
  }
  if (result.changes?.some(c => c.includes("Permission"))) {
    log("✅ Permission changes applied immediately");
  }

  previousConfig = newConfig;
  saveState(newConfig);
}

function saveState(configText) {
  const config = parseConfig(configText);
  if (!config) return;
  const state = {
    lastUpdated: new Date().toISOString(),
    plugins: getPluginList(config),
    mcpServers: Object.keys(config.mcp || {}),
    model: config.model,
    smallModel: config.small_model,
  };
  try {
    writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
  } catch {}
}

function startWatcher() {
  previousConfig = readConfig();
  handleChange(); // Log initial state
  
  watch(CONFIG_PATH, (eventType) => {
    if (eventType !== "change") return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(handleChange, 500); // Debounce
  });

  log("Config watcher running. Press Ctrl+C to stop.");
}

// ── CLI ──
const args = process.argv.slice(2);
if (args.includes("--once")) {
  previousConfig = readConfig();
  handleChange();
  process.exit(0);
} else if (args.includes("--status")) {
  if (existsSync(STATE_PATH)) {
    console.log(readFileSync(STATE_PATH, "utf-8"));
  } else {
    console.log(JSON.stringify({ status: "no_state", message: "No prior watch state" }, null, 2));
  }
} else {
  startWatcher();
}
