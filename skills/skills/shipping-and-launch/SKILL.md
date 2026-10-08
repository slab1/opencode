---
name: shipping-and-launch
description: "Ship and launch a change with a pre-launch checklist, feature flag lifecycle, staged rollout percentages, error-budget gates, and a rollback plan. Use when preparing a release, cutting a deploy, launching a feature or API, or deciding whether to advance, hold, or roll back a canary. Triggers on launch, release, deploy, ship, go-live, canary, rollout, rollback, feature flag, error budget, pre-launch checklist, production readiness."
license: MIT
metadata:
  author: opencode-meta-agent
  version: "1.0.0"
  source: "adapted from addyosmani/agent-skills (open patterns, not copied prose)"
---

# Shipping and Launch

## Overview

Launching is not deploying. Deploying is making code available; launching is
putting it in front of users in a way where you can tell whether it worked, and
undo it in under a minute if it didn't.

This skill is the operational half of delivery: the checklist before you ship,
the flag lifecycle that makes shipping reversible, the staged rollout that limits
the blast radius, the error-budget gate that decides whether you may ship at all,
and the rollback plan you write *before* the deploy, not after the incident.

The whole design is built around one property: **every launch is reversible, and
the cost of reversal is known in advance.** A flag-off deploy can be undone in
under a minute; a destructive schema migration cannot. That asymmetry is what
decides the order of your steps.

Load `references/launch-checklist.md` for the expanded per-item checklist and
`references/rollout-playbook.md` for the staged-rollout runbook.

## When to Use

- Cutting a release or deploying to production
- Launching a new feature, endpoint, or API version to users
- Turning a feature on for the first time, or widening its audience
- Deciding whether to advance, hold, or roll back a canary
- Deciding whether the team may ship feature work at all this sprint
- Writing a rollback plan, launch checklist, or go/no-go review
- Anything where "we can put it back" needs to be an answer, not a hope

## When NOT to Use

- **Local development and PR review.** No flags, no canary, no gate.
- **Emergency rollbacks in progress.** Execute the rollback; read this afterwards.
- **Content and copy changes with no code path.** The only applicable checks are
  correctness and accessibility.
- **Rolling forward on purpose, with no reversible component** — a pure data
  backfill. This skill's rollback story does not apply; use
  `deprecation-and-migration` and write a forward-completion plan instead.
- **Deciding what to build.** That is `tdd-workflow` and architecture, not launch.

## The Process

### Step 1 — Run the pre-launch checklist

Six subsections. All of them. Do not treat the checklist as a form to approve;
treat each unchecked item as work that is not done.

**Code Quality**
- [ ] Tests pass in CI on the exact commit being released
- [ ] Typecheck and lint clean at CI level, not just locally
- [ ] No debug logging, `console.log`, or `TODO(remove)` left in the diff
- [ ] The diff was reviewed by someone who did not write it
- [ ] Migrations apply cleanly from empty **and** roll back (see `deprecation-and-migration`)
- [ ] Feature is behind a flag and the flag defaults to OFF

**Security**
- [ ] No secrets in the diff, in logs, or in client-side bundles
- [ ] New endpoints have authentication *and* authorization checks — per-tenant, not just logged-in
- [ ] Input validated at the boundary; output escaped at the render
- [ ] Dependency scan run; new CVEs triaged, not auto-ignored
- [ ] No new PII in logs, analytics, or error payloads
- [ ] Rate limiting present on anything unauthenticated

**Performance**
- [ ] Bundle size change measured (gzip), budget not exceeded
- [ ] Any new query has a plan (`EXPLAIN ANALYZE`) and an index if needed
- [ ] N+1 queries checked for on the new code paths
- [ ] No unbounded loop, no query without a `LIMIT` where a count could grow
- [ ] LCP/INP/CLS checked on the affected pages (see `performance-optimization`)

**Accessibility**
- [ ] Keyboard-only path works for the new interaction
- [ ] Focus order logical; focus trap in any modal; focus restored on close
- [ ] Contrast ratios pass AA for new text and controls
- [ ] Images and icons have accessible names; decorative ones are marked
- [ ] Screen-reader announcement for anything that changes without navigation
- [ ] Motion respects `prefers-reduced-motion`

