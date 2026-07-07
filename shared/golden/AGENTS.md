# Golden Dataset Templates — Agent Evaluation Test Cases

**Inspired by:** DeepEval's `assert_test()` pattern (⭐7k) — structured golden datasets
with input/expected_output/metrics for agent behavior testing.

## Overview

Golden datasets are curated test cases that define:

1. **Input**: What task or prompt is given to the agent
2. **Expected Output**: What the agent should produce (exact match, regex, or semantic)
3. **Metrics**: How to measure success (pass/fail gates, scores)
4. **Severity**: How important this test case is (info/warn/critical)

## File Structure

```
shared/golden/
├── AGENTS.md             ← THIS FILE — documentation
├── agent_tasks.json      ← Golden test cases for all agents
└── <agent>_eval.json     ← Per-agent evaluation datasets (one per agent)
```

## Schema

Each test case follows this structure:

```json
{
  "id": "build-001",
  "agent": "build",
  "category": "tool_correctness",
  "description": "Build agent should use hash-anchored edits before modifying files",
  "input": {
    "task": "Fix the null pointer exception in src/auth.js:45",
    "context": "File has been read 60 seconds ago, re-read before editing"
  },
  "expected": {
    "behavior": "uses_hash_anchored_edits",
    "check": "loads hash-anchored-edits skill OR re-reads file before edit",
    "type": "behavioral"
  },
  "metrics": {
    "pass_on": "skill loaded or file re-read",
    "fail_on": "edit attempted without validation"
  },
  "severity": "critical",
  "reference": "build.md rules section"
}
```

## Test Categories

| Category | Description | Example |
|----------|-------------|---------|
| `tool_correctness` | Agent uses the right tools in the right order | Hash-anchored edits before file modification |
| `task_completion` | Agent completes the assigned task fully | Feature implementation covers all requirements |
| `refusal_handling` | Agent correctly refuses unsafe requests | NSFW content, secret exposure |
| `context_adherence` | Agent follows shared context protocol | Reads context.json before starting |
| `error_recovery` | Agent recovers from tool failures | MCP timeout retry pattern |
| `subagent_delegation` | Agent delegates appropriately | Invokes architect for architecture questions |
| `output_quality` | Agent produces correct, complete output | Code compiles, tests pass |

## Severity Levels

| Level | Meaning | Action on Failure |
|-------|---------|-------------------|
| `critical` | Core agent behavior broken | Block deployment, fix immediately |
| `warn` | Important but not blocking | Flag in report, fix in current sprint |
| `info` | Best practice violation | Log for trend tracking |

## Usage

```bash
# Run all golden tests for an agent
python3 -m opencode_improvement eval --agent build --golden

# Run a specific test case
python3 -m opencode_improvement eval --agent build --test build-001

# Run with fail-under gating (Juanllenato pattern)
python3 -m opencode_improvement eval --all --fail-under 0.8
```

## Property-Based Tests (NEW — mpuodziukas-labs pattern)

Property-based tests verify **invariants that ALL agents must satisfy**, regardless of domain.
These are universal truths about well-configured agents.

| ID | Property | Severity | Check |
|----|----------|----------|-------|
| property-001 | Has `<role>` section | critical | Agent defines its purpose |
| property-002 | Has 3+ capability sections | warn | Capability count >= 3 |
| property-003 | Primary agents have `task: allow` | critical | Subagent delegation enabled |
| property-004 | Complete frontmatter | critical | description + mode + permission |
| property-005 | Reads shared context | critical | Has `<shared-context>` section |
| property-006 | Has task tracking | warn | Has `<task-tracking>` section |
| property-007 | Has skills section | warn | Has `<skills>` or skill-loading cap |

Property invariants are checked as part of `python3 -m opencode_improvement eval --golden`.
Unlike behavioral test cases, property tests apply to ALL agents simultaneously.
