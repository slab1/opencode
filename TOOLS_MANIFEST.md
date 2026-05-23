# OpenCode Tools Manifest

Complete inventory of all custom tools and files built for this OpenCode system.

---

## Primary CLI (`/usr/local/bin/oc`)

The main entry point — a polished, unified CLI with subcommands:

| Subcommand | Purpose |
|------------|---------|
| `oc ask <message>` | One-shot query with streaming response |
| `oc chat` | Interactive REPL session |
| `oc session list` | List recent sessions |
| `oc session show <id>` | Show full session details with messages |
| `oc session resume` | Resume the last session |
| `oc context [summary\|findings\|decisions\|artifacts\|workflow\|full]` | Shared context inspection |
| `oc agent <name> <message>` | Dispatch task to a specific agent |
| `oc models` | List available models from server |
| `oc server start\|stop\|status` | Server lifecycle management |
| `oc stats` | Usage statistics and analytics |
| `oc search <keyword>` | Search session content by keyword |
| `oc note <text>` | Quick persistent note |
| `oc cleanup [days]` | Delete old sessions (default: 30, dry-run: -n) |
| `oc docs` | Show full documentation |
| `oc --version` | Show version info |

**Source**: `scripts/oc.py` → symlink at `/usr/local/bin/oc`

---

## Legacy System Commands (`/usr/local/bin/`)

| Command | Purpose | Created |
|---------|---------|---------|
| `ocr` | Resume last session (`opencode --continue`) | May 5 |
| `ocl` | List recent sessions (`opencode session list`) | May 5 |
| `oc-auto` | Keyword-based agent auto-invoker | May 5 |
| `oc-voice` | Text-based "voice" command simulator | May 5 |
| `oc-sync` | Cross-platform sync daemon controller | May 5 |
| `oc-search` | Session keyword search | May 12 |
| `oc-stats` | Usage statistics dashboard | May 12 |
| `oc-cleanup` | Delete old sessions (with dry-run) | May 12 |
| `oc-note` | Quick session notes (persistent JSON) | May 12 |
| `oc-cron` | Scheduled task manager (crontab) | May 12 |
| `oc-backup` | Full session backup & restore | May 12 |
| `oc-monitor` | Live terminal dashboard (like htop) | May 12 |
| `oc-context` | Shared context inspection & management | May 21 |
| `oc-gitpush` | Push OpenCode repo to GitHub (with token auth) | May 12 |

**Note**: `oc-tui` was removed in favor of the unified `oc` CLI. Use `oc chat` for interactive sessions.

---

## REPL Engine (`scripts/oc_repl.py`)