**Infrastructure**
- [ ] Config and secrets exist in the target environment *before* the deploy
- [ ] Capacity headroom checked: connection pool, memory, queue depth, third-party quotas
- [ ] Deploy is idempotent and re-runnable (a half-applied deploy is recoverable)
- [ ] Backups verified recent **and** a restore actually tested
- [ ] Dashboards and alerts exist for the new path *before* it has traffic
- [ ] Health/readiness endpoints report the new dependency's state

**Documentation**
- [ ] User-facing change documented in the changelog, not only in the PR
- [ ] Migration guide written and run end to end by someone else
- [ ] Runbook updated with the new failure modes and their first diagnostic
- [ ] Support/ops told what to expect and what "normal" looks like
- [ ] Deprecation notices sent for anything being replaced (see `deprecation-and-migration`)

### Step 2 — Run the error-budget release gate

```
Budget remaining > 20%  ->  Ship normally; monitor closely
Budget remaining 0-20%  ->  Slow rollouts only; no high-risk changes
Budget exhausted        ->  Freeze feature work; focus entirely on reliability
Budget resets           ->  Resume normal pace; bake in the fix that recovered it
```

This is a policy decision made *before* the deploy, not a judgment made during
the incident. An exhausted budget with a big launch queued is how a bad week
becomes a bad quarter. Two supporting rules:

- **A high burn rate during a canary (consuming budget faster than the baseline
  pace) is a HOLD signal.** Not a "keep an eye on it" signal. Error budget is a
  rate; a canary that burns it 3x faster than baseline will exhaust it in a third
  of the time regardless of the absolute error count looking small.
- **Budget exhaustion is a freeze, not a slow-down.** Every incident review asks
  "why didn't we stop shipping?" The gate exists so the answer is a policy, not a
  fresh debate under pressure.

### Step 3 — Prepare the rollback plan *before* the deploy

```
Rollback Plan — <change> (<release/commit>)

Trigger Conditions (any ONE is sufficient):
  - Error rate >2x baseline for 5 consecutive minutes
  - P95 latency >50% above baseline for 10 minutes
  - New client error type at >0.1% of sessions
  - Any data-integrity signal: writes failing, duplicates, wrong totals
  - Business metric down >5% and not explained by the change itself

Rollback Steps:
  1. Turn the feature flag OFF              (~<1 min, no deploy)
  2. Verify error rate returns to baseline   (5 min observation)
  3. If still elevated: redeploy previous release  (~<5 min)
  4. If still elevated: roll back the migration (<15 min, see below)

Database Considerations:
  - Migration is: additive | dual-write | destructive
  - If destructive, the previous code CANNOT read the new schema ->
    rollback is a restore, not a redeploy. Restore point: <timestamp>
  - Data written under the new code path is preserved: yes | no, <explain>
  - Restore rehearsal status: done | NOT DONE  (if NOT DONE, this is a red flag)

Time to Rollback:
  - Feature flag off:       <1 min   (preferred path)
  - Redeploy last release:  <5 min
  - Database rollback:      <15 min  (+ restore time, verify first)

Owner on call during rollout: <name, contact>
Decision maker:              <name, contact>
```

Two things make this real rather than decorative: **who** decides, and **the
numbers**. A rollback plan without a named decision maker produces a 20-minute
argument in the middle of an incident. A plan without pre-agreed thresholds
produces the same argument with different words.

The **data-integrity trigger** is separate from the metrics triggers on purpose.
Metrics can be noisy; a wrong total is not. If the change writes data in a shape
the old code cannot read, that is the trigger that fires first.

### Step 4 — Walk the staged rollout, one stage at a time

Never advance a stage on a timer. Advance on evidence, after the observation
window has actually elapsed with real traffic in it.

| Stage | Audience | Window | Gate to advance |
|---|---|---|---|
| 1 | staging | full test suite + smoke | all green |
| 2 | production, flag OFF | 1 deploy cycle | nothing broke with the code inert |
| 3 | team / internal users | 24 hours | no new error type, metrics green |
| 4 | **canary, 5%** | 24-48 hours | thresholds table: green |
| 5 | 25% | 24 hours | green |
| 6 | 50% | 24 hours | green |
| 7 | 100% | 1 week monitoring | green, then flag cleanup |

Stage 4 is the one that matters and the one most often rushed. 5% for 24-48 hours
gives you a full daily cycle of traffic shape — including the low-traffic hours
where batch jobs run. A canary you advance after 20 minutes has only seen peak.

