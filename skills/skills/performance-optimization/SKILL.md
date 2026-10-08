---
name: performance-optimization
description: "Measure, fix, verify, and guard web and application performance against Core Web Vitals and performance budgets, covering N+1 queries, indexes, connection pools, caching, and frontend rendering. Use when a page or endpoint is slow, a Core Web Vital regresses, an INP/LCP/CLS investigation is needed, or before shipping a performance budget. Triggers on slow, performance, optimize, profiling, Core Web Vitals, LCP, INP, CLS, FCP, TTI, latency, N+1, index, slow query, connection pool, cache, bundle size, Lighthouse."
license: MIT
metadata:
  author: opencode-meta-agent
  version: "1.0.0"
  source: "adapted from addyosmani/agent-skills (open patterns, not copied prose)"
---

# Performance Optimization

## Overview

Performance work fails in one of two ways: you optimize the wrong thing, or you
optimize the right thing and keep it because it "didn't hurt". Both are avoided
by the same discipline — **measure, change one thing, re-measure, and be willing
to revert**.

The workflow is fixed:

```
1. MEASURE  ->  2. IDENTIFY  ->  3. FIX  ->  4. VERIFY (keep or revert)  ->  5. GUARD
```

Step 4 is where most teams skip, and it is the reason performance work has a bad
reputation: a pile of plausible optimizations that nobody measured, kept forever
because they "seemed right", now permanent complexity with no measurable payoff.
**"Neutral" is a revert, not a keep.**

Load `references/measurement.md` for tooling setup and profiling technique, and
`references/technique-notes.md` for the deep detail on each fix in Step 3.

## When to Use

- A page feels slow, or a Core Web Vital is failing in the field
- INP, LCP, or CLS crossed a threshold (or is trending toward one)
- An endpoint's p95/p99 latency is above target
- A query is slow, or a dashboard/alert says the database is struggling
- Before setting or enforcing a performance budget (Step 5)
- After a change, to confirm you did not regress something
- Deciding whether a specific optimization idea is worth doing (Step 4)

## When NOT to Use

- **The feature does not work yet.** Correctness first; a fast wrong answer is
  still wrong. Use `tdd-workflow`.
- **No baseline exists.** If you cannot measure "before", you cannot do this
  skill — you can only guess. Establish the measurement first.
