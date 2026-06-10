---
name: multi-agent-orchestration
description: Coordinate multiple agents to complete complex tasks. Decompose work, dispatch in parallel where possible, evaluate outputs, detect gaps, iterate until quality. Used by the orchestrator agent and any task requiring multiple specialized agents.
license: MIT
compatibility: opencode>=1.16.0
---

# Multi-Agent Orchestration

The pattern for **coordinating multiple agents** to complete complex tasks. Inspired by OpenCode's orchestrator, HyperAgents, and Anthropic's subagent-driven-development.

## The Core Loop

```
1. DECOMPOSE → 2. DISPATCH → 3. EVALUATE → 4. DETECT GAPS → 5. ITERATE
   ↑                                                              ↓
   └──────────────────── QUALITY GATE PASSED ←────────────────────┘
```

### 1. Decompose
Break the user's request into concrete subtasks:
- Identify dependencies (what blocks what)
- Identify parallel opportunities (what can run concurrently)
- Identify the optimal agent for each subtask
- Estimate effort (small / medium / large)

### 2. Dispatch
For each subtask:
- **Choose agent** by capability match
- **Pass context** from previous agents in the workflow
- **Hint relevant skills** the target agent should load
- **For independent tasks**: dispatch in parallel
- **For long-running tasks**: send to background (v1.16.2+)
- **For multi-step plans**: use `subagent-driven-development` pattern

### 3. Evaluate
After each agent returns:
- Check outputs against the task spec
- Verify the agent followed its own rules
- Capture concrete evidence (files, tests, screenshots)
- Update shared context

### 4. Detect Gaps
Common gaps to look for:
- Missing tests
- Missing documentation
- Missing error handling
- Missing security review
- Missing performance check
- Missing accessibility check
- Inconsistent style with rest of codebase

### 5. Iterate
If gaps found:
- Re-dispatch the specific agent with explicit gap description
- Don't accept partial work — iterate until quality gates pass
- Use the original agent for revisions, not a new one (preserves context)

## Dispatch Patterns

### Sequential (with context flow)
```
plan → architect → build → test → review
  ↓        ↓         ↓       ↓       ↓
  findings flow forward as context for next step
```

### Parallel (independent)
```
            ┌→ build
research ───┼→ docs   (all read research findings)
            └→ test
```

### Background + Main Thread
```
main: continue working on X
      ↓
background: general research task (results come back when ready)
```

### Subagent-Driven (multi-task plans)
```
plan
  ├─ dispatch subagent 1 → spec review → quality review → next
  ├─ dispatch subagent 2 → spec review → quality review → next
  └─ dispatch subagent 3 → spec review → quality review → done
```

## Quality Gates

Hard gates (must pass):
- [ ] Code compiles / runs
- [ ] Tests pass
- [ ] No critical security issues
- [ ] Files saved to expected locations

Soft gates (nice to have):
- [ ] Style matches codebase
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Accessibility considered

## Context Injection

When delegating, include:
```yaml
workflow: "feature-implementation"
step: 2 of 5
previous_agents: [plan, architect]
relevant_findings:
  - from: architect
    summary: "Use Postgres + Drizzle ORM"
    key_decision: "..." 
files_modified: [src/db/schema.ts, src/api/users.ts]
quality_gates_passed: [compile]
remaining_steps: [build, test, review]
```

## Agent Selection Heuristics

| Task type                          | Best agent       |
|------------------------------------|------------------|
| Code implementation                 | `build`          |
| Code planning/analysis              | `plan`           |
| System architecture                 | `architect`      |
| Bug investigation                   | `debug`          |
| Documentation                      | `docs`           |
| Codebase search                     | `explore`        |
| Research, comparisons              | `general` / `pioneer` |
| Code refactoring                   | `refactor`       |
| Code review                        | `review`         |
| Security audit                     | `security`       |
| Test writing                       | `test`           |
| System self-improvement            | `meta-agent`     |

## Fast Path vs Full Workflow

**Fast path** (do directly):
- "Explain X"
- "Read file Y"
- "Edit this line"
- "Search for Z"

**Full workflow** (orchestrate):
- "Build a feature"
- "Fix this bug"
- "Refactor this module"
- "Audit this system"

## Skills to Load

- `subagent-driven-development` — for multi-task plans
- `cross-domain-transfer` — when finding best agents/patterns
- `metacognitive-tracking` — for the meta-agent to track improvement strategies


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach
