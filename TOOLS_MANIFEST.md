# OpenCode Tools Manifest

Complete inventory of all custom tools and files built for this OpenCode system.

---

## System Commands (`/usr/local/bin/`)

| Command | Purpose | Created |
|---------|---------|---------|
| `ocr` | Resume last session (`opencode --continue`) | May 5 |
| `ocl` | List recent sessions (`opencode session list`) | May 5 |
| `oc-r` | Symlink → `auto-resume.sh resume` | May 5 |
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
| `oc-tui` | Keyboard-driven TUI dashboard for OpenCode | May 21 |

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

## Local Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `cors-proxy.js` | CORS proxy for Android WebView (port 9878) |
| `install.sh` | OpenCode installation script |
| `oc-context.sh` | Shared context inspection & management CLI |
| `server.sh` | Start the OpenCode API server |
| `start.sh` | Quick-start: launches server + CORS proxy |
| `vnc-daemon.sh` | VNC server daemon for headed browser mode |
| `zip.js` | Build script producing `dist/acode-oc.zip` |
| `oc-gitpush.sh` | Push OpenCode repo to GitHub with token auth |
| `oc-tui.py` | Terminal UI dashboard for OpenCode (ANSI, zero deps) |
| `oc_chat.py` | Chat interface module for oc-tui (multi-line, markdown, agent feed) |

## Agent Configs (`agents/`)

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

## Shared Context System (`shared/`)

| File | Purpose |
|------|---------|
| `context.json` | Structured JSON store — primary machine-readable context |
| `README.md` | Directory documentation |
| `findings/*.json` | Per-agent finding files (14 agents, one file each) |
| `helpers/context.py` | Python helper for agents to read/write context programmatically |
| `helpers/` | Agent helper scripts (context.py for read/write operations) |
| `chat_history.json` | Chat conversation history (auto-managed by oc-tui chat) |

To inspect the shared context at any time:
```bash
oc-context summary     # Human-readable summary
oc-context findings    # All agent findings
oc-context workflow    # Current workflow trace
oc-context session     # Session state
```

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

## Knowledge Graph (`knowledge-graph/`)

| File | Purpose |
|------|---------|
| `graph.json` | Agent registry, workflow patterns, quality gates, gap detection rules, shared context config |
| `README.md` | Graph structure documentation |
| `outcomes/sessions.json` | Session outcome tracker (populated by orchestrator on workflow completion) |

## Configuration Files

| File | Purpose |
|------|---------|
| `opencode.jsonc` | OpenCode main config (provider, model, permissions, MCP) |
| `plugin.json` | Acode plugin manifest (id: `com.opencode.acode`) |
| `package.json` | Node.js package metadata |
| `tui.json` | Terminal UI configuration |
| `icon.png` | App icon |
| `main.js` | Compiled core logic |

## Shell Integration

- **`.bashrc` aliases**: `oc`, `oc-r`, `oc-resume`, `oc-list` (4 lines added)

## Acode Plugin (`acode-plugin/`)

| File | Purpose |
|------|---------|
| `plugin.json` | Manifest (id: `com.opencode.acode`, v1.2.0) |
| `main.js` | Compiled plugin code (120KB) |
| `src/` | Source files: `index.js`, `client.js`, `commands.js`, `panel.js` |
| `scripts/zip.js` | Build script producing `dist/acode-oc.zip` |
| `scripts/cors-proxy.js` | CORS proxy for Android WebView (port 9878) |
| `scripts/start.sh` | Quick-start: launches server + CORS proxy |
| `dist/acode-oc.zip` | Installable plugin (31KB) |

**Install in Acode**: Settings → Plugins → Install from ZIP → select `dist/acode-oc.zip`

**Commands**: Ctrl+Shift+A (Ask), F (Fix), E (Explain), G (Generate), M (Multi-file), H (History)

## Quick Reference

```
# System commands:
ocr              # Resume last session
ocl              # List recent sessions
oc-r             # Same as ocr (alias)
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
oc-tui           # Terminal UI dashboard + Chat (Tab to switch)
oc-gitpush       # Push OpenCode repo to GitHub

# oc-context subcommands:
oc-context summary     # Human-readable context summary
oc-context findings    # View all agent findings
oc-context workflow    # View current workflow trace
oc-context session     # View session state
oc-context decisions   # View architecture/design decisions
oc-context artifacts   # View files created/modified
oc-context clear       # Reset shared context (with confirmation)
```
