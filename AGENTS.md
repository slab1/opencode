# OpenCode Platform Manager — AGENTS.md

This file is a map for AI agents working with the OpenCode Platform Manager system.
All social media management tools, scripts, and config live under `~/.config/opencode/platforms/`.

**Inspired by:** Hermes Agent dev guide (NousResearch, 189K ⭐) + agentsmd/agents.md format (22K ⭐)

---

## Directory Map

```
~/.config/opencode/
├── AGENTS.md                  ← THIS FILE — root map + dev guide
├── opencode.jsonc             ← Main OpenCode config (MCP servers, permissions, plugins)
├── agents/
│   ├── human.md                ← Agent config: Human analysis — reads code like a senior engineer, searches GitHub/online, fixes ALL kinds of problems
│   ├── platform-manager.md     ← Agent config: social media management agent
│   └── ... (20+ other agents)
├── platforms/
│   ├── AGENTS.md              ← Platform manager system docs + architecture
│   ├── setup-wizard.sh        ← Interactive account setup for 11 platforms
│   ├── post.sh                ← Cross-platform posting script
│   ├── calendar.py            ← Content calendar & scheduler
│   ├── analytics.py           ← Cross-platform analytics reporter
│   ├── content-gen.py         ← AI content generation (images, video, captions)
│   ├── media-optimizer.py     ← Auto-resize media for each platform's dimensions
│   ├── understand-bridge.py   ← Understand Anything knowledge graph → shared context bridge
│   ├── adapters/              ← Pluggable platform adapter modules (Hermes-inspired)
│   └── tokens/                ← API tokens (chmod 600, gitignored)
├── shared/
│   ├── AGENTS.md              ← Shared context system docs
│   ├── context.json           ← Cross-agent shared context (READ FIRST)
│   ├── commitments.json       ← Cross-agent commitments tracker
│   ├── performance.json       ← Performance tracking data
│   └── free-models-guide.md   ← Guide to free AI models
├── skills/
│   └── skills/                ← Agent skills (SKILL.md format)
└── scripts/                   ← Utility scripts (setup, MCP toggle, etc.)
```

---

## File Dependency Chain

Understanding how scripts depend on each other — read bottom-up:

```
content-gen.py  (generates media — no deps on other scripts)
       ↑
media-optimizer.py  (resizes media — no deps on other scripts)
       ↑
calendar.py  (schedules + processes posts — calls post.sh via subprocess)
       ↑
post.sh  (publishes to platforms — reads backend.json, accounts.json, tokens/)
       ↑
analytics.py  (fetches/reports metrics — reads posts.jsonl, calls backend API)
       ↑
setup-wizard.sh  (configures everything — writes backend.json, accounts.json, tokens/)
```

**Startup order:** setup-wizard.sh → (backend config) → post.sh / calendar.py / analytics.py
**Content pipeline:** content-gen.py → media-optimizer.py → calendar.py add → calendar.py process

---

## Capability Footprint Ladder

Inspired by Hermes Agent's design principle: **capability should reach users through the least permanent surface possible.**

| Rung | Surface | What It Means Here | Example |
|------|---------|-------------------|---------|
| 1 | **Extend existing script** | Zero new files. Add a flag, mode, or option. | `post.sh --thread` for thread support |
| 2 | **New CLI script** | One new file in platforms/, follows existing conventions. | `content-gen.py`, `media-optimizer.py` |
| 3 | **Config-gated feature** | Only activates when configured (backend key, env var). | `post.sh --backend trypost` |
| 4 | **Pluggable adapter** | Drop-in module in adapters/, auto-discovered. | New platform adapter (see adapters/AGENTS.md) |
| 5 | **MCP server** | External tool reuses our MCP client infrastructure. | BulkPublish MCP in opencode.jsonc |
| 6 | **Core system change** | Modifies shared infrastructure. Last resort. | Changing token storage, logging, or error handling |

**Rule of thumb:** Before adding a new script or modifying core behavior, check if rungs 1-4 solve the problem first.

---

## Critical Rules for Agents

1. **READ `shared/context.json` first** — Contains cross-agent shared state.
2. **Tokens live in `platforms/tokens/` with `chmod 600`** — Never log or expose them.
3. **All posts are logged in `platforms/posts.jsonl`** — Append-only log for auditing.
4. **Analytics are stored in `platforms/analytics/metrics.jsonl`** — Appended on each fetch.
5. **Calendar lives in `platforms/calendar.json`** — Read/write with `platforms/calendar.py`.
6. **Self-document** — After editing any script or config, update the corresponding `AGENTS.md`.

