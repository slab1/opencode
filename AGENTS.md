# OpenCode Agents Documentation

This document describes the agent architecture, configuration syntax, and best practices for OpenCode agents.

## Agent Types

### Primary Agents
Primary agents interact directly with users in the main conversation.
- **orchestrator** - Master coordinator: decomposes tasks, dispatches agents, evaluates outputs, detects gaps, iterates until success
- **build** - Implements features and writes code
- **plan** - Analyzes code and creates implementation plans
- **pioneer** - Research & Innovation: explores cutting-edge tech, trends, prototypes, and provides actionable recommendations
- **compaction** (native) - Summarizes conversation context
- **summary** (native) - Generates session summaries
- **title** (native) - Creates session titles

### Subagents
Subagents are invoked via the `task` tool for specialized work.
- **architect** - System architecture and technology decisions
- **debug** - Bug investigation and diagnostics
- **docs** - Documentation writing and maintenance
- **explore** - Fast codebase exploration
- **general** - General-purpose research and execution
- **refactor** - Code refactoring and optimization
- **review** - Code quality reviews
- **security** - Security audits and vulnerability checks
- **test** - Test writing and coverage improvement
- **video-creator** - Programmatic video creation across platforms
- **web-browser** - Full browser automation (navigate, click, fill forms, book flights)

### Invocation Rules
- **Primary agents** (orchestrator, build, plan, pioneer) can invoke subagents via the `task` tool
- **Orchestrator** can invoke ALL agents (including video-creator, web-browser) and coordinates multi-agent workflows
- **Subagents** can ONLY invoke other agents when explicitly delegated by the orchestrator or a primary agent (max depth 3)
- **Max recursion depth**: 3 levels for build/plan, 5 levels for orchestrator

## Permission Syntax

### Shorthand Syntax
Use shorthand when the permission is uniform across all patterns:

```yaml
permission:
  edit: deny        # Always deny edit
  bash: ask         # Always ask before bash
  todowrite: allow  # Always allow todowrite
```

**Valid values**: `allow`, `ask`, `deny`

### Object Syntax (Granular Control)
Use object syntax when you need pattern-specific permissions:

```yaml
permission:
  bash:
    "*": ask                    # Ask for any command by default
    "git log*": allow          # Always allow git log
    "git diff*": allow         # Always allow git diff
    "npm audit*": allow        # Always allow npm audit
    "npx snyk*": allow        # Always allow npx snyk
```

**Pattern matching**: Uses glob patterns where `*` matches anything.

### Special Permissions

#### external_directory
Controls access to directories outside the project:

```yaml
permission:
  external_directory:
    "*": ask                                              # Ask for any external dir
    "/home/.local/share/opencode/tool-output/*": allow    # Allow tool output dir
    "/data/user/0/com.foxdebug.acode/cache/opencode/*": allow  # Allow cache dir
```

#### webfetch
Controls fetching content from URLs:

```yaml
permission:
  webfetch:
    "*": ask          # Ask before fetching any URL
```

#### doom_loop
Controls agent iteration limits:

```yaml
permission:
  doom_loop: ask      # Ask before allowing agent to loop
```

## Tool Reference

### Available Tools
| Tool | Description | Used By |
|------|-------------|---------|
| **read** | Read file contents | All agents (default allow) |
| **grep** | Search file contents with regex | All agents (default allow) |
| **glob** | Find files by pattern | All agents (default allow) |
| **edit** | Edit existing files | build, docs, refactor, test |
| **write** | Write new files | build, docs, refactor, test |
| **bash** | Run shell commands | build, debug, refactor, test, review, security, architect |
| **todowrite** | Create/manage todo lists | plan, general, orchestrator, pioneer |
| **task** | Invoke subagents | orchestrator, build, plan, pioneer |
| **webfetch** | Fetch URL content | docs, security, architect |
| **websearch** | Search the web | architect, debug, security |
| **question** | Ask user questions | build, plan (with restrictions) |
| **skill** | Load specialized skills | All agents (context-dependent) |

**Note**: `list` is NOT a valid tool. Use `glob` for file pattern matching.

## Configuration File Format

Agent configs are stored in `/home/.config/opencode/agents/` as Markdown files:

```markdown
---
description: Brief description of the agent
mode: primary|subagent
permission:
  edit: deny|ask|allow
  bash: deny|ask|allow
  # ... other permissions
---

System prompt for the agent...
```

### Frontmatter Fields
- `description` - Brief description shown in `opencode agent list`
- `mode` - `primary` or `subagent`
- `permission` - Permission rules (shorthand or object syntax)

## Built-in vs Configurable Agents

### Native/Built-in Agents (not configurable via .md files)
- compaction
- summary
- title

These agents have `native: true` in their configuration and are managed internally by OpenCode.

### Configurable Agents (can be customized via .md files)
- orchestrator
- build
- plan
- pioneer
- architect
- debug
- docs
- explore
- general
- refactor
- review
- security
- test
- video-creator
- web-browser
- display-agent

