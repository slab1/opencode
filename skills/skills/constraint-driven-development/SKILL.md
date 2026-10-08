---
name: constraint-driven-development
description: "Write a project's quality bar into a durable CONSTRAINTS.md file and detect when an agent weakens that bar to make its own change pass. Covers constraint discovery, per-dimension tooling installs, lifecycle wiring by check cost, diff-scoped guards against threshold-lowering and skipped tests, and ratchets for values with no defensible target. Use when starting work in an unfamiliar repo, when adding a quality gate, when reviewing a diff that touches lint config, coverage thresholds, test skips, or suppressions, or whenever you catch yourself relaxing a standard to get something green. Triggers on: constraints, quality gate, quality bar, coverage threshold, lint budget, constraint file, reward hacking, threshold lowered, test skipped, CI gate."
license: MIT
metadata:
  author: opencode-meta-agent
  version: "1.0.0"
  teaches_stub_markers: "true"
  source: "adapted from addyosmani/agent-skills (open patterns, not copied prose)"
---

# Constraint-Driven Development

## Overview

A codebase's quality bar is usually implicit: a number someone set in a config file, a
convention three people follow, a threshold that was lowered once under deadline pressure and
never raised again. Implicit bars fail in one specific, predictable way — the moment the cheapest
way to make a change pass is to lower the bar itself.

This skill makes the bar explicit (`CONSTRAINTS.md`), attaches an executable command to every
rule in it, and adds a guard that detects bar-weakening inside a diff. It is the anti-reward-
hacking skill: it treats "the check is green" as evidence only when the check was not modified by
the same commit that needed it green.

The governing rule: **every row names the command that produces the verdict. A dimension with a
number and no command is an aspiration, not a constraint.**

## When to Use

- First substantial change in an unfamiliar repo, before writing feature code.
- Adding a quality gate (coverage, a11y, dependency audit, bundle size, mutation score).
- Reviewing or writing a diff that touches `eslint.config.*`, `.eslintrc*`, `pyproject.toml`,
  `tsconfig.json`, `codecov.yml`, `.nycrc`, CI workflows, or a `check`/`test` npm script.
- You personally just disabled, deleted, skipped, or reconfigured something to get output green.
- A project's checks are slow enough that people have started skipping them.

### When NOT to use

- A throwaway spike, scratch script, or one-off data analysis that will never be committed.
- Content or documentation repos with no executable quality surface (no tests, no build).
- As a substitute for actually fixing the failure. A constraint that is failing tells you what to
  do; lowering it to clear the message is the thing this skill exists to catch.
- Mid-incident, when the fix takes minutes and the constraint work belongs in the follow-up. Record
  the incident as a time-boxed Exception (Step 3) and move on.

## The Process

### Step 1 — Detect before you ask

**Never ask what you can read.** Most constraint intake questions are already answered by files on
disk. Read first, then ask only what is genuinely undecidable.

