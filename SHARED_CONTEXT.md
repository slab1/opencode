# OpenCode Shared Context System v2

This file describes the cross-agent shared context system. The actual machine-readable data lives in `shared/context.json`. This file is the human-readable reference.

---

## Overview

The shared context system enables **cross-agent memory persistence** — findings, decisions, and artifacts from one agent are automatically available to all others. This means:

- **Debug** finds a root cause → **Build** picks it up automatically
- **Architect** makes a design decision → **Build** implements accordingly
- **Security** finds a vulnerability → **Build** fixes it → **Test** writes regression tests
- **Plan** creates a task breakdown → **Build** follows the plan

## Where Context Lives

| Path | Format | Purpose |
|------|--------|---------|
| `~/.config/opencode/shared/context.json` | JSON | **Primary store**: machine-readable, agents read/write here |
| `~/.config/opencode/shared/findings/{agent}.json` | JSON | Per-agent finding files |
| `~/.config/opencode/shared/README.md` | Markdown | This directory's documentation |
| `~/.config/opencode/SHARED_CONTEXT.md` | Markdown | **This file**: human-readable reference |

## Context JSON Structure

```jsonc
{
  "meta": {
    "version": "2.0.0",
    "updated": "ISO timestamp"
  },
  "session": {
    "current_id": "ses_xxx",
    "current_title": "Session title",
    "active_agents": ["debug", "build"],
    "workflow_pattern": "bug-fix",
    "started_at": "ISO timestamp"
  },
  "findings": {
    "debug": [ /* array of finding objects */ ],
    "security": [ /* array of finding objects */ ],
    "architect": [ /* array of recommendation objects */ ],
    "build": [ /* array of implementation records */ ],
    "plan": [ /* array of task breakdowns */ ],
    "review": [ /* array of review findings */ ],
    "test": [ /* array of test records */ ],
    "general": [ /* array of research findings */ ]
  },
  "decisions": {
    "architecture": [],
    "design": [],
    "technology": [],
    "workflow": []
  },
  "artifacts": {
    "files_created": [],
    "files_modified": [],
    "files_deleted": [],
    "tests_written": [],
    "documentation_updated": []
  },
  "cross_references": [],
  "workflow_trace": []
}
```

## Agent Context Protocol

### Every Agent MUST:

1. **READ** `~/.config/opencode/shared/context.json` at session start
   - Check for findings from other agents relevant to your task
   - Check `workflow_trace` to understand what's been done so far
   - Check `artifacts` to know what files have been changed

2. **WRITE** your findings back to the shared context before finishing
   - Append to the relevant section under `findings`
   - Add entries to `artifacts` for files changed
   - Add cross-references linking your findings to other agents' findings

3. **FOLLOW** the finding schema below

### Finding Schema

Each finding object should follow this structure:

```json
{
  "id": "uuid-or-timestamp-id",
  "type": "finding|recommendation|decision|implementation|note",
  "session": "ses_xxx",
  "agent": "debug|security|architect|build|plan|review|test|general",
  "summary": "Short description (max 100 chars)",
  "detail": "Detailed description with context",
  "severity": "critical|high|medium|low|info",
  "location": {
    "file": "path/to/file.ext",
    "line": 42,
    "function": "functionName"
  },
  "references": [
    {"type": "cve|finding|decision", "id": "referenced-id", "relation": "related_to"}
  ],
  "timestamp": "2026-05-21T00:00:00Z"
}
```

## What Each Agent Contributes

| Agent | Type | Contributes |
|-------|------|-------------|
| **orchestrator** | primary | Workflow outcomes, gap detection, quality assessments, session state |
| **build** | primary | Implementation details, files modified, API changes |
| **plan** | primary | Task breakdowns, requirements analysis, roadmaps, architecture decisions |
| **pioneer** | primary | Technology research, trend analysis, experiment results, prototypes, recommendations |
| **meta-agent** | primary | Performance logs, config patches, cross-domain transfers, audit reports |
| **architect** | subagent | Design decisions, technology recommendations, trade-off analyses |
| **debug** | subagent | Root causes, error details, stack traces, reproduction steps |
| **docs** | subagent | Documentation changes, API docs updated, README updates |
| **document-agent** | subagent | Document parses, text/table extractions, OCR results, format conversions |
| **explore** | subagent | Code maps, structure discoveries, dependency findings |
| **general** | subagent | Research findings, analysis results, investigation outcomes |
| **heartbeat** | subagent | System health metrics, anomaly alerts, overdue commitments |
| **media-agent** | subagent | Image analysis, audio transcriptions, video descriptions, OCR results |
| **refactor** | subagent | Refactoring details, patterns applied, structure improvements |
| **review** | subagent | Code quality findings, best practice violations |
| **security** | subagent | Vulnerabilities, CVEs, outdated packages, risk assessments |
| **test** | subagent | Test coverage, failing tests, edge cases tested, regression tests |
| **video-creator** | subagent | Video paths, platform info, rendering results, compositions |
| **web-browser** | subagent | Extracted data, navigation results, form submissions, screenshots |
| **display-agent** | subagent | Display config, VNC connections, screenshots, resolution config |

## How Context Flows Through Workflows

### Bug Fix Workflow Example

```
1. User: "Fix the login bug"
2. Orchestrator → Debug:
   [Passes: current shared context]
3. Debug identifies root cause → SAVES to context.json
   {
     "findings": { "debug": [{ "summary": "Null pointer in auth.js:45",
                                "root_cause": "Missing null check on user object" }] }
   }
4. Orchestrator → Build:
   [Passes: Debug's findings from context.json]
5. Build implements fix → SAVES to context.json
   {
     "artifacts": { "files_modified": ["src/auth.js"] },
     "findings": { "build": [{ "summary": "Added null check in auth.js:45" }] }
   }
6. Orchestrator → Test:
   [Passes: Debug's findings + Build's changes from context.json]
7. Test writes regression test → SAVES to context.json
   {
     "artifacts": { "tests_written": ["test/auth.test.js"] },
     "findings": { "test": [{ "summary": "Regression test for null pointer in auth" }] }
   }
8. Orchestrator verifies all quality gates pass
```

## CLI Quick Reference

```bash
# View the full shared context
python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/.config/opencode/shared/context.json'))); print(json.dumps(c, indent=2))"

# View findings from a specific agent
python3 -c "
import json,os
c=json.load(open(os.path.expanduser('~/.config/opencode/shared/context.json')))
agent='debug'
print(json.dumps(c['findings'].get(agent, []), indent=2))
"

# View workflow trace
python3 -c "
import json,os
c=json.load(open(os.path.expanduser('~/.config/opencode/shared/context.json')))
print(json.dumps(c['workflow_trace'], indent=2))
"
```

## Benefits

| Before (v1) | After (v2) |
|-------------|------------|
| Manual markdown file, easily stale | Structured JSON, machine-readable |
| No agent reads or writes it | Every agent reads/writes automatically |
| No context handoff in delegation | Orchestrator passes accumulated context |
| Static placeholder data | Real data populated by agents |
| Flat structure | Per-agent findings + aggregated view |
| No cross-references between agents | Cross-references link findings across agents |

---

**This file is the human-readable reference for the shared context system.**
**Agents: Use `~/.config/opencode/shared/context.json` (JSON) for programmatic access.**
**CLI tool (future): `oc-context` for quick inspection.**
