# CONSTRAINTS.md — template

Copy into the repo root and edit. Delete every row you are not enforcing. An empty table is fine;
a filled-but-unenforced table is not — that is what the Measured table is for.

---

# CONSTRAINTS.md

Project quality bar. Each rule names the command that produces its verdict.

> This file does not get weakened to make a change pass. A change to a threshold, a gate stage, or
> an exception row is reviewable in its own right. `npm run guard` fails when the same commit both
> moves the bar and relies on the bar.

Last reviewed: YYYY-MM-DD · Owner: @team

## 1. Floor — always enforced

| Dimension | Rule | Checked by |
|---|---|---|
| Types | no `any` in `src/`, no new `@ts-ignore` | `npm run typecheck` |
| Secrets | no committed credentials (redacted output) | `gitleaks detect --redact` |
| Scope | no files outside the change's declared blast radius | `git diff --name-only` vs. task scope |

## 2. Enforced with numbers

| Dimension | Rule | Threshold | Checked by | Stage |
|---|---|---|---|---|
| Coverage (changed lines) | new logic is tested | >= 80% | `npm run coverage:changed` | task |
| Dependency risk | no exploitable advisories | 0 high/critical | `npm run audit` | task |
| Bundle budget | entry point size | <= 450 kB | `npm run size` | task |
| A11y (automated) | axe on primary pages | 0 critical/serious | `npm run a11y` | full |

## 3. Measured, not yet enforced (ratchets)

Value is today's measured number. Direction is the only allowed movement. Tolerance absorbs
rounding and generated files only.

| Dimension | Today | Direction | Tolerance | Checked by | Promote when |
|---|---|---|---|---|---|
| Whole-project coverage | 71.2% | up | flat | `npm run coverage` | reaches 75% |
| Mutation score | 54% | up | flat | `npm run stryker` | reaches 60% |
| Bundle size | 412 kB | down | 0.5% | `npm run size` | never (cost) |

## 4. Exceptions

No expiry means this is not an exception, it is a hole. Review before each expiry date.

| Rule | Path | Reason | Owner | Expires | Issue |
|---|---|---|---|---|---|
| Bundle budget | `vendor/legacy/**` | frozen vendor drop | @platform | YYYY-MM-DD | #412 |

## Ratchet config

Machine-readable mirror of section 3, enforced by `npm run ratchet`.

```yaml
# .constraints-ratchet.yaml
coverage_pct:      { value: 71.2, direction: up,   tolerance_pct: 0.0 }
mutation_score:    { value: 54.0, direction: up,   tolerance_pct: 0.0 }
bundle_kb:         { value: 412.0, direction: down, tolerance_pct: 0.5 }
dep_vulns:         { value: 2,    direction: down, tolerance_pct: 0.0 }
```

## Scripts

`CONSTRAINTS.md` is the source of truth. If a script disagrees with this file, the file wins and
the script is a bug.

| Script | Budget | Stages run |
|---|---|---|
| `npm run check:fast` | < 5s | typecheck, lint (touched files) |
| `npm run check:task` | < 90s | check:fast, test, coverage:changed, guard |
| `npm run check:full` | CI | check:task, audit, size, a11y; stryker on schedule |