| What to read | What it tells you |
|---|---|
| `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` | Stack, versions, existing `check`/`lint`/`test` scripts |
| `eslint.config.*`, `.eslintrc*`, `ruff.toml`, `.flake8`, `clippy.toml` | Which rules are already on, and whether any were muted |
| `tsconfig.json` / `mypy.ini` / `#![deny(...)]` | Type-strictness floor; the strongest cheap constraint most projects already own |
| Test config (`vitest.config.*`, `jest.config.*`, `pytest.ini`) | Test runner, coverage provider, existing thresholds |
| `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` | What is already gated, and on which OS/node version |
| `codecov.yml`, `.nycrc`, `sonar-project.properties` | Coverage targets and whether they are a floor or aspirational |
| `CONTRIBUTING.md`, `README.md`, `docs/` | Written norms nobody automated |
| `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, agent harness config | Constraints already aimed at an agent — do not duplicate them |

Ask the user only when two readings of the same file are equally plausible (e.g. is CI advisory or
blocking?) or when the answer depends on intent rather than fact.

### Step 2 — Four questions, each with a sane default

Stop at four. **A twelve-question intake produces a config nobody understands**, and an
ununderstood config gets deleted during the first crisis.

1. **Which dimensions matter here?** Default: correctness (tests + types), security, changed-line
   coverage. Skip the rest.
2. **Block or warn?** Default: warn locally, block in CI. You want a signal you can see and a gate
   that holds.
3. **Target numbers, or measure-and-hold?** Default: measure-and-hold (a ratchet) for anything
   whose healthy value you cannot defend in a review. See Step 7.
4. **Slowest tolerable check time?** Default: 90 seconds for the verify stage, 10 seconds for the
   edit loop.

Write the chosen default next to every question so a reader can tell "we decided warn" from "we
never asked".

### Step 3 — Write CONSTRAINTS.md

Four tables. Anything that does not fit one of them is not a constraint yet.

**Floor** — always enforced, no number needed.

| Dimension | Rule | Checked by |
|---|---|---|
| Types | no `any` in `src/`, no new `@ts-ignore` | `npm run typecheck` |
| Secrets | no committed credentials | `gitleaks detect --redact` |
| Scope | do not touch files outside the change's blast radius | `git diff --name-only` vs. task scope |

**Enforced with numbers** — the number and the command travel together.

| Dimension | Rule | Checked by |
|---|---|---|
| Coverage (changed lines) | >= 80% | `npm run coverage:changed` |
| Dependency risk | 0 high / critical advisories | `npm audit --audit-level=high` |
| A11y | 0 critical / serious violations | `npm run a11y` |

**Measured, not yet enforced** — the ratchet table. Value, direction, tolerance. No gate yet.

| Dimension | Today | Direction | Tolerance | Checked by |
|---|---|---|---|---|
| Bundle size | 412 kB | down | 0.5% | `npm run size` |
| Mutation score | 54% | up | flat | `npm run stryker` |

**Exceptions** — time-boxed, owned, expiring. No expiry means it is not an exception, it is a hole.

| Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|
| Bundle size | `vendor/legacy/**` | Frozen vendor drop, migration in #412 | @platform | 2026-12-31 |

Two lines are non-negotiable in the file itself:

> This file does not get weakened to make a change pass. Changes to a threshold, a gate stage, or an
> exception row are a reviewable change in their own right, and `npm run guard` fails if the same
> commit both weakens the bar and relies on it.

Use [`references/constraints-template.md`](references/constraints-template.md) as the starting file
and [`references/floor-guard.py`](references/floor-guard.py) as the executable guard.

### Step 4 — Install per dimension

| Dimension | Install | Run | Gate |
|---|---|---|---|
| Coverage (changed lines) | `npm i -D nyc` | `nyc report` intersected with `git diff` | verify |
| Lint / types | already present | `npm run lint && npm run typecheck` | edit loop |
| Dependency advisories | `npm i -D osv-scanner` or CI-native | `osv-scanner --lockfile=package-lock.json` | verify |
| A11y | `npm i -D @axe-core/cli` | `axe http://localhost:3000 --exit` | full |
| Core Web Vitals | `npm i -D lighthouse` | `lighthouse <url> --only-categories=performance` | full |
| Bundle budget | `npm i -D size-limit` | `npx size-limit` | verify |
| Mutation | `npm i -D stryker` | `npx stryker run` | full, off by default |

Operational gotchas that cost real time when rediscovered — the full list is in
[`references/dimension-installs.md`](references/dimension-installs.md); the two that bite hardest:

- **`--redact` is mandatory on secret scanners.** Without it, the finding — including the secret
  itself — lands in your transcript, your CI log, and possibly your model's context. Always
  `gitleaks detect --redact`.
- **axe and Lighthouse need a running URL.** They test a rendered page, not a source tree. Budget
  for a build + serve + wait loop, and skip with a loud message — never a silent pass.

Then scope expensive checks to the diff (a full audit on every edit does not get run), read the
existing `lcov.info` rather than re-running the suite for a number you already computed, and check
licences before vendoring a rule pack — some shared-configs forbid redistribution.

Emit three scripts and let CONSTRAINTS.md be their documentation:

```jsonc
{
  "scripts": {
    "check:fast":  "npm run typecheck && npm run lint",        // < 5s, every save
    "check:task":  "npm run check:fast && npm run test && npm run guard", // < 90s, per change
    "check:full":  "npm run check:task && npm run audit && npm run a11y && npm run size" // CI
  }
}
```

If the scripts and the file disagree, **the file wins** and the script is a bug. The file is the
source of truth; scripts are its current projection.

### Step 5 — Wire to lifecycle by cost

| Stage | Budget | What runs | Failure behaviour |
|---|---|---|---|
| BUILD | < 5s | typecheck, lint on touched files | show, keep going |
| VERIFY | < 90s | unit/integration tests, coverage:changed, guard | block the task |
| REVIEW | minutes | size budget, deps, diff inspection | block the task, needs a human |
| SHIP | CI, minutes-to-tens | full suite, a11y, mutation (scheduled), Lighthouse | block merge |

The single biggest mistake is running everything everywhere. **A check that stalls the agent gets
switched off, and a gate people switched off is worse than no gate** — it leaves the team
believing they are protected while the bar erodes unobserved. If a check cannot fit its budget,
move it to a slower stage; do not leave it in the fast stage hoping.

### Step 6 — Guard the bar itself

The core of this skill. Constraints only bind against an agent that is willing to move them, and an
agent optimising a green check has a much easier path than a green check honestly.

Run a `git diff`-scoped guard over your change. It detects five named moves:

1. **Threshold moved.** A budget lowered, a severity dropped, or a check removed from the fast
   stage. Diff the config against the merge base: a number going down in the same commit that needs
   it down is the pattern.
2. **Test got easier.** `.skip`/`.only`/`xit` added, a test deleted, an assertion removed, an
   expected value loosened from `400` to `2xx`.
3. **Checker got silenced.** A new `@ts-ignore`, `eslint-disable`, `nosemgrep`, `gitleaks:allow`,
   or Stryker disable. Note what each actually does: `istanbul ignore` **removes code from
   coverage rather than testing it**; `nosemgrep` and `gitleaks:allow` **disable security findings**;
   a Stryker disable **hides a surviving mutant**. None of them make code more correct.
4. **Work is unfinished.** A stub that throws `NotImplementedError`, an empty `catch`, a `TODO`
   where an implementation belongs, a function that returns a constant.
5. **An exception appeared that nobody discussed.** A new exception row, a path added to an ignore
   list, a `paths-ignore` entry — appearing in the same diff as the change that needs it.

[`references/floor-guard.py`](references/floor-guard.py) implements this over `git diff`
(base ref configurable) and exits **0** clean, **1** violation found, **2** misconfigured
(unable to run — which must never be reported as clean).

```bash
python3 references/floor-guard.py --base origin/main
# usage: floor-guard.py [--base REF] [--allow 'pattern'] [--quiet]
```

The **circularity ranking** — how circular is the evidence that this change is good?

| Tier | Checker | Circular? |
|---|---|---|
| External | axe, osv-scanner, Lighthouse, gitleaks, a real browser | **No.** Someone else wrote the rule |
| Project | your lint config, your module boundaries, your conventions | **Weakly.** A human owns the file; the rule predates this change |
| Self | your own test suite | **Yes.** The agent can write code that satisfies tests it also wrote, without working |

Only the third tier is genuinely circular. That is not an argument against tests — it is an
argument for keeping at least one external opinion in the loop. A project where every constraint is
checked by the project's own test suite is a project with no outside witness.

### Step 7 — Ratchets

Some dimensions have no defensible target. You cannot say "bundle size should be 300 kB" for a
codebase whose users' network conditions you do not know. For those, record today's value plus a
direction and refuse to get worse. Machine-readable, in `.constraints-ratchet.yaml`:

```yaml
bundle_kb:      { value: 412.0, direction: down, tolerance_pct: 0.5 }   # may not grow
mutation_score: { value: 54.0,  direction: up,   tolerance_pct: 0.0 }   # may not fall
dep_vulns:      { value: 2,     direction: down, tolerance_pct: 0.0 }
```

Ratchets are not a compromise, they are the point. **Models are rewarded for passing tests, which
you can evaluate in seconds. Architectural rot shows up over months and never reaches the
weights.** A ratchet is the missing penalty, written down where the build can see it — it converts
a direction that would otherwise live only in a reviewer's head into something mechanical.

## Sane Defaults

Use these unless you have a specific reason not to; record the reason in the same row.

| Dimension | Default | Why |
|---|---|---|
| Changed-line coverage | >= 80% | High enough to catch untested branches, low enough not to demand exhaustive tests for a config tweak |
| Whole-project coverage | Today's value, held flat | A rising whole-project target rewards writing easy tests for easy code, not testing hard paths |
| Mutation score | >= 60% | Below this, coverage is measuring execution, not verification; 60% is where assertions start killing mutants |
| Dependency advisories | 0 high / critical | High is "exploitable in a plausible path"; critical is actively exploited. Lower severities are a review item, not a gate |
| LCP | <= 2500 ms | Google's "good" threshold; below it users perceive the page as instant |
| CLS | <= 0.1 | Above 0.1, layout shift becomes noticeable as jank rather than settling |
| Accessibility | 0 critical / serious | Automatable floor (axe). Beyond that, human review — do not claim more than axe proves |
| Exception lifetime | 90 days max | Long enough to land a real fix, short enough that it cannot become permanent |
| Ratchet tolerance | 0.5% | Enough to absorb rounding and generated code, small enough that "it barely moved" cannot hide a regression |

**State the number and the reason together. A threshold without a rationale gets deleted by the
next person who hits it** — and they will hit it.

## Escalation Path

| Level | Mechanism | Cost | Use when |
|---|---|---|---|
| 1 | Written only — a CONSTRAINTS.md nobody runs | ~0 | Documenting norms before you can wire tooling |
| 2 | Scripted — `npm run check`, a post-edit hook, and CI | seconds | **Most projects should stop here.** Deterministic, debuggable, reviewable |
| 3 | Tool-backed runner — a runner/agent that reads constraints, runs them, and blocks with a reason | minutes | Cross-repo enforcement, or untrusted contributor code |

Levels 1 and 2 are enforceable by anyone who can run a command. Level 3 buys enforcement where a
human reviewer is the bottleneck; it also adds a model in the loop, which is exactly the thing
guarding a model. Prefer 2 unless you have a concrete reason.

## Common Rationalizations

| The excuse an agent tells itself | The reality |
|---|---|
| "The threshold was already too strict for this module." | Then it was already failing before your change. Check `git log -S` on that line — if it moved in your commit, it is your move to justify. |
| "Adding a skip was faster than writing the test." | Correct, and that is the problem. The skip is invisible six months later; the cost of the test is one afternoon. |
| "This is a temporary change, I'll revert it." | Uncommitted exceptions are how permanent ones happen. Use an Exception row with a date, or it did not happen. |
| "The lint rule is too noisy for legacy code." | Then it belongs in a `paths-ignore` for `legacy/**` with a reason and an expiry — not in your new file. |
| "I'll add an `istanbul ignore` since it's defensive code." | `istanbul ignore` removes the code from coverage; it does not test it. If the branch is genuinely unreachable, delete the branch. |
| "The config change is unrelated to the feature." | `git diff` does not care why you edited it. A commit that both lowers a bar and relies on that bar is a bar-lowering commit. |
| "Coverage went up overall, so the diff is fine." | Whole-project coverage can rise while the new branch you wrote is entirely uncovered. Intersect with the diff. |
| "This is a spike; I'll clean it up next week." | Then it belongs in a branch, not `main`, where the guard can see it. |
| "The guard is too aggressive for this codebase." | Narrow it with a specific `--allow 'regex'` and a comment, never by deleting the rule. A guard that cries wolf gets muted forever. |

## Red Flags

Concrete signals that the bar is being moved rather than met:

1. The diff contains a number in a config file that moved **downward**, and the change needed it to.
2. `git diff` shows a `-` line deleting a test file, or a new `.skip`/`.only`/`xit`/`@Ignore`.
3. New suppression comments: `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `nosemgrep`,
   `gitleaks:allow`, `istanbul ignore`, `# type: ignore`, `stryker disable`.
4. An assertion loosened from an exact value to a range, a substring, or a status class.
5. A new entry in any ignore list — `.gitignore`, `codecov.yml` `ignore`, `.eslintignore`,
   `paths-ignore`, `semgrepignore`, CI `paths-ignore`.
6. A new Exceptions row in CONSTRAINTS.md added by the same commit that needs it.
7. An empty `catch {}` block, a `pass` body, an empty function body, or a function whose only
   statement is `return null`.
8. `TODO`, `FIXME`, or `XXX` introduced inside a function that the change claims to implement.
9. The guard script was removed, made non-executable, or added to `--allow` patterns in the same
   commit.
10. A check present in `check:full` was dropped from `check:task` in the same commit that made the
    suite slower.
11. Every dimension is verified by the project's own test suite — no axe, no osv-scanner, no
    linter, nothing whose author is not you.

## Verification

Before this work counts as done:

- [ ] `CONSTRAINTS.md` exists at the repo root and every row in Floor and Enforced has a non-empty
      `Checked by` cell containing a runnable command.
- [ ] Every number in the file appears in a config file or is produced by a command you ran and
      pasted the output of.
- [ ] `references/floor-guard.py` runs clean (`exit 0`) on the current branch, and fails (`exit 1`)
      on a deliberately weakened fixture you created to prove it — record both outputs.
- [ ] `check:fast` completes under 5s and `check:task` under 90s, measured with a timer, on this
      machine.
- [ ] `check:task` fails when you introduce a known violation (skip a test, add an `eslint-disable`)
      — a gate that cannot fail is not a gate.
- [ ] Every Exception row has a Rule, Path, Reason, Owner, and an `Expires` date within 90 days.
- [ ] CI runs `check:full` on pull requests, and you have seen a PR blocked by it.
- [ ] The diff you are shipping contains none of the eleven Red Flags.
- [ ] At least one enforced dimension is checked by an **external** tool, not only your own tests.
- [ ] The guard is not in any `--allow` list you added in this change.

## See Also

- [`references/constraints-template.md`](references/constraints-template.md) — copy-paste starting
  file for Step 3.
- [`references/floor-guard.py`](references/floor-guard.py) — the Step 6 diff-scoped guard
  (exit 0 clean / 1 violation / 2 misconfigured).
- [`references/dimension-installs.md`](references/dimension-installs.md) — the full Step 4 install
  matrix, operational gotchas, and the script split.
- [tdd-workflow](../tdd-workflow/SKILL.md) — write the failing test before you need the gate.
- [verification-planning](../../verification-planning/SKILL.md) — pick the evidence path before you
  pick the threshold.
- [security-audit](../security-audit/SKILL.md) — the dimensions to constrain when the project holds
  user data or credentials.
- [security-threat-model](../security-threat-model/SKILL.md) — derive security constraints from a
  real threat model instead of guessing thresholds.
- [git-commit-hygiene](../git-commit-hygiene/SKILL.md) — a threshold change is its own commit.
- [refactor-safe](../refactor-safe/SKILL.md) — ratchets let you refactor without a coverage fight.
- [system-audit](../system-audit/SKILL.md) — the same detect-before-you-ask discipline applied to
  agent configuration.
- Ask the `librarian` agent (by name) to fill any dimension where you are about to guess a tool's
  configuration rather than reading its docs.
