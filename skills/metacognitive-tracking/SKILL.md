---
name: metacognitive-tracking
description: Track not just task outcomes but the improvement strategies that produced them. Enable recursive self-improvement of the meta-agent by logging which strategies worked, which failed, and why. Based on HyperAgents (Meta, 2026).
license: MIT
compatibility: opencode>=1.16.0
metadata:
  inspired_by: HyperAgents (arXiv:2603.19461)
---

# Metacognitive Tracking

The insight from **HyperAgents** (Meta, March 2026): the meta-level modification procedure is itself editable. So we must track not just *what we did* but *how we did it* — and which improvement *strategies* actually improve outcomes.

## Why Outcomes Alone Aren't Enough

Most performance tracking logs:
- What task was done
- Whether it succeeded
- How long it took

But it does NOT log:
- **Which strategy** was used (e.g., "added rules section" vs "transferred capability" vs "renamed tag")
- **Why that strategy was chosen** (e.g., "agent had no rules" vs "agent had wrong rules")
- **Whether the strategy actually worked** (did the next audit pass? did performance improve?)

Without this meta-level data, the meta-agent can't learn which strategies to apply in which situations. It's trying new strategies blindly.

## What to Track

Add a `strategy_log` entry to shared context for every improvement attempt:

```json
{
  "id": "strategy-1717700000",
  "agent_target": "display-agent",
  "diagnosis": "missing rules section (structure_complete: false)",
  "strategy_chosen": "add_rules_section",
  "strategy_alternatives_considered": [
    "transfer_rules_from_similar_agent",
    "patch_with_template",
    "request_user_input"
  ],
  "why_this_strategy": "rules section is missing entirely; template approach is fastest and most consistent",
  "applied_at": "2026-06-07T00:00:00Z",
  "outcome": "success",
  "outcome_evidence": "audit re-run shows structure_complete: true",
  "duration_s": 45,
  "confidence_before": 0.95,
  "confidence_after": 0.97,
  "followup": null
}
```

## Strategy Library

Common strategies the meta-agent can use:

| Strategy                      | When to use                                      |
|-------------------------------|--------------------------------------------------|
| `add_missing_section`         | Section is absent                                |
| `improve_section_content`     | Section exists but is vague/incorrect            |
| `transfer_capability`         | Target lacks a pattern that source has well      |
| `add_example`                 | Capability is too abstract, needs concrete use   |
| `add_rule`                    | Agent makes repeated errors that rules could prevent |
| `tighten_permissions`         | Agent has overly broad access                    |
| `loosen_permissions`          | Agent is blocked by overly narrow access         |
| `fix_frontmatter`             | Frontmatter is invalid or missing fields         |
| `rename_section_tag`          | Section name doesn't match module detection      |
| `split_into_subagent`         | Agent's scope is too broad                       |
| `merge_with_related`          | Two agents have overlapping purpose              |
| `deprecate_agent`             | Agent is no longer needed                        |
| `self_improve`                | The meta-agent itself is the target              |

## Track Effectiveness

After applying a strategy, log the outcome evidence:
- Did the audit pass?
- Did the next performance entry show improvement?
- Did the agent complete the next assigned task successfully?

This builds a dataset of `(situation, strategy) → outcome` mappings that future runs can use.

## Self-Improvement Loop

```
1. Diagnose situation (what's wrong with target agent)
2. Choose strategy from library (or invent new)
3. Apply strategy
4. Verify outcome
5. Log to strategy_log with confidence_before/after
6. Update strategy effectiveness scores
7. Repeat — now with better strategy selection
```

The **strategy effectiveness** is itself editable. The meta-agent can prune strategies that never work and add new ones that succeed. This is the metacognitive self-modification loop from HyperAgents.

## Integration

- Add `strategy_log` to `findings.meta-agent` in shared context
- Reference this skill from the meta-agent's `<workflow-types>` section
- Update meta-agent's `<rules>` to require strategy logging before applying any patch
