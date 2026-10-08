# Measurement — tooling and profiling technique

## Which metric, which layer

| Symptom | Metric | Usual layer | Where to look |
|---|---|---|---|
| Blank/fast-looking page until something pops in | LCP | network, image, server TTFB | waterfall, TTFB, image bytes |
| Typing/clicking feels sticky | INP | main-thread JS | long tasks in the Performance panel, heavy re-renders |
| Content jumps around while loading | CLS | missing dimensions, late CSS, ads | layout shift entries, element source |
| Spinner, everything fine afterwards | TTFB / server | backend, DB | APM span breakdown, `EXPLAIN ANALYZE` |

Do not chase INP with an image fix, or LCP with `useMemo`. A fix for one vital
does nothing for the others.

## Field measurement (RUM)

```js
// web-vitals v4+; onINP replaced onFID in v4
import { onLCP, onINP, onCLS } from 'web-vitals/attribution';

function send(metric) {
  const body = JSON.stringify({
    name: metric.name,
    value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
    rating: metric.rating,
    id: metric.id,                 // ties entries to the INP interaction that caused it
    path: location.pathname,
    // attribution (v4 only, needs attribution build):
    // target: metric.attribution?.target, field: metric.attribution?.field
  });
  navigator.sendBeacon('/rum', new Blob([body], { type: 'application/json' }));
}
onLCP(send); onINP(send); onCLS(send);
```

Reporting rules that matter:

- CLS is a unitless score; send it × 1000 so it lands in an integer column.
- Always send `metric.id`. Without it you cannot dedupe the same shift reported
  repeatedly, and your p75 is noise.
- Sample if volume is high, but never sample INP-only pages — INP needs the
  interaction that produced it.
- `sendBeacon` survives unload; `fetch` with `keepalive: true` is the fallback.
- Do not gate CI on RUM. Gate CI on synthetic; use RUM to validate.

## CrUX / field percentiles

CrUX gives p75 aggregates by origin (or URL) from real Chrome users:

```js
const url = 'https://api.crux.dev/v1?key=<KEY>';
const res = await fetch(`${url}&url=${encodeURILECT_URL('https://example.com')}`);
const { record: { metrics } } = await res.json();
console.log(metrics.largest_contentful_paint.percentiles); // { p75: ... }
```

If you do not have your own RUM, CrUX is the free fallback for a single origin.
It is monthly-ish and aggregate — too coarse for a canary, fine for "did the fix
help real people".

## Synthetic measurement

**Lighthouse CLI**, throttled, repeatable:

```bash
npx lighthouse https://example.com --throttling-method=simulate \
  --only-categories=performance --output=json --output-path=./lh.json
```

**lighthouse-ci** for a gate — this is the budget enforcement mechanism:

```bash
npx lhci autorun
```
```js
// lhci.config.js
module.exports = {
  ci: {
    collect: { url: ['https://example.com/'], numberOfRuns: 5 },  // 5 runs: median
    assert: {
      preset: 'lighthouse:recommended',
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
      },
    },
  },
};
```

`numberOfRuns: 5` is not optional if you want a stable gate. A single run has
several points of variance and the assert becomes a coin flip.

**Bundle budgets** with `size-limit`:

```json
{ "name": "main", "path": "dist/assets/main-*.js", "limit": "200 KB" }
```

## Reading the Performance panel

1. **Screenshots strip** — where the page is blank. The gap before the first
   content is your LCP problem.
2. **Network track** — waterfall; find the longest pole (a 900KB image on a
   slow connection) and the request chain depth (server → CDN → font → icon →
   icon).
3. **Main-thread track** — the red triangles are tasks >50ms; the grey is
   scripting/rendering/layout. Interaction-to-next-paint latency is time from a
   click to the next frame after the handler finishes.
4. **Long tasks are the INP story.** Anything over 50ms blocks interaction.
   Anything over 200ms is user-visible.
5. **Bottom-Up / flame chart** — the widest self-time frames are what to
   optimize. Wide ≠ deep, and a deep narrow stack may be irrelevant.
6. **Coverage panel** — CSS/JS bytes never executed. A dependency at 0% usage on
   the critical path is a free win.

## Backend

- **APM span breakdown** per request: where did the 400ms go? Framework,
  database, cache, third-party?
- **`EXPLAIN ANALYZE <query>`** — the ground truth. Read estimated vs. actual
  rows, and time the plan, not just read the shape.
- **Slow query log** with a threshold, or `pg_stat_statements` ordered by total
  time. The top statement by total time is almost always the highest-value
  target.
- **Percentiles, not averages.** A p99 of 2s behind a p50 of 30ms is a different
  problem from a p50 of 400ms: the first is tail (GC, lock contention, a cache
  stampede), the second is broad (a slow query everywhere).

## Variance discipline

The failure mode of every performance claim:

- Lighthouse scores on the same commit differ by several points run to run.
- Field data is noisier still, and p75 needs volume.
- The remedy: `numberOfRuns: 5` and take the median for synthetic; for RUM,
  compare a trend or a median over days, not a single day; always state the
  variance alongside the delta.

A change smaller than the noise floor is not a change. Measure the noise floor
once (run the baseline 5x, look at the spread) and hold the line against it.