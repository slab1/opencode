---
name: system-audit
description: Run a complete structural and performance audit of all 20 OpenCode agents. Use when verifying system health, identifying configuration gaps, or preparing improvement reports. Detects missing sections, incomplete frontmatter, capability count, and cross-references the opencode_improvement module's audit command.
license: MIT
compatibility: opencode>=1.16.0
---

# System Audit

Run a complete structural and performance audit of all 20 OpenCode agents in `~/.config/opencode/agents/`.

## What I do

- Audit every agent `.md` file for structural completeness
- Detect missing frontmatter, `<rules>`, `<workflow>`, `<shared-context>`, `<memory>`, `<task-tracking>` sections
- Count capability sections under `<capabilities>` (target: 5+)
- Cross-reference with `python3 -m opencode_improvement audit` output
- Produce a structured report with severity-prioritized findings

## When to use me

Use this skill when:
- User asks "is the system healthy?" or "audit the agents"
- Before applying any structural patches
- After any new agent is added
- During meta-agent improvement cycles
- Periodic health checks (cron-friendly)

## How I work

1. **Run the audit**: `python3 -m opencode_improvement audit` — captures size, sections, completeness
2. **Parse output**: Read JSON, identify agents with `structure_complete: false`
3. **Group findings**: Missing rules / missing workflow / missing context / etc.
4. **Cross-reference**: Check `shared/context.json` performance_log for trend data
5. **Prioritize**: Missing critical sections > missing optional > low capability count
6. **Report**: Produce actionable list with file paths and proposed patches

## Severity levels

- **Critical**: Missing `<shared-context>`, `<memory>`, or frontmatter
- **High**: Missing `<rules>`, `<workflow>`, `<task-tracking>`
- **Medium**: Missing `<context>`, `<role>`, `<capabilities>`
- **Low**: Capability sections < 5, oversized config, outdated patterns

## Expected output

A structured report with:
- Total agents audited
- Pass/fail count
- Per-agent findings (file, missing sections, line counts)
- Recommended patches (file, section, content)
- Trend data (comparing this run to previous runs)

## Validation

After applying any patches, re-run the audit to confirm 100% structural completeness.
