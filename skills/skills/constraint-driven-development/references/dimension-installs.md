# Per-dimension installs — Step 4 reference

Commands and gotchas for installing a quality gate per dimension. Adjust to your package manager;
the *ordering* and the failure modes are the transferable part.

## Install matrix

| Dimension | Install | Run | Stage |
|---|---|---|---|
| Lint / types | usually already present | `npm run lint && npm run typecheck` | edit loop |
| Coverage (changed lines) | `npm i -D nyc` | `nyc report` ∩ `git diff --name-only` | verify |
| Coverage provider | `npm i -D @vitest/coverage-v8` (or `coverage-final.json` from jest) | emitted by the existing test run | verify |
| Dependency advisories | `npm i -D osv-scanner` or the CI-native scanner | `osv-scanner --lockfile=package-lock.json` | verify |
| Secret scanning | `npm i -D gitleaks` / `trufflehog` | `gitleaks detect --redact` | verify + CI |
| A11y (automated) | `npm i -D @axe-core/cli` | `axe http://localhost:3000 --exit` | full |
| Core Web Vitals | `npm i -D lighthouse` | `lighthouse <url> --only-categories=performance` | full |
| Bundle budget | `npm i -D size-limit` | `npx size-limit` | verify |
| Mutation | `npm i -D stryker` | `npx stryker run` | full, scheduled, off by default |

Python equivalents: `ruff`, `mypy`, `pytest --cov`, `bandit`, `pip-audit`,
`axe-core-python`, `lighthouse` via `npm`, `stryker` has no Python peer (use `mutmut`).

## Operational gotchas

1. **`--redact` is mandatory on secret scanners.** Without it, the finding — including the secret
   itself — lands in your transcript, your CI log, and possibly your model's context.
   Always `gitleaks detect --redact`. Same for `trufflehog --only-verified` plus redaction.
2. **axe and Lighthouse need a running URL.** They test a rendered page, not a source tree. Budget
   for build → serve → wait-for-port in the script, and skip with a **loud** message when the URL
   is unreachable. A silent pass is a lie the build will repeat forever.
3. **Scope expensive checks to the diff.** A full audit on every edit does not get run, and a check
   that does not get run is not a constraint. The units that survive a real edit loop are:
   - changed-line coverage (intersect the coverage report with `git diff --name-only`)
   - lint on touched files (`eslint --changed` / `ruff` on the changed set)
   - size-limit on the affected entry point only
4. **Coverage needs no second test run.** Read the existing `lcov.info` / `coverage-final.json` and
   intersect its file set with the diff. Re-running the suite to produce a number you already have
   computed is pure latency.
5. **Check licences before vendoring a rule packs.** A shared-config or ruleset pulled from npm
   carries its author's licence into your repo, and some forbid redistribution. Verify the licence,
   pin the version, and prefer copying the individual rules you need into your own config.
6. **Pin the tool version.** A checker that floats is a gate that moves without a commit — which is
   the same failure mode as lowering a threshold, just less visible.
7. **Exit codes must be non-zero on failure.** Verify by deliberately breaking something and
   observing the non-zero exit; a check that cannot fail is decoration.

## The three-stage script split

```jsonc
{
  "scripts": {
    "check:fast":  "npm run typecheck && npm run lint",
    "check:task":  "npm run check:fast && npm run test && npm run coverage:changed && npm run guard",
    "check:full":  "npm run check:task && npm run audit && npm run a11y && npm run size",
    "guard":       "python3 scripts/floor-guard.py --base origin/main"
  }
}
```

Budgets: `check:fast` < 5s (every save), `check:task` < 90s (per change), `check:full` in CI.
`stryker` runs on a schedule, not in `check:full`, because it does not fit either budget.

`CONSTRAINTS.md` is the source of truth. If a script disagrees with it, the file wins and the
script is a bug.