---

## Contribution Rubric

### What We Want
- **Bug fixes** that reproduce the issue and fix the whole class, not just one call site
- **New platform adapters** as pluggable modules in `adapters/` (see adapters/AGENTS.md)
- **Content format improvements** — template enhancements, new content types
- **Refactors** that extract god-files into clean modules
- **Better error messages** that tell the user exactly what to fix

### What We Don't Want
- **Speculative infrastructure** — hooks/callbacks with no concrete consumer
- **New scripts that duplicate existing functionality** — extend before creating
- **Hardcoded credentials** — secrets go in `tokens/` with `chmod 600`, period
- **Env var sprawl for non-secret config** — use config files, not env vars
- **Tests that freeze current model responses** — assert behavior invariants, not exact outputs

### Before You Submit a Change
1. Read the target file first (understand current state)
2. Route capability through the lowest Footprint Ladder rung possible
3. Test with `--dry-run` where available
4. Update AGENTS.md if directory structure or commands change
5. Log action in `shared/performance.json`

---

## What Makes This System Stand Out

This system implements 9 strategic differentiators beyond what typical code agents offer:

### 🔥 Genuinely Novel
1. **Automatic Agent Evolution** — `agent-eval/auto_evolve.py` reads eval results, patches failing agent configs, re-evaluates until scores improve. Self-healing agent configurations.
2. **Dynamic Agent Spawning** — `opencode_improvement/spawner.py` creates transient multi-agent teams for complex tasks. Ephemeral pods with shared context and automatic cleanup.
3. **Delegation Pattern Mining** — `opencode_improvement/pattern_miner.py` learns which agents excel at which tasks from historical performance data. Recommends optimal routing.

### 🥈 High-Visibility
4. **Live Agent Dashboard** — `dashboard/main.py` FastAPI web UI showing eval scores, strategy effectiveness, agent health, and performance trends.
5. **Competitive Benchmarking** — `opencode_improvement/benchmark.py` runs the 53 golden test cases and compares results against other agent systems.
6. **Cross-Session Memory Loop** — `opencode_improvement/memory_loop.py` generates structured handoff records so each session learns from the last.

### 🥉 Polished Infrastructure
7. **Single-Command Setup** — `install.sh` provisions the entire system with `bash <(curl -fsSL ...)`.
8. **AGENTS.md Protocol Spec** — `AGENTS_SPEC.md` formalizes the discoverability protocol for other projects.
9. **Standalone Eval Toolkit** — `agent-eval/` is a pip-installable package for evaluating ANY agent system.

---

## Key Commands

| Action | Command |
|--------|---------|
| Setup new accounts | `bash ~/.config/opencode/platforms/setup-wizard.sh` |
| Post immediately | `bash ~/.config/opencode/platforms/post.sh --text "..." --platforms "twitter"` |
| Schedule a post | `python3 ~/.config/opencode/platforms/calendar.py add --text "..." --platforms "..." --schedule "2026-06-10 14:00"` |
| Process due posts | `python3 ~/.config/opencode/platforms/calendar.py process` |
| View analytics | `python3 ~/.config/opencode/platforms/analytics.py report` |
| Generate content | `python3 ~/.config/opencode/platforms/content-gen.py image --prompt "..."` |
| Optimize media | `python3 ~/.config/opencode/platforms/media-optimizer.py input.jpg --platforms instagram,twitter` |
| List platform adapters | `python3 ~/.config/opencode/platforms/post.sh --list-adapters` |
| Run learning loop | `python3 ~/.config/opencode/platforms/analytics.py learn` |
| Auto-evolve agents | `python3 ~/.config/opencode/agent-eval/auto_evolve.py [--agent NAME] [--dry-run]` |
| Delegation patterns | `python3 -m opencode_improvement patterns --recommend "fix login bug"` |
| Spawn agent team | `python3 -m opencode_improvement spawn --task "..." --complexity moderate` |
| Benchmark vs other agents | `python3 -m opencode_improvement benchmark --compare` |
| Memory handoff | `python3 -m opencode_improvement memory --handoff` |
| Live dashboard | `python3 ~/.config/opencode/dashboard/main.py --port 8080` |
| Bridge U-A graph | `python3 ~/.config/opencode/platforms/understand-bridge.py --input graph.json --output context.json --project NAME` |
| View graph summary | `python3 ~/.config/opencode/platforms/understand-bridge.py --input graph.json --summary` |
| Generate guided tour | `python3 ~/.config/opencode/platforms/understand-bridge.py --input graph.json --generate-tour --output TOUR.md` |
| Diff graph versions | `python3 ~/.config/opencode/platforms/understand-bridge.py --input new.json --diff old.json` |

---

## Architecture Overview

### System Boundaries

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  User/AI     │───▶│  Agent Layer     │───▶│  Publishing Layer │
│  (prompts)   │    │  (plan + create)  │    │  (post + schedule)│
└──────────────┘    └──────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                     ┌──────────────┐    ┌─────────────────┐
                     │  Media Layer │    │  Analytics Layer │
                     │  (gen + opt) │    │  (track + learn) │
                     └──────────────┘    └─────────────────┘
```

### Data Flow for a Post

```
1. content-gen.py  →  image/video file
       │
2. media-optimizer.py  →  resized files per platform
       │
3. calendar.py add  →  calendar.json entry
       │
4. calendar.py process  →  post.sh (for each due post)
       │
5. post.sh  →  backend API  →  platform API  →  published
       │
6. analytics.py fetch  →  metrics.jsonl
       │
7. analytics.py learn  →  best posting times learned
```

---

## Coding Conventions

### Python Scripts
- Use `argparse` with `subparsers` for multi-command scripts
- Support `--help` on every script
- Support `--dry-run` for testing
- Use `pathlib.Path` for file paths (never `os.path`)
- ANSI color class `C` for terminal output (consistent across scripts)
- `sys.exit(1)` on errors, `sys.exit(0)` on success

### Shell Scripts
- `set -e` for fail-fast
- `--dry-run` flag that prints instead of executes
- Color constants at the top (RED, GREEN, YELLOW, etc.)
- Parse args at the top, validate before executing

### Configuration
- API keys → `tokens/` directory with `chmod 600`
- Non-secret config → JSON files (`backend.json`, `accounts.json`)
- All posts logged → `posts.jsonl` (append-only)
- Metrics stored → `analytics/metrics.jsonl`

---

## Adding a New Platform Adapter

See `platforms/adapters/AGENTS.md` for the full guide. Quick steps:

1. Create `platforms/adapters/<name>/` directory
2. Create `__init__.py` with required exports: `PLATFORM`, `post()`, `validate_credentials()`
3. Create `AGENTS.md` documenting the adapter
4. Test with `post.sh --adapter <name> --dry-run`

---

## File Change Protocol

When editing any file under `platforms/` or `shared/`:
1. Read the file first (understand current state)
2. Make the change
3. Update the corresponding `AGENTS.md` if the change affects the directory structure, available commands, or conventions
4. Test with `--dry-run` where available
5. Log the action in `shared/performance.json`

---

## Eval System — Agent Evaluation & CI Gating

The eval system evaluates agent configs against golden test cases, enforces quality gates,
and detects regressions. Inspired by 7 eval harness repos.

### Architecture

```
shared/eval/
├── AGENTS.md              ← Eval system documentation
├── agent_eval.yaml        ← Main eval config (regokan/evalh pattern)
├── build_eval.yaml        ← Per-agent eval configs
├── ... 22 more ...
└── baseline.json          ← Baseline snapshot (Victor-David-Medina pattern)

shared/golden/
├── AGENTS.md              ← Golden dataset documentation
└── agent_tasks.json       ← 53 test cases: behavioral + property-based
```

### Patterns Implemented

| Pattern | Source | What It Does |
|---------|--------|--------------|
| **Structured golden datasets** | DeepEval (⭐7k) | Input/expected/metrics per test case |
| **YAML-driven eval config** | regokan/evalh | Single `agent_eval.yaml` drives all eval |
| **`--fail-under` CI gate** | Juanllenato | Non-zero exit blocks CI when pass rate drops |
| **Baseline comparison** | Victor-David-Medina | Snapshot current state, detect regressions |
| **3-layer eval** | mpuodziukas-labs | Golden + property invariants + LLM-judge |
| **CI cron + diff** | linny006 | Weekly scheduled eval runs with auto-tracking |

### Key Commands

| Action | Command |
|--------|---------|
| Evaluate all agents | `python3 -m opencode_improvement eval` |
| Evaluate one agent | `python3 -m opencode_improvement eval --agent build` |
| With fail-under gate | `python3 -m opencode_improvement eval --fail-under 0.8` |
| Compare vs baseline | `python3 -m opencode_improvement eval --compare` |
| List available strategies | `python3 -m opencode_improvement list-strategies` |
| View strategy effectiveness | `python3 -m opencode_improvement strategies` |
