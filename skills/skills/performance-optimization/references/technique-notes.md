# Technique notes — detail behind Step 3

Each entry: signature (how you recognize it), rule, fix, and the way it fails.

## N+1

**Signature:** latency grows linearly with page size; a query repeats with one
changing parameter; ORM query counter climbs with result count.

**Fix:** fetch the relation in the same query.

```sql
-- explicit join
SELECT p.*, a.display_name FROM posts p JOIN authors a ON a.id = p.author_id;
-- or IN(...) with ids collected first — two queries, not N
SELECT * FROM authors WHERE id IN (%s, %s, %s);
```

**Fails when:** the join fans out (a join across a many-to-many multiplies rows),
the ORM lazy-loads anyway because you navigated a property not covered by the
prefetch, or pagination happens after the join instead of before it.

**Check:** count queries in the test/dev log. The number should be constant as
page size grows. A constant count is the regression test — write it with
`tdd-workflow` so the N+1 cannot come back.

## Indexes

**Signature:** a query whose plan does a sequential scan on a large table, or
whose estimated rows are wildly wrong.

### Read the plan first

```
EXPLAIN ANALYZE SELECT ...;
-- Seq Scan on orders  (cost=0.00..48210.00 rows=1200000 actual rows=1198433 time=...)
--                                                            ^^^^^^^  ^^^^^^^
--                                                            estimate  actual
```

| Symptom | Meaning | Fix |
|---|---|---|
| `estimate` off by >10x | Stale stats | `ANALYZE <table>`; adjust `default_statistics_target` for the column |
| Seq scan, high-selectivity predicate | Missing index | B-tree on the filter/sort columns |
| Seq scan kept after indexing, `status='active'` where 95% are active | Low selectivity | Partial index `WHERE status='active'` |
| `LIKE '%foo'` | B-tree unusable | `pg_trgm` GIN index, or full-text search |
| `WHERE lower(email) = ?` | Function wraps the column | `CREATE INDEX ON users (lower(email))`, query must use the identical expression |
| Index present but unused | Planner decided a scan was cheaper | Check the estimate before assuming it is a bug |
| Index present, `rows` now fine, still slow | The problem was not I/O | Look at the next cost — it is usually `Sort` or a heap fetch |

### Rules

- Build large indexes with `CREATE INDEX CONCURRENTLY`; it cannot run in a
  transaction and leaves an invalid index if it fails (`DROP` and retry).
- Every index taxes every write and grows the database. An index whose plan did
  not change is a revert.
- Check for redundancy: an index on `(a, b)` often covers queries filtering on
  `a` alone. Find unused indexes from `pg_stat_user_indexes.idx_scan = 0` over a
  real workload period.
- Partial indexes are free wins on large tables with a small hot subset.

## Connection pools

**Signature:** every endpoint slows simultaneously; the DB shows many sessions
`idle in transaction` / `idle`, not `active`.

That combination is the diagnostic: the app is queuing for a connection, so the
DB is idle while users wait.

```
app instances  x  pool_max   must be  <  max_connections  (with headroom)
```

10 x 20 = 200 against `max_connections = 100` is a self-inflicted outage. Reserve
headroom for migrations, replication workers, the health checker, and a human with
psql.

**Serverless:** instance count is a function of request concurrency, so pool size
is unbounded in practice. Use pgbouncer in transaction mode, and keep a separate
direct connection for migrations (transaction mode breaks session-level features
like `SET`, advisory locks, and prepared statements).

**Fails when:** raising the pool to "fix" it — that just moves the queue into
Postgres, where it is harder to see and where more concurrent queries make
contention worse, not better.

**Also check:** a slow query holding a connection. That shows as *active* sessions
with a long duration, and the fix is the query, not the pool.

## Caching

**Both conditions required:** expensive to produce **and** re-read far more
often than it changes.

| Data | Cacheable? | Why |
|---|---|---|
| Reference/config data, rarely changes | Yes | Classic case |
| Read-heavy aggregate, recomputed | Yes | Expensive and re-read constantly |
| A 4ms primary-key lookup | **No** | Caching adds a hop and a staleness bug for nothing |
| Account balance | **No** | Wrong to be stale |
| Permission check | **No** | Wrong to be stale = privilege escalation |
| Inventory count | **No** | Overselling is a real-world cost |
| User-specific computed report | Yes, if the key includes the user and tenant | Tenant leakage otherwise |

### Key design

Every input that changes the response belongs in the key:

```
key = f"{api_version}:{resource}:{tenant_id}:{user_id}:{locale}:{permission_tier}:{feature_flags_hash}"
```

