# Platform Manager System — AGENTS.md

This directory contains all scripts and tools for the OpenCode Platform Manager.
Together they form a complete, free, self-hosted social media management system.

**Inspired by:** Hermes Agent plugin architecture (NousResearch, 189K ⭐) + agentsmd/agents.md (22K ⭐)

---

## Quick Reference

| File | Purpose | Language | Key Dependencies |
|------|---------|----------|------------------|
| `AGENTS.md` | THIS FILE — agent map for platforms/ | md | — |
| `setup-wizard.sh` | Interactive account setup for 11 platforms | bash | curl, python3 |
| `post.sh` | Cross-platform posting with hooks, confirm, dry-run | bash | curl, backend API key |
| `calendar.py` | Content calendar with kanban board & scheduling | python3 | subprocess (calls post.sh) |
| `analytics.py` | Analytics reporting, best times, growth, learning | python3 | urllib, backend API |
| `content-gen.py` | AI content generation (images, video, text) | python3 | requests, localhost:7777 |
| `media-optimizer.py` | Auto-resize media per platform dimensions | python3 | Pillow |
| `adapters/` | Pluggable platform adapter modules (auto-discovered) | python3 | — |
| `hooks/` | Pre/post publishing hook scripts (auto-run) | bash | — |
| `tokens/` | API tokens directory (chmod 600) | — | — |
| `config.yaml` | User preferences (not secrets, not connection config) | yaml | — |
| `adk_pipeline/` | ADK Go 2.0 content pipeline: graph-based workflow agent | Go | ADK v2 |

---

## Supported Platforms (11)

Facebook, Instagram, X/Twitter, TikTok, YouTube, LinkedIn, Pinterest, Threads, Bluesky, Mastodon, Google Business Profile

---

## Capability Footprint Ladder

When adding new capability to this system, choose the **least permanent surface**:

| Rung | Surface | Use When | Example |
|------|---------|----------|---------|
| 1 | **Extend existing script** | Adding a flag/option to post.sh | `post.sh --thread` |
| 2 | **New CLI script** | New independent capability | `content-gen.py` |
| 3 | **Config-gated feature** | Only needed when backend is configured | `--backend trypost` |
| 4 | **Pluggable adapter** | New platform or service integration | `adapters/bluesky/` |
| 5 | **MCP server** | External tool integration | BulkPublish MCP |
| 6 | **Core change** | Modifying shared infrastructure | Token storage refactor |

---

## Backend Abstraction

The system supports 4 backends for actual API posting:
- **BulkPublish** (recommended, cloud, 100 req/day free)
- **TryPost** (self-hosted, AGPL-3.0)
- **BrightBean Studio** (self-hosted, AGPL-3.0)
- **Mixpost** (paid, $79 one-time)

Backend is configured in `backend.json`. Post scripts route through the configured backend.

---

## Agent Workflow

When interacting with this system as an AI agent:

1. **Plan** — Understand what the user wants (post, schedule, analyze, generate)
2. **Check config** — Read `backend.json` and `accounts.json` to know what's connected
3. **Generate media** — Use `content-gen.py` if images/videos are needed
4. **Optimize** — Use `media-optimizer.py` to resize for target platforms
5. **Create calendar entry** — Use `calendar.py add` for scheduled posts
6. **Post or schedule** — Use `post.sh` or `calendar.py process`

---

## Security

- **`post.sh --confirm`** — By default, real posts (non-dry-run) require `y/N` confirmation
- **`post.sh --yes`** — Skip confirmation for batch/automated use
- **`post.sh --dry-run`** — Preview mode, always safe to use
- **Hooks `hooks/pre-post.sh`** can abort posts by returning non-zero exit code
- API tokens must always be stored in `tokens/` with `chmod 600`
- Never read token files into AI sessions

## Kanban Workflow

`calendar.py` tracks posts through a visual pipeline:

```
📝 Draft → 📅 Scheduled → ✅ Posted → 📊 Analyzed → 📦 Archived
```

| Command | Action |
|---------|--------|
| `calendar.py add --status draft` | Create a post in draft state |
| `calendar.py kanban` | Show board grouped by status |
| `calendar.py status <id> --set posted` | Move a post to a new column |
| `calendar.py process` | Posts due posts (scheduled → posted) |

## Hook System

`post.sh` automatically runs hooks before and after each platform post:

- **`hooks/pre-post.sh`** — Validation, enrichment, abort logic. Sets `PLATFORM`, `TEXT`, `MEDIA`, etc. env vars.
- **`hooks/post-post.sh`** — Logging, notifications, analytics. Gets `POST_ID`, `PLATFORM_OK`, etc.

Hooks are optional — missing hooks are silently skipped. Hook returning non-zero = abort for pre-post.

## Editing Guidelines

- All scripts should support `--help` and `--dry-run` flags
- New platform additions → create `adapters/<name>/` module (rung 4), don't edit post.sh
- New content features → extend content-gen.py (rung 1), don't create new scripts
- API tokens must always be stored in `tokens/` with `chmod 600`
- Log all posting operations to `posts.jsonl`
- Track performance via `python3 -m opencode_improvement track`
- Update this file when directory structure or workflows change

## ADK Go 2.0 Content Pipeline

A graph-based workflow agent under `adk_pipeline/` that calls real system scripts.

```
content_gen → optimize_media → post_all (dynamic node, per-platform loop)
                               → post.sh (dry-run or live)
                             → summarize → finalize → posts.jsonl + analytics.py
```

Built with ADK Go 2.0 (`google.golang.org/adk/v2`). Uses a **dynamic node** to iterate over the platform list, calling `post.sh` for each. HITL approval pauses the graph before live posts.

| Action | Command |
|--------|---------|
| Build | `cd ~/.config/opencode/platforms/adk_pipeline && go build -o pipeline .` |
| Run console | `./pipeline console` |
| Pipe input | `echo "your prompt" \| ./pipeline console` |
| Web UI + API | `./pipeline web --port 8080 api webui` (sublaunchers as positional args) |
| API only | `./pipeline web --port 8080 api` |
| Background daemon | `make start` / `make stop` (tmux-free nohup wrapper) |
| Config | `ADK_PIPELINE_DRY_RUN=true\|false` (default: auto-detect from backend.json) |
| Check API | `curl http://localhost:8080/api/list-apps` (returns `["content_pipeline"]`) |

**What it integrates with:**

| System | How |
|--------|-----|
| `post.sh` | Called via `os/exec` per platform with `--dry-run` or `--yes` |
| `posts.jsonl` | Pipeline outputs logged in same format as post.sh |
| `analytics.py` | Triggered on completion (`fetch` mode) |
| `backend.json` | Auto-detects if backends are ready for live posting |
| `accounts.json` | Reads configured platforms automatically |

**Patterns demonstrated:** dynamic node with `RunNode` loop, HITL via `ResumeOrRequestInput`, typed generics, sub-branch isolation per platform child, sequential + dynamic composition. Same `agent.Agent` interface works with any runner.
