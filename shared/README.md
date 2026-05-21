# OpenCode Shared Context

This directory contains the cross-agent shared context store for OpenCode.

## Files

| File | Purpose |
|------|---------|
| `context.json` | **Primary store** — all agents read/write here for workflow continuity |
| `findings/{agent}.json` | Per-agent finding files (also aggregated in context.json) |

## Structure

```
shared/
├── context.json              # Central shared context (all agents write here)
├── README.md                 # This file
└── findings/                 # Per-agent finding files
    ├── debug.json
    ├── security.json
    ├── architect.json
    ├── build.json
    ├── plan.json
    ├── review.json
    ├── test.json
    ├── general.json
    ├── refactor.json
    ├── docs.json
    ├── explore.json
    └── video-creator.json
    └── web-browser.json
    └── display-agent.json
```

## How It Works

1. **Orchestrator** reads `context.json` at workflow start
2. **Before dispatch**, orchestrator extracts relevant findings as context for the target agent
3. **Agent** reads `context.json` to get accumulated context from previous agents
4. **Agent** writes its findings to `context.json` (into its own findings array)
5. **Orchestrator** reads `context.json` after agent returns, updates workflow trace
6. **Next agent** gets the accumulated context, including the previous agent's findings

## Usage

### For Agents

```python
# Read shared context
import json, os
ctx = json.load(open(os.path.expanduser("~/.config/opencode/shared/context.json")))

# Write finding to context
ctx["findings"]["build"].append({
    "id": "build-1712345678",
    "type": "implementation",
    "summary": "Added null check in auth.js:45",
    "detail": "...",
    "severity": "info",
    "location": {"file": "src/auth.js", "line": 45},
    "timestamp": "2026-05-21T00:00:00Z"
})
json.dump(ctx, open(os.path.expanduser("~/.config/opencode/shared/context.json"), "w"), indent=2)
```

### For CLI Inspection

```bash
# Use the oc-context command
oc-context                     # Show full context
oc-context findings debug      # Show debug findings
oc-context artifacts           # Show artifacts
oc-context workflow            # Show workflow trace
oc-context clear               # Reset context (careful!)
```

---

**This directory is auto-managed by the OpenCode agent system.**