## Best Practices

1. **Least Privilege**: Start with `deny`, add `ask` or `allow` only as needed
2. **Clear Roles**: Each agent should have a single, well-defined purpose
3. **Consistent Naming**: Use the tool names exactly as defined (e.g., `glob` not `list`)
4. **Pattern Specificity**: In object syntax, order matters - first match wins
5. **Include all recommended sections**: Every agent config should have `<role>`, `<context>`, `<capabilities>`, `<rules>`, `<workflow>`, `<shared-context>`, `<memory>`, and `<task-tracking>` — the `opencode_improvement` module audits for these
6. **Documentation**: Update this file when adding new agents or changing permissions

## AgentInteraction Flow

```
User
  |
  v
Orchestrator Agent (default entry point)
  |
  +---> Handle directly (simple tasks)
  |
  +---> Delegate to build/plan/pioneer (implementation/research tasks)
  |         |
  |         +---> task tool ---> Subagent (architect/debug/docs/etc)
  |                                   |
  |                                   +---> Returns results to build/plan
  |                                             |
  |                                             v
  |                                       Orchestrator evaluates
  |                                             |
  +---> Dispatch full workflow (complex tasks)  |
            |                                   |
            +---> Multiple agents in sequence   |
            +---> Gap detection after each      |
            +---> Re-dispatch if needed --------+
                                                  |
                                                  v
                                          Final quality gate
                                                  |
                                                  v
                                            User receives result
```

### Recursive Invocation
Subagents can invoke other agents ONLY when explicitly delegated by the orchestrator or a primary agent:
- **Max depth**: 3 levels for build/plan/pioneer delegations, 5 levels for orchestrator delegations
- **Depth tracking**: Delegator must include current depth in the task prompt
- **Stop condition**: If max depth reached, report back with what still needs to be done

## Memory & Continuity System

OpenCode has a three-tier memory system for cross-session continuity:

### Tier 1: Daily Notes (`memory/YYYY-MM-DD.md`)
Auto-saved via the `opencode-memory-plugin` before session compaction.
Contains raw findings, decisions, and artifacts from each session.
Use `oc-memory save` to manually save, `oc-memory list` to see recent notes.

### Tier 2: Shared Context (`shared/context.json`)
Machine-readable cross-agent context store.
Agents read at start and write findings at finish.
Persists across sessions within a project.

### Tier 3: Commitments (`shared/commitments.json`)
Lightweight follow-up tracking for things the agent should check back on.
Create with `oc-commitments add --desc "..." --due "4h"`.
Check with `oc-commitments list`, mark done with `oc-commitments done <id>`.

### Agent Prompt Template

When building system prompts, include:

> You have persistent memory across sessions:
> - `memory_search` tool finds relevant past context
> - `oc-memory save` persists important findings
> - `oc-commitments` tracks follow-ups the agent promises to check
> - `oc-doctor --fix` auto-repairs any system issues

### Doctor Command

`oc-doctor` diagnoses common issues:
```bash
oc-doctor                    # Full health check
oc-doctor --fix              # Auto-fix common issues
oc-doctor --check ld_preload # Single check
oc-doctor --json             # Machine-readable output
```

Checks: context, config, memory, plugins, mcp, ld_preload, permissions, api_keys, system.

## Shared Context System

All agents participate in the **cross-agent shared context system** for memory persistence and workflow continuity.

### How It Works

1. **Orchestrator** initializes the shared context at workflow start (`shared/context.json`)
2. **Each agent** reads `shared/context.json` at session start to get accumulated context from previous agents
3. **Each agent** writes findings back to `shared/context.json` before finishing
4. **Orchestrator** passes accumulated context between sequential agents during delegation

### Key Files

| File | Purpose |
|------|---------|
| `shared/context.json` | Machine-readable JSON store — primary context source |
| `shared/findings/*.json` | Per-agent finding files |
| `SHARED_CONTEXT.md` | Human-readable reference documentation |

### Agent Responsibilities

- **Primary agents** (orchestrator, build, plan, pioneer): Manage context flow, include context in delegations
- **Subagents**: Read context at start, write findings before finishing
- All agents follow the finding schema documented in `SHARED_CONTEXT.md`

### CLI Tool

```bash
oc-context summary     # Quick human-readable summary
oc-context findings    # View all agent findings
oc-context workflow    # View workflow trace
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|------|-----------|
| Agent can't edit files | Missing `edit: allow` | Add to permissions |
| Agent can't run commands | `bash: deny` | Change to `ask` or add selective permissions |
| "Invalid tool" errors | Using `list` instead of `glob` | Use `glob` for file patterns |
| Agent not found | Missing config file | Create `.md` file in agents directory |

### Validation

Check agent configuration:
```bash
opencode debug agent <agent-name>
opencode agent list
```