- **Third-party latency you do not control** (an upstream API, a CDN miss, a
  vendor's own outage). You can cache around it or fail over; you cannot make it
  faster. Say which you are doing instead of tuning your code at random.
- **Micro-optimizations with no measurement** — loop unrolling, string
  concatenation, "this looks faster". Step 4 will revert them; skip to the end.
- **Product tradeoffs that are not performance problems** — e.g. "the feature
  requires a big query". That is a scope conversation, not an optimization.

## The Process

### 1. MEASURE

You cannot skip this, and you cannot substitute opinion for it. Two kinds of
measurement, and you need both at different stages:

| | **Synthetic** | **RUM / field** |
|---|---|---|
| Tools | Lighthouse, DevTools Performance panel, `lighthouse-ci` | `web-vitals` library, CrUX, APM traces |
| Controlled | yes — same device, throttling, network every run | no — whatever the user had |
| Reproducible | yes | no (noisy, but real) |
| Best for | CI gates, A/B comparison of two commits | **validating that a fix actually improved user experience** |
| Blind spot | does not represent your real users or your real data volumes | cannot A/B two commits quickly |

Rule: **synthetic is where you iterate, field data is where you validate.** A
synthetic win you never confirm with field data is a hypothesis. A field metric
you cannot reproduce is a story. Do both, in that order.

```js
// field measurement — ship this on every page you care about
import { onLCP, onINP, onCLS } from 'web-vitals/attribution';

const report = (metric) => navigator.sendBeacon('/rum', JSON.stringify({
  name: metric.name, value: metric.value,
  rating: metric.rating, id: metric.id, path: location.pathname,
}));
onLCP(report); onINP(report); onCLS(report);
// sendBeacon is fire-and-forget and survives page unload; fetch().keepalive
// with a JSON blob is the fallback.
```

Note `onINP` requires `web-vitals` v4+; v3 had `onFID`, which is not INP.

### 2. IDENTIFY

Find the actual bottleneck. Do not skip to the fix you already have in mind —
the most common performance bug is optimizing the wrong layer.

- **Is it the network or the main thread?** LCP is usually network and image.
  INP is almost always main-thread JavaScript.
- **Which of the three?** LCP = load, INP = interactivity, CLS = visual
  stability. Each has a different cause and a different fix; a fix for one does
  nothing for the others.
- **Real users or one slow device?** One anecdote is not a distribution. Check
  field percentiles by device class and connection type — the fix for the 1% slow
  connection is different from the fix for the median desktop user.
- **Which layer?** Trace before theorizing: browser devtools for frontend, APM
  for the request path, `EXPLAIN ANALYZE` for the database. The layer matters
  because the fixes are unrelated.

### 3. FIX

Apply the technique that matches the bottleneck (see the technique list below).
**One change at a time.** Three optimizations landed together produce one
number, and if it moves you cannot tell which one did it or which one to revert.

### 4. VERIFY — keep or revert

Re-measure with the *same method* as the baseline, then decide:

| Result vs baseline | Action |
|---|---|
| Past the threshold, tests green | **Keep.** Commit with the before/after numbers in the message. |
| Within noise (no measurable change) | **Revert.** |
| Worse | **Revert.** |
| Improved, but a test went red | **Revert.** A regression wearing a win's clothing. |

Three supporting rules:

- **Re-measure the way you measured the baseline** — a baseline on a cold cache
  against a result on a warm one measures the cache, not your change.
- **Change one thing at a time.** Three optimizations landed together produce one
  number.
- **Beat the noise, not just the mean.** A 3% gain inside ±5% variance is not a
  gain. Repeat noisy measurements or compare medians/trends; a single Lighthouse
  score has several points of run-to-run variance on its own.

**Verdict: "neutral" is a revert, not a keep.** The cost of a kept-but-neutral
change is permanent complexity — someone must understand, maintain, and not
accidentally break it — in exchange for zero user benefit. Reverting is cheap
while the change is one commit old.

### 5. GUARD

An unmeasured optimization regresses silently. Put a budget in CI so the next
person cannot quietly undo your work.

**Step 5 budgets** (starting points — tune to your product):

| Budget | Target |
|---|---|
| JS bundle (per route) | < 200 KB gzipped |
| CSS | < 50 KB gzipped |
| Images above the fold | < 200 KB total |
| Fonts | < 100 KB total |
| API response | < 200 ms p95 |
| TTI | < 3.5 s on simulated 4G |
| Lighthouse Performance | ≥ 90 |

Enforce budgets in CI (`lighthouse-ci` with `assert`, or `size-limit`), not in a
document nobody opens.

> Repeat noisy measurements or compare a median/trend so normal run-to-run
> variance does not turn the gate into a flaky check.

A flaky performance gate is worse than no gate: the team learns to re-run it, and
then to ignore it, and now nothing is enforced. Use multiple runs and a median, or
compare against a stored baseline with a tolerance band, or run the budget check
on a nightly branch rather than every PR.

## Core Web Vitals — targets

| Metric | Good | Needs improvement | Poor | What it measures |
|---|---|---|---|---|
| **LCP** (Largest Contentful Paint) | ≤ 2.5 s | ≤ 4.0 s | > 4.0 s | when the main content appeared |
| **INP** (Interaction to Next Paint) | ≤ 200 ms | ≤ 500 ms | > 500 ms | responsiveness to user input |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | ≤ 0.25 | > 0.25 | visual stability of the page |

Judged at the **75th percentile** of field data, segmented by mobile and desktop,
against real users. A perfect score on your laptop and a poor p75 means your
users — on mid-range Android on 4G — are having a bad time, and your Lighthouse
score was measuring your laptop.

Related legacy metrics (still useful diagnostically, but do not gate on them):
TTFB (server response), FCP (server + render path), TBT and TTI (lab proxies for
responsiveness that INP has largely replaced). Tooling and how to read a trace:
`references/measurement.md`.

## Step 3 techniques

### N+1 queries

**Signature:** page gets slow with more rows; a query appears in a log once per
row; ORM query counts scale with the result count.

**Rule:** join/include instead of a query in a loop.

```python
# N+1: one query for posts, then one per post for author
posts = Post.objects.all()
for p in posts:
    p.author.display_name          # <-- fires a query

# single query with the relation preloaded
posts = Post.objects.select_related("author").all()   # FK/OneToOne
posts = Post.objects.prefetch_related("tags").all()   # reverse FK/M2M
```

Nested graphs need both: `select_related` for the join direction, `prefetch_related`
for the reverse, and a second query per relation is *fine* — two queries is the
goal, not one. In ORM-literal-SQL codebases the fix is an explicit join or an
`IN (...)` query with the ids already collected.

### Indexes

**Rule:** "'Add an index' is the guess; `EXPLAIN ANALYZE` is the measurement."

Start with `EXPLAIN ANALYZE <query>` and read three things: estimated rows vs.
actual rows, the plan shape, and total time.

- **Bad `rows=` estimate** (usually off by 10x+) → stale statistics. Run
  `ANALYZE <table>` first. An index on a badly-estimated query often fixes
  nothing, because the planner still thinks the table is tiny.
- **Plain index fails on a low-selectivity dominant value** (e.g. `WHERE
  status = 'active'` where 95% of rows are active) → the planner will correctly
  ignore it. Use a **partial** index:
  `CREATE INDEX ON orders (created_at) WHERE status = 'active';`
- **Leading wildcard** (`LIKE '%foo'`) → B-tree cannot help. Use a **trigram**
  index (`pg_trgm` + `GIN`) or full-text search.
- **Function on a column** (`WHERE lower(email) = ?`) → index the *expression*:
  `CREATE INDEX ON users (lower(email));` and write the query with the same
  expression.

```sql
-- build large indexes without blocking writes (not inside a transaction)
CREATE INDEX CONCURRENTLY idx_orders_customer ON orders (customer_id);
-- if it fails it leaves an INVALID index: DROP then retry.
CREATE INDEX CONCURRENTLY idx_orders_active
  ON orders (created_at) WHERE status = 'active';      -- partial
```

**Every index taxes every write.** An index makes reads faster and inserts,
updates, and deletes slower and bigger — and it grows the database. Re-run the
plan afterwards; **an index that did not change the plan is a revert.** Delete
unused indexes (check `pg_stat_user_indexes.idx_scan = 0` over a real workload,
not a fresh database).

### Connection pools

**Signature:** *every* endpoint slows at once AND the database shows mostly
**idle** sessions. Idle sessions are the tell: a pool problem looks like
saturation at the app and like idleness at the DB, because connections are
waiting to check out, not executing.

**Rule:** `instances x pool_max` must stay under the database ceiling.

10 app instances x 20 connections = 200 connections, on a DB with
`max_connections = 100`. Now half the connections are refused and the app is
starving on the DB's behalf. Leaving headroom matters for migrations, admin
sessions, replication, and the health checker.

> **Bigger is not faster; it relocates the queue to the database where it is
> harder to see.** A pool of 500 does not make queries faster — it makes 500
> queries wait inside Postgres instead of waiting in your app.

Serverless does not fix this, it multiplies it: hundreds of concurrent instances
each opening a pool. Use a **multiplexer** (pgbouncer in transaction mode) so
many client connections share a small number of server connections, and prefer a
direct connection for migrations.

### Caching

**Rule:** cache what is (a) expensive **and** (b) re-read far more often than it
changes.

Both halves are required. A cheap query read once does not benefit, and an
expensive query read hourly gains nothing from a cache that costs you an
invalidation bug. **Caching an already-fast query adds a network hop and a
staleness bug in exchange for nothing.**

**Every input that changes the response belongs in the key**: tenant, locale,
permissions, feature flags, currency, plan tier. A key that omits the viewer is
how one user's data gets served to another — a cross-tenant data leak, not a
performance bug. When a cache incident happens, this is the first thing to audit.

```python
# the key is the contract
key = f"v3:summary:{tenant_id}:{locale}:{permission_tier}:{period}"
```

Three more rules:

1. **One invalidation strategy, and an explicit staleness window.** TTL-only is
   a legitimate strategy; so are event-driven invalidation and write-through. What
   is not acceptable is "we'll clear it eventually" — state the maximum staleness
   in the code, and make it a number someone can answer a question about.
2. **Stampede guard.** When a hot key expires, every concurrent request misses and
   recomputes it. Serve stale while recomputing in the background, or coalesce
   concurrent misses with a lock/singleflight.
3. **Never cache balances, permissions, or inventory.** These are not "slow to
   recompute"; they are *wrong to be stale*. Caching a permission check is a
   privilege-escalation bug waiting for its window.

### Frontend

**Images** — the most common LCP and CLS cause, and the most fixable:

- Explicit `width`/`height` (or `aspect-ratio`) on every image so the browser
  reserves space. Missing dimensions = guaranteed CLS.
- `fetchpriority="high"` on the LCP image; `loading="lazy"` on everything below
  the fold. Lazy-loading the LCP image makes it *slower*.
- Serve AVIF/WebP with `srcset` and `sizes` so phones get small files.
- Do not lazy-load the hero. Do not lazy-load anything above the fold.

**Rendering** — the INP cause:

- An object or function created during render is a **new reference every time**,
  so every memoized child re-renders. Hoist it, declare it outside the component,
  or wrap it in `useMemo`/`useCallback` when it is a dependency of something
  already memoized. Worked code in `references/technique-notes.md`.
- **Reserve `React.memo` and `useMemo` for work the profile shows is expensive,
  since overuse is its own cost.** Each memo allocates, compares, and adds a
  thing to reason about; `memo` on twenty rows that are cheap to render is a net
  loss and a source of stale-prop bugs.
- Key lists by stable identity, never by index.
- Long tasks: yield, chunk the work, or move it off the interaction path.

**Bundles:**

- Bundlers tree-shake ESM named imports on their own. Do not hand-optimize
  import syntax for shaking — that battle was won by the tooling.
- Real gains come from **route-level splitting** plus `Suspense` boundaries, and
  from deleting dependencies rather than tricking them.
- Heavy libraries (charting, editors, date libs, PDF) load on demand at the
  interaction that needs them.

## The attempt ledger

Reverted work leaves no trace in git history, which is exactly why the same dead
idea gets tried again next quarter. Ship the ledger as a PR section or a
`PERF.md`:

| Idea | Baseline -> Result | Verdict | Why |
|---|---|---|---|
| Memoize the row component | INP 240ms -> 235ms | reverted | Inside noise (±15ms). Rows weren't the bottleneck. |
| Virtualize the list | INP 240ms -> 90ms | kept | Long tasks gone from the trace. |
| Preconnect to the API origin | LCP 2.8s -> 2.8s | reverted | Already same-origin. |

The ledger makes three things possible: nobody re-runs an experiment already
proven neutral, the *why* survives past the person who ran it, and the "obvious"
optimizations get one measured attempt instead of infinite confident ones.

## Common Rationalizations

| The excuse | The reality |
|---|---|
| "We'll optimize later" | Later is after the traffic, the dataset, and the p75 regression that made it an incident. The list of cheap structural fixes (image dimensions, N+1, missing index, unstable references) is knowable now and expensive to find later under load. |
| "It's fast on my machine" | Your machine is not the p75 user. Field data at the 75th percentile on mid-range mobile over 4G is the metric, and it is routinely 3-10x worse than your laptop. |
| "This optimization is obvious" | Obvious is not measurable. The most convincing "obvious" wins in review history turned out to be inside the noise — the ledger exists because of those. |
| "Users won't notice 100ms" | Users do not notice, but they abandon, and you cannot detect abandonment from a chart you did not instrument. Aggregate over a month and it is your conversion rate. |
| "The framework handles performance" | The framework handles rendering efficiently. It does not stop you fetching the same data five times, rendering a thousand rows, or shipping a 900KB dependency you imported for one function. |
| "The query is slow, add an index" | "'Add an index' is the guess; `EXPLAIN ANALYZE` is the measurement." A bad row estimate means the index will be ignored. A low-selectivity or leading-wildcard or function-wrapped column needs a partial, trigram, or expression index instead. And an index taxes every write. |
| "Just cache it" | Only if it is expensive *and* re-read far more often than it changes. An already-fast query gains a network hop and a staleness bug. And the cache key must include tenant, locale, permissions, and flags — a key that omits the viewer is how one user's data gets served to another. |
| "Raise the pool size, we're running out of connections" | *Every* endpoint slow plus mostly **idle** DB sessions means the pool is the constraint, and raising the cap usually exceeds `max_connections` and makes it worse. Bigger is not faster; it relocates the queue into the database where it is harder to see. |
| "It didn't help much, but it doesn't hurt" | It hurts: permanent complexity someone must maintain, understand, and not break — for zero user benefit. "Neutral" is a revert, not a keep. |
| "We already wrote it, may as well keep it" | Sunk cost. The question is only whether the code should exist now, and a reverted experiment costs one revert commit while a kept one costs forever. |
| "The improvement is obvious, no need to re-measure" | Then you have a baseline and a result that differ by less than the variance, and you will write "2x faster" in a PR body. Re-measure, or do not claim it. |
| "We measured once on a warm cache, it's fine" | A cold-cache baseline against a warm result measures the cache. Same conditions, or the number is fiction. |

## Red Flags

- An optimization merged with no before/after numbers in the commit or PR body
- A commit message claiming "much faster" / "significantly improved" with no
  measurement attached
- Optimizing a single anecdote (one user's report, one device) with no field
  percentile check
- An index added without re-running the query plan afterwards — especially with
  no check of whether existing indexes already cover it
- A cache key missing tenant, locale, permission, or feature-flag inputs
- Cached balances, permissions, or inventory
- No staleness window written down anywhere; invalidation is "we'll clear it"
- `React.memo`/`useMemo` applied broadly without a profile showing the work is
  expensive
- Pool size raised above the database's `max_connections` headroom
- Images without explicit dimensions, or the LCP image marked `loading="lazy"`
- A performance budget documented but not enforced in CI
- CI gating on a single noisy Lighthouse run (a flaky gate gets ignored, then
  enforces nothing)
- No reverted-experiment record anywhere, guaranteeing the same dead idea returns
- "It's faster" asserted on the basis of a dev-machine reload

## Verification

- [ ] Baseline captured **before** the change: metric, method, device/network
      conditions, and the raw numbers written down
- [ ] Bottleneck identified from a trace or `EXPLAIN ANALYZE`, not assumed — and
      the identified layer recorded
- [ ] Exactly one change per measurement; the others queued behind it
- [ ] Re-measured with the identical method and conditions as the baseline
- [ ] Result compared against the run-to-run variance; a 3% change inside ±5% is
      treated as no change
- [ ] Keep-or-revert decision made against the Step 4 table and recorded
- [ ] If kept: before/after numbers in the commit message
- [ ] If reverted: reverted, and the attempt recorded in the ledger (`PERF.md`
      or the PR section) with the reason
- [ ] Full test suite green before keeping any change
- [ ] New query plans checked with `EXPLAIN ANALYZE`; index verified used
- [ ] Cache keys audited to include tenant, locale, permissions, and flags
- [ ] Cache staleness window written down; stampede guard considered for hot keys
- [ ] Images verified with explicit dimensions, `fetchpriority` on the LCP one,
      lazy-loading only below the fold
- [ ] Field (RUM) data re-checked after the fix, not just the synthetic number
- [ ] Budgets enforced in CI, using repeated runs/medians so the gate is not flaky
- [ ] `PERF.md` or ledger updated with this experiment's verdict
- [ ] If this was a `designer`-adjacent UI change, visual output re-checked in a
      browser after the perf work (dev agent should confirm nothing regressed
      visually, e.g. an image stripped of its dimensions now misaligned)

## See Also

- [shipping-and-launch](../shipping-and-launch/SKILL.md) — the Performance
  subsection of the pre-launch checklist, and the staged rollout that validates a
  perf fix on real traffic
- [deprecation-and-migration](../deprecation-and-migration/SKILL.md) — expand/
  contract for adding an index or a column without a maintenance window
- [supabase-postgres-best-practices](../supabase-postgres-best-practices/SKILL.md) —
  query plans, index strategy, and pool sizing detail for Postgres
- [verification-planning](../../verification-planning/SKILL.md) — designing the
  measurement plan up front, so the baseline exists before the change
- [debug-systematic-investigation](../debug-systematic-investigation/SKILL.md) —
  the hypothesis discipline this skill inherits; use it when a regression's cause
  is not yet identified
- [tdd-workflow](../tdd-workflow/SKILL.md) — the correctness gate that Step 4 uses
  to veto a performance win that turned a test red
- [refactor-safe](../refactor-safe/SKILL.md) — one-change-at-a-time is the same
  discipline this skill requires before measuring
- [security-audit](../security-audit/SKILL.md) — cache keys and cached
  permission checks are security-relevant, not just performance-relevant
- [error-recovery-protocol](../error-recovery-protocol/SKILL.md) — when a
  performance change causes an outage, this is the rollback path
- [git-commit-hygiene](../git-commit-hygiene/SKILL.md) — a revert is a commit;
  keeping perf experiments in one commit each makes reverting trivial
- The `web-design-guidelines` skill (under the openmontage bundle, not directly
  under `skills/`) covers the rendering-quality side of the same pages. For visual
  work, hand it to the `designer` agent by name — there is no agent file to link.