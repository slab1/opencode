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

## Agent Configs (`agents/`)

| Agent | Mode | Key Permissions |
|-------|------|-----------------|
| `build.md` | primary | edit:allow, bash:ask |
| `plan.md` | primary | edit:deny, todowrite:allow |
| `orchestrator.md` | primary | (coordinator) |
| `architect.md` | subagent | bash:selective, webfetch:ask |
| `debug.md` | subagent | bash:ask |
| `docs.md` | subagent | edit:allow, webfetch:ask |
| `explore.md` | subagent | (fast codebase explorer) |
| `general.md` | subagent | (general research) |
| `refactor.md` | subagent | bash:ask |
| `review.md` | subagent | (code quality) |
| `security.md` | subagent | bash:selective, webfetch:ask |
| `test.md` | subagent | (test writing) |

## Configuration Documents

| File | Lines | Purpose |
|------|-------|---------|
| `AGENTS.md` | 221 | Permission syntax documentation |
| `AGENT_ROUTER.md` | 110 | Keyword-to-agent routing rules |
| `SESSION_STATE.md` | 138 | Auto-resume state tracker |
| `SHARED_CONTEXT.md` | 109 | Cross-agent memory store |
| `ULTIMATE_PLAN.md` | 383 | Full roadmap & vision |
| `WORKFLOWS.md` | 261 | 6 multi-agent workflows |
| `TOOLS_MANIFEST.md` | — | This file |

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
# Most-used commands:
ocr              # Resume session
ocl              # List sessions
oc-auto "..."    # Smart agent selector
oc-note "..."    # Quick note
oc-search "kw"   # Find sessions
oc-stats         # Dashboard
oc-monitor       # Live dashboard
oc-backup create # Backup now
oc-context       # Shared context inspection
oc-context summary   # Human-readable context summary
oc-context workflow  # Current workflow trace
oc-context findings  # View all agent findings
```