### Step 5 — Judge each stage with the rollout decision thresholds

| Metric | Advance (green) | Hold and investigate (yellow) | Roll back (red) |
|---|---|---|---|
| Error rate | Within 10% of baseline | 10-100% above baseline | >2x baseline |
| P95 latency | Within 20% of baseline | 20-50% above baseline | >50% above baseline |
| Client JS errors | No new error types | New errors at <0.1% of sessions | New errors at >0.1% of sessions |
| Business metrics | Neutral or positive | Decline <5% (may be noise) | Decline >5% |

Read the columns as an action ladder, not a scoreboard: green means advance,
**yellow means stop and understand before doing anything else** — including
before advancing — and red means roll back now and diagnose offline.

Baseline is the *pre-deploy* measurement of the same metric on the same
population. Comparing against a global average that includes other traffic
classes is how a real 3x regression reads as "within 10%".

Yellow is not a pass. The most expensive outcome in a rollout is tolerating a
yellow twice — the second yellow is usually red, and by then you have spent the
window you were supposed to learn from.

### Step 6 — Clean up

Flags, temporary code, and instrumentation all expire. See the flag lifecycle
below. A launch that leaves its flag in place has not finished; it has moved the
cleanup debt forward and made the next launch's flag set larger.

## Feature Flag Lifecycle

```
DEPLOY (flag OFF)  ->  ENABLE for team/beta  ->  GRADUAL ROLLOUT
  5%  ->  25%  ->  50%  ->  100%             ->  MONITOR at each stage
  ->  CLEAN UP (flag and dead branch removed)
```

MONITOR is a stage, not a vibe. Each transition is a checkpoint where you
compare against the thresholds table. Skipping a stage is allowed (small
internal feature: OFF -> 100%), skipping MONITOR is not.

**Four rules:**

1. **Every flag has an owner AND an expiration date.** No owner means nobody
   deletes it. No date means it becomes permanent and grows the state space.
2. **Cleanup within 2 weeks** of the flag reaching 100% (or of the feature being
   reverted). Remove the flag *and* the dead branch — a flag at `true` forever is
   not a flag, it is a second code path.
3. **Do not nest flags.** Two independent flags mean four states; three mean
   eight; a flag plus a cohort means more. You cannot test four states, so at
   least two of them are untested in production. Keep one rollout flag and put
   genuinely independent behavior behind separate deploys.
4. **Test both states in CI.** Both states are shipped code. A flag whose off-path
   is untested is untested code that a user will eventually reach.

Use a flag for: risky behavior you want to disable instantly, staged rollout of a
change, and operational kill switches. Do not use a flag for: long-lived
configuration (use real config), feature entitlements (use real permissions), or
anything you would not be willing to delete in two weeks.

## Common Rationalizations

| The excuse | The reality |
|---|---|
| "It works in staging, it'll work in production" | Staging has no real traffic shape, no real data volume, no third-party rate limits, and no real users to lose. Staging proves the code runs. It cannot prove the change is safe at load. |
| "We don't need feature flags for this" | You are not deciding whether the code needs a flag, you are deciding whether *being unable to turn it off in under a minute* is acceptable. If yes, fine — that is a decision. Make it explicitly and make sure you have a redeploy path instead. |
| "Monitoring is overhead" | Monitoring is what makes the rollout thresholds a measurement instead of an opinion. Without it, the canary is the only signal, and the canary is your users. |
| "We'll add monitoring later" | Later is after the incident. Instrument before the traffic, not after the graph. Dashboards and alerts for a new path must exist before the path has traffic — otherwise you are reading history, not watching. |
| "Rolling back is admitting failure" | Rolling back is a success: the blast radius was capped at 5% of traffic and the change cost 15 minutes instead of a week. Admitting failure is shipping a known-bad change forward to save the appearance of a plan. |
| "The error rate looks fine, let's keep shipping" | The error rate being fine does not mean the change is fine — it may mean the flag is at 5%, or the affected path is not instrumented, or the error is a business-level failure with a 200 status. Check the new-error-type signal and the business metric, not just the 5xx graph. |
| "It's a small change, the checklist is overkill" | The blast radius of a change is not proportional to its size. A one-line change to a shared component or a default value has a larger surface than a 500-line isolated feature. |
| "We'll roll back if something goes wrong" | Without pre-written trigger thresholds and a named decision maker, that sentence describes a 20-minute argument during the incident, not a rollback. |
| "The canary has been clean for 20 minutes, let's widen" | 20 minutes of canary traffic has not seen the batch jobs, the daily peak, or the traffic dip. That window is what the canary is for; spending it early is the whole cost. |
| "We can push the fix and hotfix instead of rolling back" | That is a valid alternative only if the fix is one-line, testable, and does not touch the same code the change touched. In practice it usually means shipping an unverified change on top of an unverified change, at 2am, with no baseline. |

