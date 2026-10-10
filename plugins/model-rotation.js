// model-rotation OpenCode plugin
// Health-aware automatic model rotation for agents.
//
// OpenCode 1.18.x has no per-request model-switch hook, so this plugin does three things:
//   1. config hook  -> assigns a model to each agent at startup, round-robin across the
//                      pool while skipping cooled-down models (health tracking).
//   2. chat.message -> best-effort: if the inbound message pins a cooled-down model,
//                      swap it to the next healthy model for that turn.
//   3. event hook   -> on a rate-limit/quota/capacity error, cool the responsible model
//                      down for cooldownMs so future assignments avoid it.
//
// Config:  ~/.config/opencode/model-rotation.json   (env MODEL_ROTATION_CONFIG to override)
// State:   ~/.config/opencode/.model-rotation-state.json (env MODEL_ROTATION_STATE to override)
//
// NOTE: the OpenCode plugin loader treats every export as a plugin factory, so all
// helpers must stay module-private (not exported).

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { homedir } from "os";

const CONFIG_DIR = process.env.OPENCODE_CONFIG_DIR || join(homedir(), ".config", "opencode");
const CONFIG_PATH = process.env.MODEL_ROTATION_CONFIG || join(CONFIG_DIR, "model-rotation.json");
const STATE_PATH = process.env.MODEL_ROTATION_STATE || join(CONFIG_DIR, ".model-rotation-state.json");

const DEFAULTS = {
  enabled: true,
  strategy: "round-robin", // "round-robin" | "first-available"
  cooldownMs: 5 * 60 * 1000,
  spreadAgents: true,
  models: ["opencode/big-pickle"],
  agents: {},
};

const LIMIT_RE = /rate.?limit|quota|429|free tier|capacity|overloaded|too many requests|temporarily unavailable|resource[_ ]?exhausted/i;

function readJSON(p, fallback) {
  try {
    return JSON.parse(readFileSync(p, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJSON(p, data) {
  try {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, JSON.stringify(data, null, 2));
  } catch {
    /* best-effort */
  }
}

function loadConfig() {
  const user = readJSON(CONFIG_PATH, {});
  return {
    ...DEFAULTS,
    ...user,
    models: Array.isArray(user.models) && user.models.length ? user.models : DEFAULTS.models,
    agents: user.agents && typeof user.agents === "object" ? user.agents : {},
  };
}

function loadState() {
  const s = readJSON(STATE_PATH, {});
  return { cooldowns: s.cooldowns && typeof s.cooldowns === "object" ? s.cooldowns : {}, counter: Number(s.counter) || 0 };
}

function healthyPool(list, state, now) {
  const healthy = list.filter((m) => (state.cooldowns[m] ?? 0) <= now);
  return healthy.length ? healthy : list; // if everything is cooled, use the full list
}

function parseModel(str) {
  if (typeof str !== "string") return null;
  const i = str.indexOf("/");
  if (i <= 0 || i === str.length - 1) return null;
  return { providerID: str.slice(0, i), modelID: str.slice(i + 1) };
}

function pickFor(agent, cfg, state, now) {
  const override = cfg.agents?.[agent];
  const base = Array.isArray(override) && override.length ? override : cfg.models;
  const pool = healthyPool(base, state, now);
  if (!pool.length) return null;
  if (cfg.strategy === "first-available") return pool[0];
  const chosen = pool[state.counter % pool.length];
  state.counter += 1;
  return chosen;
}

function modelKey(m) {
  if (!m) return null;
  const providerID = m.providerID ?? m.provider?.id;
  const modelID = m.modelID ?? m.id;
  if (!providerID || !modelID) return null;
  return `${providerID}/${modelID}`;
}

export const ModelRotationPlugin = async ({ client }) => {
  const log = async (level, message, extra) => {
    try {
      await client.app.log({ body: { service: "model-rotation", level, message, extra } });
    } catch {
      /* logging is best-effort */
    }
  };

  const lastModelBySession = new Map();

  return {
    // 1) Startup assignment: give each agent a health-aware rotation slot.
    config: async (input) => {
      const cfg = loadConfig();
      if (!cfg.enabled) return;
      try {
        const state = loadState();
        const now = Date.now();
        const agents = input?.agent;
        if (!agents || typeof agents !== "object") {
          await log("warn", "config hook: no agent table present; rotation not applied", {});
          return;
        }
        const names = Object.keys(agents);
        if (cfg.spreadAgents && names.length) {
          // advance once so different agents get different slots across the pool
          state.counter += 1;
        }
        let assigned = 0;
        const summary = {};
        for (const name of names) {
          const chosen = pickFor(name, cfg, state, now);
          if (!chosen || !parseModel(chosen)) continue;
          const entry = agents[name] && typeof agents[name] === "object" ? agents[name] : {};
          agents[name] = { ...entry, model: chosen };
          summary[name] = chosen;
          assigned += 1;
        }
        writeJSON(STATE_PATH, state);
        await log("info", `rotation: assigned models to ${assigned}/${names.length} agents`, summary);
      } catch (e) {
        await log("warn", "config hook failed: " + e.message, {});
      }
    },

    // 2) Track the model actually used per session (for error attribution).
    "chat.params": async (input) => {
      try {
        const key = modelKey(input?.model);
        if (input?.sessionID && key) lastModelBySession.set(input.sessionID, key);
      } catch {
        /* ignore */
      }
    },

    // 3) Best-effort mid-session fallback when the pinned model is cooling down.
    "chat.message": async (input, output) => {
      const cfg = loadConfig();
      if (!cfg.enabled) return;
      try {
        const requested = modelKey(input?.model);
        if (!requested) return;
        const state = loadState();
        const now = Date.now();
        if ((state.cooldowns[requested] ?? 0) <= now) return; // model is healthy
        const chosen = pickFor(input?.agent ?? "", cfg, state, now);
        const parsed = parseModel(chosen);
        if (parsed && output?.message) {
          output.message.model = parsed;
          writeJSON(STATE_PATH, state);
          await log("info", `rotation: swapped cooled model ${requested} -> ${chosen}`, {
            sessionID: input?.sessionID,
            agent: input?.agent,
          });
        }
      } catch (e) {
        await log("warn", "chat.message hook failed: " + e.message, {});
      }
    },

    // 4) Rate-limit detection -> cooldown the responsible model.
    event: async ({ event }) => {
      try {
        if (event?.type !== "session.error") return;
        const props = event.properties ?? {};
        const sessionID = props.sessionID;
        const shown = modelKey(props.model) || lastModelBySession.get(sessionID) || null;
        const text = JSON.stringify(props.error ?? props ?? "").toLowerCase();
        if (!LIMIT_RE.test(text)) return;
        const cfg = loadConfig();
        const state = loadState();
        if (shown) {
          const ttl = Number(cfg.cooldownMs) || DEFAULTS.cooldownMs;
          state.cooldowns[shown] = Date.now() + ttl;
          writeJSON(STATE_PATH, state);
          await log("warn", `rotation: cooling ${shown} for ${Math.round(ttl / 60000)}m after limit error`, {
            sessionID,
            model: shown,
          });
        } else {
          await log("warn", "rotation: limit error but model could not be attributed", { sessionID });
        }
      } catch (e) {
        await log("warn", "event hook failed: " + e.message, {});
      }
    },
  };
};
