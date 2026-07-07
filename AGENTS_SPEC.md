# AGENTS.md — Discoverability Protocol Specification

**Status:** Draft v0.1  
**Last Updated:** 2026-06-20  
**Inspirations:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) dev guide (NousResearch, 189K ⭐), [agentsmd/agents.md](https://github.com/agentsmd/agents.md) format (22K ⭐)

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Purpose

An `AGENTS.md` file is a **structured machine-readable map file** that enables AI agents (LLM-based coding agents) to efficiently navigate and understand a codebase. It answers: *"What files exist here, what do they do, and how should agents interact with them?"*

---

## 2. File Location Conventions

### 2.1 Root `AGENTS.md`

Every project root SHOULD contain an `AGENTS.md` that describes the top-level directory structure, conventions, and entry points for AI agents.

### 2.2 Per-Directory `AGENTS.md`

Any subdirectory with substantial logic or multiple files MAY contain its own `AGENTS.md` to provide a focused map for agents operating in that scope.

**Examples from this project:**

| Path | Scope |
|------|-------|
| `~/.config/opencode/AGENTS.md` | Root map — entire OpenCode Platform Manager |
| `~/.config/opencode/platforms/AGENTS.md` | Platform adapters — social media adapter system |
| `~/.config/opencode/shared/AGENTS.md` | Shared context — cross-agent communication system |
| `~/.config/opencode/shared/eval/AGENTS.md` | Eval system — agent benchmarking |
| `~/.config/opencode/shared/golden/AGENTS.md` | Golden datasets — test fixtures |

### 2.3 Agent Config Files

Agent definition files SHOULD follow the convention `agents/<name>.md` (not `AGENTS.md`) and use the XML tag schema defined in §4. See `~/.config/opencode/agents/` for examples (orchestrator.md, meta-agent.md, etc.).

---

## 3. Directory Tree Format

### 3.1 Specification

The directory tree section MUST use the Unicode box-drawing glyphs `├──`, `└──`, and `│`.

Each line follows this pattern:

```
<indent><prefix> <name>  ← <description>
```

- `<indent>`: `│   ` for each depth level
- `<prefix>`: `├──` for non-last entries, `└──` for the last entry at each level
- `<name>`: the file or directory name (trailing `/` for directories)
- `← <description>`: brief summary of the file's purpose

### 3.2 Example

```
~/.config/opencode/
├── AGENTS.md                  ← THIS FILE — root map + dev guide
├── opencode.jsonc             ← Main OpenCode config (MCP servers, permissions, plugins)
├── agents/
│   ├── human.md               ← Agent config: Human analysis
│   ├── platform-manager.md    ← Agent config: social media management
│   └── ... (20+ other agents)
├── platforms/
│   ├── AGENTS.md              ← Platform manager system docs
│   ├── post.sh                ← Cross-platform posting script
│   └── tokens/                ← API tokens (chmod 600, gitignored)
└── shared/
    ├── context.json            ← Cross-agent shared context
    └── AGENTS.md               ← Shared context system docs
```

---

## 4. Frontmatter Schema (YAML)

Agent config files (`agents/<name>.md`) MUST begin with YAML frontmatter between `---` delimiters.

```yaml
---
description: <string>            # REQUIRED: One-line purpose of this agent
mode: primary | secondary        # REQUIRED: primary for user-facing agents
permission:
  edit: allow | ask              # REQUIRED: file editing permission
  bash: allow | ask              # REQUIRED: shell execution permission
  task: allow | ask              # OPTIONAL: subagent delegation permission
  todowrite: allow | ask         # OPTIONAL: task tracking permission
  webfetch: allow | ask          # OPTIONAL: URL fetching permission
  websearch: allow | ask         # OPTIONAL: web search permission
  question: allow | ask          # OPTIONAL: user prompting permission
---
```

---

## 5. XML Tag Conventions

Agent config files define sections using XML-style tags. Tags are NOT actual XML (no namespace, no schema validation) — they are markdown delimiters for section segmentation that agents can parse.

### 5.1 Tag Registry

| Tag | Purpose | Example Content |
|-----|---------|-----------------|
| `<role>` | Agent identity — what the agent IS | "You are the Orchestrator Agent..." |
| `<context>` | Environment, startup steps, constraints | "You are the default entry point..." |
| `<capabilities>` | Bulleted list of what the agent can do | "Task Decomposition", "Quality Gates" |
| `<rules>` | Behavioral rules the agent MUST follow | "Be systematic", "Be thorough" |
| `<workflow>` | Step-by-step procedures for tasks | "The Execution Loop" with numbered steps |
| `<shared-context>` | Cross-agent state management protocol | "READ context.json first" |
| `<memory>` | Persistent memory across sessions | "memory_search tool", "oc-memory save" |
| `<skills>` | Loadable skills the agent can activate | "multi-agent-orchestration", "system-audit" |
| `<best-practices>` | Non-binding guidance for quality work | "Decompose before dispatching" |
| `<task-tracking>` | Outcome logging commands | "python3 -m opencode_improvement.track ..." |

### 5.2 Optional Tag Attributes

Tags MAY carry a `type` attribute to sub-categorize content:

```xml
<rules type="fast-path">
Use FAST PATH for: simple tasks (explain, read, small edit).
</rules>

<rules type="invocation">
- You can invoke ALL agents (build, plan, architect...)
- Maximum invocation depth: 5 levels
</rules>
```

### 5.3 Tag Ordering

Tags SHOULD appear in this order within an agent config:

1. `frontmatter` (YAML)
2. `<role>`
3. `<context>`
4. `<shared-context>` (if applicable)
5. `<memory>` (if applicable)
6. `<capabilities>`
7. `<skills>` (if applicable)
8. `<rules>`
9. `<workflow>` / `<workflow-types>`
10. `<best-practices>`
11. `<task-tracking>`

### 5.4 Schema for Select Tags

**`<capabilities>`:**
```
<capabilities>
### <Category Name>
- **<Capability>**: <description>
- **<Capability>**: <description>

### <Another Category>
- **<Capability>**: <description>
</capabilities>
```

**`<workflow>`:**
```
<workflow>
## <Workflow Title>

### N. <STEP NAME>
<instruction block>

### N+1. <NEXT STEP>
<instruction block>
</workflow>
```

**`<gap-detection-checklist>`:**
```
<gap-detection-checklist>
| Category | What to Check |
|----------|---------------|
| **<Category>** | <check description> |
| **<Category>** | <check description> |
</gap-detection-checklist>
```

---

## 6. Agent Discovery Protocol

### 6.1 Entry Point

When an AI agent first encounters a codebase, it SHOULD:

1. **Look for `AGENTS.md` in the root directory** of the project
2. Read it to understand the top-level map, key files, and conventions
3. Navigate into subdirectories and check for their own `AGENTS.md` files

### 6.2 Recursive Discovery

Agents navigating a directory tree SHOULD check each subdirectory they enter for a local `AGENTS.md`. When found, the agent MUST read it before proceeding deeper.

### 6.3 Agent Config Discovery

When an agent needs to understand another agent's capabilities or rules, it SHOULD:
1. Read `agents/<name>.md` for the target agent
2. Extract the `<role>`, `<capabilities>`, and `<rules>` sections
3. Use the `permission` frontmatter to determine what the agent is allowed to do

### 6.4 Skill Discovery

When an agent needs specialized methodology, it SHOULD:
1. Check the `<skills>` section of its own config
2. Load the matching skill via the native `skill` tool
3. If no matching skill is listed, search the shared skills catalog via the `skill-recommender` skill

### 6.5 Cross-Agent Context

When an agent participates in a multi-agent workflow, it MUST:
1. Check `~/.config/opencode/shared/context.json` for accumulated decisions, artifacts, and workflow trace
2. Write its own findings back before finishing
3. Follow the schema defined in the relevant `<shared-context>` section

---

## 7. Formal Examples

### Example 1: Root AGENTS.md (OpenCode Platform Manager)

```markdown
# OpenCode Platform Manager — AGENTS.md

This file is a map for AI agents working with the OpenCode Platform Manager system.

**Inspired by:** Hermes Agent dev guide (NousResearch, 189K ⭐) + agentsmd/agents.md format (22K ⭐)

---

## Directory Map

```
~/.config/opencode/
├── AGENTS.md                  ← THIS FILE — root map + dev guide
├── opencode.jsonc             ← Main OpenCode config
├── agents/                    ← Agent definitions (20+ agents)
├── platforms/                 ← Social media platform system
├── shared/                    ← Cross-agent shared context
└── scripts/                   ← Utility scripts
```

---

## Key Commands

| Action | Command |
|--------|---------|
| Post immediately | `bash post.sh --text "..."` |
| Schedule a post | `python3 calendar.py add --text "..."` |
```

### Example 2: Agent Config (Orchestrator)

```markdown
---
description: Master orchestrator that decomposes tasks and dispatches agents
mode: primary
permission:
  edit: allow
  bash: ask
  task: allow
---

<role>
You are the Orchestrator Agent — the highest-level coordinator.
</role>

<context>
You are the default entry point for all user requests.
</context>

<capabilities>
### Orchestration
- **Task Decomposition**: Break complex requests into concrete subtasks
- **Agent Dispatching**: Route work to the optimal agent
</capabilities>

<rules>
- Be systematic
- Be thorough
</rules>
```

### Example 3: Minimal AGENTS.md (Per-Directory)

```markdown
# adapters/ — Platform Adapters

## Directory

```
adapters/
├── AGENTS.md              ← This file
├── twitter/               ← Twitter/X adapter
├── mastodon/              ← Mastodon adapter
└── bluesky/               ← Bluesky adapter
```

## Adding a New Adapter

1. Create `adapters/<name>/`
2. Add `__init__.py` with exports: `PLATFORM`, `post()`, `validate_credentials()`
3. Test with `post.sh --adapter <name> --dry-run`
```

---

## 8. References

- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** (189K ⭐) — Dev guide pattern with orchestrator agents, subagent delegation, and capability-based routing
- **[agentsmd/agents.md](https://github.com/agentsmd/agents.md)** (22K ⭐) — Directory tree mapping convention with `├──` box-drawing format and `←` descriptions
- **[HyperAgents (Meta, 2026)](https://arxiv.org/abs/2502.04543)** — Metacognitive strategy tracking pattern (strategy log schema, confidence calibration)
- **[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)** — Key words for use in RFCs to Indicate Requirement Levels
- **[DeepEval](https://github.com/confident-ai/deep-eval)** (7K ⭐) — Structured golden datasets for agent evaluation
