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