Interactive command-line REPL with enhanced features:
- **Syntax highlighting** for code blocks (```...```) in responses
- **Multi-line input** (lines ending with `\` continue)
- **Tab completion** for slash commands (`/help`, `/exit`, `/models`, etc.)
- **Timing stats** per response (chars, elapsed time)
- **Session persistence** — writes to shared context automatically
- **Commands**: `/help`, `/exit`, `/quit`, `/clear`, `/cls`, `/models`, `/stats`, `/context`
- Library mode: `from oc_repl import OpenCodeREPL, REPLPoller`

---

## Chat Interface (`scripts/oc_chat.py`)

Terminal-based chat interface module (1130 lines):
- Multi-line input with text wrapping
- Message history persistence (JSON)
- Agent activity feed with status polling
- Markdown rendering with ANSI codes
- Full keyboard navigation
- Integrates with `oc_repl` for backend communication

---

## Cache Scripts (`/data/user/0/com.foxdebug.acode/cache/opencode/`)

| Script | Purpose | Lines |
|--------|---------|-------|
| `auto-resume.sh` | Interactive session resume | 100+ |
| `auto-session.sh` | 5-min auto-save daemon | 60+ |
| `voice-simple.py` | HTTP server for voice commands (port 8081) | 110+ |
| `voice-ui.html` | Web Speech API frontend with animations | 200+ |
| `cross-platform-db.py` | Direct SQLite session reader | 100+ |
| `cross-platform-client.py` | Multi-device sync client | 150+ |
| `cross-platform-sync.py` | Background sync daemon | 90+ |
| `bubble-bookmarklet.html` | Floating voice button bookmarklet | 200+ |

---

## Local Scripts (`scripts/`)

| Script | Purpose | Lines |
|--------|---------|-------|
| `oc.py` | **Main CLI entry point** — all `oc *` subcommands | 540+ |
| `oc_repl.py` | REPL engine + standalone interactive mode | 700+ |
| `oc_chat.py` | Chat interface module (multi-line, markdown, agent feed) | 1130 |
| `test_agents.py` | Comprehensive test suite (33 tests, context→agents→CLI) | 310+ |
| `oc-context.sh` | Shared context inspection & management CLI | 399 |
| `oc-gitpush.sh` | Push OpenCode repo to GitHub with token auth | 37 |
| `cors-proxy.js` | CORS proxy for Android WebView (port 9878) | — |
| `install.sh` | OpenCode installation script | — |
| `server.sh` | Start the OpenCode API server | — |
| `start.sh` | Quick-start: launches server + CORS proxy | — |
| `vnc-daemon.sh` | VNC server daemon for headed browser mode | — |
| `zip.js` | Build script producing `dist/acode-oc.zip` | — |

---

## Agent Configs (`agents/`)

15 custom agents with permission rules and shared context integration:

| Agent | Mode | Key Permissions |
|-------|------|-----------------|
| `build.md` | primary | edit:allow, bash:ask, task:allow |
| `plan.md` | primary | edit:deny, todowrite:allow, task:allow |
| `orchestrator.md` | primary | edit:allow, bash:ask, task:allow, webfetch:ask, websearch:ask |
| `architect.md` | subagent | bash:selective, webfetch:ask |
| `debug.md` | subagent | bash:ask |
| `docs.md` | subagent | edit:allow, webfetch:ask |
| `explore.md` | subagent | (fast codebase explorer) |
| `general.md` | subagent | edit:deny, bash:ask, todowrite:allow, webfetch:ask, websearch:ask |
| `refactor.md` | subagent | edit:allow, bash:ask |
| `review.md` | subagent | (code quality) |
| `security.md` | subagent | bash:selective, webfetch:ask |
| `test.md` | subagent | edit:allow, bash:ask |
| `display-agent.md` | subagent | edit:allow, bash:ask, todowrite:allow |
| `video-creator.md` | subagent | edit:allow, bash:ask, webfetch:ask, websearch:ask |
| `web-browser.md` | subagent | edit:allow, bash:ask, webfetch:ask, websearch:ask |

---

## Shared Context System (`shared/`)

Cross-agent memory persistence — every agent reads at start, writes findings at finish.

| File | Purpose |
|------|---------|
| `context.json` | Structured JSON store — primary machine-readable context |
| `README.md` | Directory documentation |
| `findings/*.json` | Per-agent finding files (14 agents, one file each) |
| `helpers/context.py` | Python helper for agents to read/write context programmatically (272 lines) |
| `chat_history.json` | Chat conversation history |
| `notes.json` | Persistent notes (via `oc note`) |

To inspect the shared context:
```bash
oc context summary      # Human-readable summary
oc context findings     # All agent findings
oc context decisions    # Architecture/design decisions
oc context artifacts    # Files created/modified
oc context workflow     # Current workflow trace
oc context full         # Raw JSON
```

---

## Knowledge Graph (`knowledge-graph/`)

| File | Purpose |
|------|---------|
| `graph.json` | Agent registry, workflow patterns (13), quality gates (8), gap detection rules, shared context config |
| `README.md` | Graph structure documentation |
| `outcomes/sessions.json` | Session outcome tracker with aggregated insights |

Persistence: Every `oc ask` call saves to outcomes. Context findings persist across sessions.

---

## Configuration Documents

| File | Lines | Purpose |
|------|-------|---------|
| `AGENTS.md` | 221+ | Permission syntax & agent architecture docs |
| `AGENT_ROUTER.md` | 110 | Keyword-to-agent routing rules |
| `SESSION_STATE.md` | 150+ | Auto-resume state tracker + shared context integration |
| `SHARED_CONTEXT.md` | 189 | Cross-agent memory store v2 (reference) |
| `ULTIMATE_PLAN.md` | 383 | Full roadmap & vision |
| `WORKFLOWS.md` | 522+ | 16 multi-agent workflows with context flow |
| `TOOLS_MANIFEST.md` | — | This file |
| `changelogs.md` | — | Release changelog |
| `README.md` | — | Project README |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `opencode.jsonc` | OpenCode main config (provider, model, permissions, MCP) |
| `plugin.json` | Acode plugin manifest (id: `com.opencode.acode`, v3.2.8) |
| `package.json` | Node.js package metadata |
| `icon.png` | App icon |
| `main.js` | Compiled core logic |

---

## Test Suite

Run all 33 tests:
```bash
python3 scripts/test_agents.py       # Compact output
python3 scripts/test_agents.py -v    # Verbose
python3 scripts/test_agents.py TestContextSystem  # Specific test class
```

**Test categories** (33 tests, all pass):
- `TestContextSystem` (5) — shared context read/write, state updates
- `TestSessionPersistence` (3) — outcome structure, add/aggregate
- `TestCLISubcommands` (10) — all `oc *` subcommands routing and response
- `TestREPLEngine` (7) — REPL class, poller, highlighting, error classes
- `TestKnowledgeGraph` (5) — graph structure, agents, patterns, quality gates
- `TestAgentConfigs` (2) — agent .md files existence and frontmatter
- `TestScriptFiles` (3) — scripts exist, symlinks valid, Python compiles

---

## Quick Reference

```bash
# Primary CLI
oc --version                         # Show version
oc ask "fix the login bug"           # One-shot query
oc chat                              # Interactive REPL
oc session list                      # List recent sessions
oc session show <id>                 # Show session details
oc session resume                    # Resume last session
oc context summary                   # Context overview
oc context findings                  # All agent findings
oc agent build "implement feature"   # Dispatch to specific agent
oc server status                     # Check server health
oc stats                             # Usage statistics
oc search "keyword"                  # Search sessions
oc note "remember this"              # Quick note
oc cleanup 30 -n                     # Dry-run cleanup

# Legacy commands (still work)
ocr              # Resume last session
ocl              # List recent sessions
oc-auto "..."    # Smart agent selector
oc-search "kw"   # Find sessions by keyword
oc-stats         # Usage statistics dashboard
oc-monitor       # Live terminal dashboard
oc-cleanup       # Delete old sessions (with dry-run)
oc-backup create # Full session backup
oc-note "..."    # Quick session note (persistent JSON)
oc-cron          # Scheduled task manager
oc-sync          # Cross-platform sync daemon
oc-voice         # Voice command simulator
oc-context       # Shared context inspection
oc-gitpush       # Push OpenCode repo to GitHub
```
