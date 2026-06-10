---
name: subagent-driven-development
description: Execute implementation plans by dispatching a fresh subagent per task, with two-stage review (spec compliance first, then code quality). Faster iteration, no context pollution. Use when implementing multi-step plans with independent tasks in the current session.
license: MIT
compatibility: opencode>=1.16.0
---

# Subagent-Driven Development

Execute an implementation plan by dispatching a **fresh subagent per task** with **two-stage review** after each.

**Core principle**: Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan with multiple steps
- The tasks are mostly independent
- You want to stay in the current session (no context switch)
- You want faster iteration than manual execution

Do NOT use when:
- Tasks are tightly coupled
- You need parallel execution across sessions
- You're brainstorming or planning (not yet implementing)

## The Process (Per Task)

### 1. Dispatch implementer subagent
Send a fresh subagent with:
- The full task spec
- Relevant context from previous tasks
- Tool routing rules
- Output contract (exact format)
- Done-when criteria

### 2. Spec compliance review
Before accepting the implementation, run a spec compliance check:
- Does the output match the spec exactly?
- Are all required files modified?
- Are all acceptance criteria met?

If the review fails, send the subagent back to fix.

### 3. Code quality review
After spec compliance passes, run a quality review:
- Is the code readable and idiomatic?
- Are there error handling gaps?
- Does it follow the project's conventions?
- Is the test coverage adequate?

If the review fails, send the subagent back to improve.

### 4. Move to next task
Once both reviews pass, log the outcome and proceed to the next task.

## Why Fresh Subagents?

A fresh subagent has:
- **Clean context** — no pollution from previous tasks
- **Full attention** — not distracted by side discussions
- **No bias** — sees the spec with fresh eyes
- **Predictable behavior** — same prompt produces same quality

## Why Two-Stage Review?

A single review conflates "did it do what was asked" with "is it well done." Separating:
- **Spec review** catches missing functionality first
- **Quality review** catches code smells after

This produces a tighter feedback loop than combining both.

## Subagent Prompt Anatomy

For reliable behavior, structure subagent prompts in this order:

1. **Role** — what specialist this agent is
2. **Scope** — what it owns for this task
3. **Hard boundaries** — what it must not do
4. **Tool routing rules** — which tools to prefer
5. **Workflow** — ordered execution steps
6. **Output contract** — exact format and constraints
7. **Done-when** — completion criteria and stop conditions

## Example: 3-Task Implementation Plan

```
Task 1: Add login form
  → Dispatch implementer subagent
  → Spec review: form has all required fields ✓
  → Quality review: input validation, accessibility ✓
  → Log outcome: success

Task 2: Add password reset
  → Dispatch implementer subagent
  → Spec review: reset flow complete ✓
  → Quality review: rate limiting, secure tokens ✓
  → Log outcome: success

Task 3: Add session management
  → Dispatch implementer subagent
  → Spec review: session lifecycle implemented ✓
  → Quality review: CSRF protection, secure cookies ✓
  → Log outcome: success
```

## Integration with Background Subagents (OpenCode 1.16.2+)

For independent tasks, send subagents to the background and continue working on the main thread. Results come back when ready.

## Origin

Pattern from Anthropic's "subagent-driven-development" and Oh-My-OpenCode's parallel Team Mode.