## Red Flags

- No written rollback plan, or no named decision maker in it
- Rolling back with no rehearsal — the first test of the rollback path is the
  real one
- Feature flag with no owner, no expiration date, or still present 2+ weeks after
  100%
- Nested flags (a rollout flag inside a cohort flag), or more than a handful of
  simultaneously active flags
- Canary advanced on a timer instead of on measured evidence
- Rolling back and re-pushing in a loop ("flip-flopping") without changing
  anything between attempts
- Dashboards or alerts created *after* the deploy
- Error budget exhausted, with feature work still queued
- Migration bundled into the same deploy as application code that depends on it
- Config or secrets assumed present in the target environment without checking
- Rollback plan that says "restore from backup" with no restore rehearsal
- No baseline captured *before* the change, so "within 10%" cannot be evaluated
- Release notes written after the release, not before
- "Hotfix" pushed to production without the change going through the same checks

## Verification

- [ ] Pre-launch checklist completed item by item, not summarized
- [ ] Error-budget gate evaluated and its verdict recorded before the deploy
- [ ] Rollback plan written and saved where on-call can find it in 30 seconds
- [ ] Rollback triggers are numeric, and baseline values captured pre-deploy
- [ ] Decision maker and on-call owner named and reachable for the window
- [ ] Every feature flag has an owner and an expiration date recorded in the flag system
- [ ] Flag defaults to OFF in the deployed commit
- [ ] Both flag states covered by tests in CI
- [ ] Staged rollout executed with each stage's window actually elapsed
- [ ] Each stage's metrics captured and compared against the thresholds table
- [ ] Any yellow documented with a hypothesis before advancing
- [ ] Rollback path rehearsed (staging or a real past rollback), not assumed
- [ ] Migration verified reversible, or the irreversibility explicitly accepted in the plan
- [ ] Dashboards live and alerting before traffic, verified by receiving a test alert
- [ ] Support/ops briefed with "what normal looks like" for the first 48 hours
- [ ] Flag cleanup scheduled, with a calendar entry or issue — not a memory
- [ ] Post-launch: flags and dead branches removed within 2 weeks

## See Also

- [deprecation-and-migration](../deprecation-and-migration/SKILL.md) — the
  announcement half of a launch, plus expand/contract so the migration and the
  deploy are never the same event
- [performance-optimization](../performance-optimization/SKILL.md) — the
  performance and Core Web Vitals line of the pre-launch checklist, and the
  budgets that make it measurable
- [verification-planning](../../verification-planning/SKILL.md) — designing the
  evidence a launch requires before you pick a go/no-go date
- [security-audit](../security-audit/SKILL.md) — the Security subsection and the
  gate for shipping anything that changes auth or data exposure
- [security-threat-model](../security-threat-model/SKILL.md) — for launches that
  introduce a new trust boundary (webhooks, third-party OAuth, public endpoints)
- [tdd-workflow](../tdd-workflow/SKILL.md) — the Code Quality subsection depends
  on red-green-refactor being how the change was built
- [debug-systematic-investigation](../debug-systematic-investigation/SKILL.md) —
  what to do during a yellow (investigate before advancing) and after a rollback
- [error-recovery-protocol](../error-recovery-protocol/SKILL.md) — the mechanical
  steps when a deploy fails halfway
- [git-commit-hygiene](../git-commit-hygiene/SKILL.md) — release commits,
  revert-friendly history, and revert commits as a first-class artifact
- For UI-heavy launches, hand the Accessibility and visual-polish passes to the
  `designer` agent; there is no agent file to link here, ask for it by name.
  The web-design-guidelines skill (under the openmontage bundle, not directly
  under `skills/`) is the companion checklist