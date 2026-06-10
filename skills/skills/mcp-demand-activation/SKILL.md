---
name: mcp-demand-activation
description: Toggle MCP servers on/off on demand for agents that need heavy MCPs (higgsfield, firecrawl, pdf-mcp). Use when an agent needs a specific MCP that's currently disabled, or when finishing a task that used a heavy MCP. Reduces startup time and resource usage by keeping heavy MCPs off until needed.
license: MIT
compatibility: opencode>=1.16.0
---

# MCP Demand Activation

Heavy MCPs (those that require credentials, long startup, or network access) should be **disabled by default** and **enabled on demand** when an agent actually needs them.

## Why

- **Faster startup**: opencode connects to all enabled MCPs at boot
- **Fewer auth prompts**: higgsfield requires OAuth on first connect
- **Lower memory**: each connected MCP holds state and tool definitions
- **Less noise**: `opencode mcp list` is more useful when most are off

## Heavy MCPs (the demand-activation set)

| MCP | Why heavy | When to enable |
|-----|-----------|----------------|
| `higgsfield` | Remote, OAuth, 30+ models | Video/image generation tasks |
| `firecrawl` | External API, credentials | Web scraping, deep crawl, structured extraction |
| `pdf-mcp` | Local but starts slowly, large tool surface | PDF processing, hybrid search, OCR |
| `websearch` | External API | (already on; cheap and useful) |

## The script

`oc-mcp-toggle` is at `/home/.config/opencode/scripts/oc-mcp-toggle.sh` (symlinked to `/usr/local/bin/oc-mcp-toggle`).

```bash
oc-mcp-toggle list          # show current state
oc-mcp-toggle <name> on     # enable one MCP
oc-mcp-toggle <name> off    # disable one MCP
oc-mcp-toggle demand        # disable heavy MCPs, keep light ones on
oc-mcp-toggle all-on        # enable all
oc-mcp-toggle all-off       # disable all
```

## Workflow

### 1. Check what you need
Before starting work, list current MCP state:
```bash
oc-mcp-toggle list
```

### 2. Enable what you need
```bash
oc-mcp-toggle higgsfield on   # for video/image gen
oc-mcp-toggle firecrawl on    # for web scraping
oc-mcp-toggle pdf-mcp on      # for PDF processing
```

### 3. Reload opencode
MCP config changes take effect on next session. If you need the MCP mid-session, tell the user to restart, or work with what's available.

### 4. Disable when done (optional)
If you're cleaning up before ending the session, disable heavy MCPs:
```bash
oc-mcp-toggle higgsfield off
oc-mcp-toggle firecrawl off
```

## When to use this skill

- You are about to call a heavy MCP that's currently disabled
- The user reports an MCP is failing — check if it's actually enabled
- You're setting up a fresh environment and want to start in demand mode
- The user asks "which MCPs are running?"

## When NOT to use

- Light MCPs (context7, filesystem, websearch) — leave them on
- Mid-task — toggling requires a session restart
- During an interactive session where the user can't restart

## Integration with agents

- `pioneer` — enable higgsfield for media research
- `video-creator` — enable higgsfield (always on for this agent's tasks)
- `document-agent` — enable pdf-mcp for PDF tasks, disable when not needed
- `web-browser` — enable firecrawl for deep scraping
- `meta-agent` — can audit and recommend demand mode