Version the prefix (`v3:`). It is the cheapest, most reliable invalidation there
is: bump the version, old keys become garbage, no scan required.

The missing-tenant failure is the classic multi-tenant incident. When a cache
incident happens, audit the key first, before the eviction policy.

### Invalidation

Pick **one** strategy and write the staleness window as a number:

- **TTL** — simplest, staleness bounded by the TTL. Pick it when the data is
  eventually consistent anyway.
- **Event-driven** — invalidate on write. Correctness-sensitive; needs to be
  actually wired, and a missed event is a permanently stale key.
- **Write-through** — update the cache in the write path. Low staleness, adds
  latency and a second failure mode to your writes.

A cache with no stated staleness window is a cache with an unknown correctness
property.

### Stampede

A hot key expiring sends every concurrent request to the backend at once — the
classic "periodically the site falls over for 30 seconds" pattern.

Two fixes:

1. **Serve stale while recomputing** — return the old value, refresh in the
   background (needs a grace period longer than the recompute).
2. **Coalesce misses** — singleflight/lock so one request recomputes and the rest
   wait or read the fresh value.

```python
value = cache.get(key)
if value is None:
    with singleflight(key):          # only one recompute at a time
        value = cache.get(key)
        if value is None:
            value = compute()
            cache.set(key, value, ttl)
return value
```

## Frontend rendering

### Unstable references

An object or function literal created during render is a new reference every
render, so `React.memo`/`useMemo` children re-render anyway:

```jsx
// new object every render -> memoized child re-renders every time
<Filters options={{ active: 1, sort: 'name' }} />

// stable module constant
const DEFAULT_FILTERS = { active: 1, sort: 'name' };
<Filters options={DEFAULT_FILTERS} />

// stable function
const onSelect = useCallback((id) => setActive(id), []);
<Filters options={DEFAULT_FILTERS} onSelect={onSelect} />
```

But: **reserve `React.memo` and `useMemo` for work the profile shows is
expensive, since overuse is its own cost.** Each hook allocates a dependency
array, adds a comparison, and adds a way to be wrong (a missing dependency is a
stale-closure bug). Forty memoized rows that render in 0.2ms are worse than none.

Profile before you memoize. A long list's cost is usually the count of rendered
rows, not the per-row cost.

### Long tasks and INP

INP measures input → next paint. The work between them is your handler plus
everything it triggers synchronously: state updates, re-renders, layout, and
layout thrashing.

- Split work: `startTransition` for non-urgent updates; `useDeferredValue` for
  expensive derived values.
- Avoid layout thrashing — interleaved reads and writes of layout properties
  (`offsetHeight` between a style write and a class change) force synchronous
  reflow. Batch reads, then batch writes.
- Move heavy work off the interaction: a web worker, or defer it.
- Virtualize long lists (thousands of rows). Fixed-height virtualization is much
  simpler than variable-height — start there.

### Images

```html
<img src="hero.avif"
     srcset="hero-640.avif 640w, hero-1280.avif 1280w"
     sizes="100vw"
     width="1280" height="720"        <!-- reserves space: no CLS -->
     alt="Descriptive, not 'hero image'"
     fetchpriority="high"             <!-- the LCP image -->
     decoding="async" />

<img src="below-fold.avif" loading="lazy" width="640" height="480" alt="…">
```

- `loading="lazy"` on the LCP image makes LCP **worse** — the browser defers
  the fetch the metric measures.
- Missing `width`/`height` (or `aspect-ratio`) = layout shift. This is the
  highest-frequency CLS cause in the wild.
- Serve AVIF (with WebP fallback), `srcset` for real device widths, and don't
  ship a 2400px file to a phone.

### Bundles

- Tree-shaking works for ESM named imports already. `import _ from 'lodash'`
  pulling the whole library is the real problem; import the named function.
- Route-level `import()` + `Suspense` is the big win: ship the code for the route
  you are on, not the code for the app.
- Heavy, rarely-used libraries (PDF, editors, charting, date-fns) load on demand.
- Watch for a dependency added for one helper: 200KB for a date format is a
  finding in review.

## Server and runtime

- **TTFB**: check it before blaming the frontend. A 900ms TTFB caps LCP at 900ms
  no matter how fast the rest is.
- **Nagle / delayed ACK** interactions with small responses: usually a red
  herring, occasionally real.
- **Garbage collection pauses** are the tail-latency story in most runtimes —
  look for p99 with a flat p50.
- **Lock contention** shows as tail latency with short queries; look at
  `pg_locks` under load.