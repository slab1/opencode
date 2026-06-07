---
name: cross-domain-transfer
description: Transfer capabilities from high-performing OpenCode agents to lower-performing ones. Compare success rates, extract structural patterns, validate before applying. Used by the meta-agent for Phase 3 self-improvement cycles.
license: MIT
compatibility: opencode>=1.16.0
metadata:
  inspired_by: HyperAgents (Meta, 2026)
---

# Cross-Domain Transfer

The **Phase 3** self-improvement operation in the meta-agent improvement cycle. Transfer successful patterns from a high-performer to a low-performer to lift system-wide performance.

## The Core Idea

Different agents solve different problems, but **structural patterns** (capability section count, workflow types, rules clarity) correlate with success rates across all agents. By lifting low-performers to match high-performers structurally, we lift their success rate.

This is the metacognitive principle from **HyperAgents (Meta, arXiv:2603.19461)**: improvements at the meta-level transfer across domains and accumulate across runs.

## How It Works

### Step 1: Identify candidates
Run `python3 -m opencode_improvement report` to compare success rates.

| Agent         | Success Rate | Capabilities |
|---------------|--------------|--------------|
| `pioneer`     | 92%          | 6            |
| `web-browser` | 88%          | 5            |
| `general`     | 68%          | 3            |  ← transfer target
| `debug`       | 71%          | 3            |  ← transfer target

### Step 2: Extract patterns
Read the high-performer's `<capabilities>` and `<workflow-types>` sections. Note structural elements:
- 6 capability sections (vs 3)
- 4 workflow types (vs 1)
- Concrete examples in capability descriptions
- 7+ rules (vs 3)

### Step 3: Analyze gap
Read the low-performer's config. Identify missing elements:
- Missing workflow types
- Vague capability descriptions
- Missing best-practices section

### Step 4: Validate transfer
Before applying, ask:
- Does the pattern fit the target agent's domain?
- Will the new content be too generic to be useful?
- Does the target agent have the tools needed?

### Step 5: Apply
Edit the target `.md` file. Add the transferred capabilities, workflow types, and rules. Keep the agent's existing domain-specific content.

### Step 6: Log
Add to `findings.meta-agent.transfer_attempts`:
```json
{
  "from": "pioneer",
  "to": "general",
  "capability": "Structured Research Workflows",
  "expected_outcome": "general now has 6 capability sections matching pioneer's structure",
  "status": "applied"
}
```

## Transfer Heuristics

- **High → Low with >2x capability gap**: Strong transfer candidate
- **High → Low with same domain**: Highly applicable
- **High → Low cross-domain**: Risk of context mismatch; validate carefully
- **Same-tier agents**: Peer learning — exchange useful patterns

## Track Success

After applying a transfer, run a follow-up audit and compare:
- Did success rate improve?
- Did the new capabilities get used?
- Are the transferred patterns still relevant?

Record the outcome in `transfer_attempts[].actual_outcome` (vs `expected_outcome`).

## Proven Transfers (this system)

| From         | To         | Capability                            | Result            |
|--------------|------------|----------------------------------------|-------------------|
| pioneer      | general    | Structured Research Workflows         | 3 → 5 caps        |
| web-browser  | explore    | Search Strategy Patterns              | 3 → 4 caps        |
| video-creator| docs       | Example-Rich Documentation Patterns    | richer templates  |
| architect    | plan       | Architecture evaluation patterns       | 2 → 6 caps        |


## When to use

Load this skill when:
- The task description matches the patterns described in this skill
- You are uncertain about the recommended approach
- You need a checklist or pattern to follow

## When NOT to use

- The task clearly doesn't match (use a different skill)
- You have a more specific skill for the situation
- The user explicitly requests a different approach
