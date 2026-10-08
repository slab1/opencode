# Launch checklist — expanded

The `SKILL.md` version is the gate. This is the detail behind each item, written
to be argued with. An item marked *(often skipped)* is one that keeps showing up
in retrospectives.

## Code Quality

- Tests pass in CI on the **exact commit** being released, not on `main` from
  this morning. CI on a different SHA is not evidence about this SHA. *(often
  skipped)*
- Typecheck and lint at CI's strictness, not the local, more forgiving config.
- No debug artifacts: `console.log`, `print()`, `.only`, commented-out blocks,
  `FIXME` from today.
- The diff was read by someone who did not write it. "I reviewed my own PR" is
  not a review.
- Migrations apply from empty **and** roll back. The `down` was run. *(often
  skipped — and the moment you need it, it is untested)*
- Feature behind a flag that defaults to OFF.
- Third-party API contracts re-checked against current docs if the change depends
  on one; a vendor deprecation is your trigger, not theirs.
- Feature is usable when a downstream service is down (graceful degradation) or
  the failure is at least loud.

## Security

- No secrets in the diff, in logs, in analytics payloads, or in the client bundle.
  Check the **built** bundle, not the source.
- New endpoints: authentication **and** authorization. "They must be logged in" is
  not authorization — check per-tenant and per-role, and check the *default* is
  deny. *(often skipped)*
- Input validated at the boundary (schema validation, not string checks);
  output escaped at the render (framework escaping on, no raw HTML sinks).
- Dependency scan run. New advisories triaged with a decision recorded, not
  dismissed by the default ignore list.
- PII: nothing new in logs, traces, or client-side analytics. Check what the
  error reporter captures.
- Rate limiting on every unauthenticated or expensive endpoint.
- CSRF protection on state-changing cookie-authenticated routes.
- File uploads: type and size validated, stored outside the web root, served
  with a safe content type.
- Redirects and callback URLs validated against an allowlist.

## Performance

- Bundle size measured **gzipped**, per route, before and after. Delta recorded in
  the PR. *(often skipped — the bundle grows every deploy and nobody diffs it)*
- Every new query has a plan: `EXPLAIN ANALYZE`, not `EXPLAIN`. Look for
  sequential scans on large tables and row-count estimates off by orders of
  magnitude.
- N+1 check on the new paths: a query inside a loop is a finding even if each
  query is fast.
- Every list/query has a `LIMIT` or a bounded default page size.
- No unbounded fan-out: a loop over a webhook or a child-record walk has no cap.
- Cache keys include everything that changes the response (tenant, locale,
  permissions, flags) — see `performance-optimization`.
- Core Web Vitals on affected pages: LCP / INP / CLS at field p75, not just
  Lighthouse on a laptop.
- Background work is queued, not done inline in the request.

## Accessibility

- Keyboard only: tab order reaches every interactive element, operation order
  is logical, no traps outside modals.
- Modals: focus moved in on open, trapped while open, **restored to the trigger
  on close**, `Escape` closes, background marked `inert` or `aria-hidden`.
- Contrast: 4.5:1 for body text, 3:1 for large text and UI component boundaries
  (focus rings included — a focus ring you cannot see is not a focus ring).
- Accessible names on every control; decorative icons `aria-hidden`; icon-only
  buttons get a label.
- Dynamic changes announced: toasts and validation errors use a live region;
  the change is not colour-only.
- `prefers-reduced-motion` respected for animation and parallax.
- Zoom to 200% without loss of content or function; no horizontal scroll at
  320px.
- Custom controls expose the right roles and states (`aria-expanded`,
  `aria-selected`, `aria-current`).

## Infrastructure

- Config and secrets exist in the **target** environment before the deploy, not
  added after the first crash. *(often skipped)*
- Connection pool: `instances x pool_max` against the database's `max_connections`,
  with headroom for admin sessions and migrations.
- Memory and queue depth checked against the actual load the change adds.
- Third-party quotas and rate limits: the change must not exceed the plan.
- Deploy is idempotent and re-runnable. A half-applied deploy has a documented
  recovery.
- Backups are recent **and a restore has been tested**. A backup that has never
  been restored is a hypothesis.
- Dashboards and alerts exist for the new path **before** it has traffic, and
  the alert has been triggered once on purpose to prove it works.
- Health/readiness endpoints reflect the new dependency; an unhealthy dependency
  removes the instance instead of serving broken responses.
- Rollback and roll-forward procedures are written down, and the rollback one is
  rehearsed.

## Documentation

- Changelog entry written before release, in user language, describing behaviour
  change (not commit messages).
- Migration guide run end to end by someone who did not write it, on a clean
  environment. *(often skipped)*
- Runbook updated: the new failure modes, their first diagnostic command, and the
  expected output.
- Support and ops told what is shipping, when, what users will notice, and what
  normal looks like for the first 48 hours.
- Deprecation notices sent directly to consumers, with removal dates and
  migration guides — see `deprecation-and-migration`.
- Architecture/decision record updated if a non-obvious tradeoff was made.

## Sign-off question

Before go/no-go, answer these four out loud. An unanswerable one is the blocker:

1. If this goes wrong at 3am, who is woken and what do they do first?
2. How long until we know it went wrong?
3. What is the exact command that undoes it?
4. What data, if any, does that command *not* undo?