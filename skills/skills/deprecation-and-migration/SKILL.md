---
name: deprecation-and-migration
description: "Decide whether to keep, deprecate, or remove a system, then migrate its users safely via strangler fig, adapters, feature flags, and database expand/contract. Use when an API, column, flag, dependency, or service is being replaced, sunset, renamed, or versioned out, or when a deprecation notice or migration plan is needed. Triggers on deprecate, deprecation, sunset, migrate, migration, breaking change, end-of-life, EOL, rename column, backfill, strangler, expand/contract, zombie code."
license: MIT
metadata:
  author: opencode-meta-agent
  version: "1.0.0"
  source: "adapted from addyosmani/agent-skills (open patterns, not copied prose)"
---

# Deprecation and Migration

## Overview

Deprecation is a business decision with an engineering tail. This skill covers the
decision (keep vs. deprecate vs. remove), the announcement, and — the part most
teams skip — actually moving the users off the old thing.

The core obligation: **whoever owns the infrastructure being deprecated is
responsible for migrating the users of it.** Notifying people is not migrating
them. A deprecation without a working migration path is a hostile act with a
polite vocabulary.

Load `references/expand-contract.md` for the long-form database playbook and
`references/deprecation-notices.md` for announcement and API-surface templates.

## When to Use

- Replacing an API, endpoint, RPC, config key, environment variable, or CLI flag
- Renaming, retyping, or splitting a database column or table
- Removing a dependency, vendored module, or internal library
- Versioning an interface out: `v1` -> `v2`, protocol versions, schema versions
- Declaring end-of-life for a service, job, cron, or feature
- Any consumer has to change code as a result of your change (breaking change)
- Auditing for zombie code: unused-by-us but depended-on-by-everyone
- Writing a deprecation notice, changelog entry, or migration guide

## When NOT to Use

- **Private, internal, single-team refactor** with no other consumers. Use
  `refactor-safe`: change it, ship it, no deprecation period.
- **A bug fix or security patch on a supported path.** That is not a migration.
- **Renaming a local variable, function, or type inside one file.** No consumer
  exists; a rename is a rename.
- **Version bumps inside a package you publish, where semver already governs the
  contract.** Follow your deprecation policy, not a new process.
- **Before a replacement exists.** Do not start this skill at step 1; start at
  question 3 of the decision framework and build the alternative first.

## The Process

### Step 1 — Run the deprecation decision (all five questions)

Do not skip to a decision. Answer in writing, with numbers where possible.

1. **Does this system still provide unique value?** (if yes, maintain it)
2. **How many users/consumers depend on it?** (quantify migration scope)
3. **Does a replacement exist?** (if no, build the replacement FIRST — don't
   deprecate without an alternative)
4. **What's the migration cost for each consumer?**
5. **What's the ongoing maintenance cost of NOT deprecating?** (security risk,
   engineer time, opportunity cost of complexity)

Question 5 is the one teams skip, and it is the one that actually decides things.
An unquantified "this is dead code" claim loses to a real number: 6 CVEs in
transitive deps, 3 engineers' worth of maintenance hours per quarter, one P1
incident last year caused by exactly this module.

Write the answers into the tracking issue. A decision with no written
rationale gets re-litigated in three months by someone who was not in the room.

### Step 2 — Choose compulsory or advisory

| | **Advisory** | **Compulsory** |
|---|---|---|
| Trigger | old system is stable; alternative exists | old system has security issues, blocks progress, or maintenance cost is unsustainable |
| Mechanism | warnings, docs, changelog, nudges, runtime deprecation notices | hard deadline + published removal date + migration tooling |
| Consumer action | migrate on their own timeline | migrate before the date or be broken |
| Support | best-effort | supported through the window |
| Blast radius | nobody's builds break | someone's builds break on the date |

**Rule: default to advisory. Compulsory deprecation requires providing migration
tooling, documentation, and support — you can't just announce a deadline.**

Advisory is the default for three reasons: most consumers never read the notice,
a soft deadline is not a real deadline so planning is worse, and the moment you
reserve the right to break builds unilaterally you spend that trust on
everything else too. Choose compulsory when the cost of not acting is higher
than the cost of the break — usually active exploitation or a fork you cannot
maintain.

### Step 3 — Apply the churn rule

> **If you own the infrastructure being deprecated, you are responsible for
> migrating your users — or providing backward-compatible updates that require
> no migration. Don't announce deprecation and leave users to figure it out.**

Read this as a design constraint, not a sentiment. If you cannot ship a
backward-compatible shim (an adapter, a codemod, a compat layer that is already
in the product), then you cannot claim to be deprecating — you are breaking.
Say so honestly in the announcement and give a real migration guide.

For the common case of a rename you control end to end: ship the rename *and* a
compat shim in the same deploy. Consumers who upgrade the library get the new
name; consumers who do nothing keep working until the next major. That is a
deprecation. Announcing a name change with no shim is not.

### Step 4 — Pick the migration pattern

| Pattern | Use when | Cost |
|---|---|---|
| **Strangler Fig** | replacing a whole system behind a stable interface | highest — 5 traffic-shift phases |
| **Adapter** | a few consumers, or consumers you cannot edit | low — one shim layer to maintain |
| **Feature Flag Migration** | risky or staged cutover, code-level not schema-level | low — flag debt (see below) |
| **Database Expand/Contract** | any schema change to a table with real data | medium — multiple deploys, days of overlap |
| **Parallel run + diff** | you must prove equivalence of results | expensive — both systems must be deterministic |

Flag-based migration must be temporary. Every flag needs an owner and an
expiration date, cleanup within two weeks of the cutover completing, no nested
flags (two flags = four states to test), and CI runs that exercise both states.
See `../shipping-and-launch/SKILL.md` for the full flag lifecycle.

### Step 5 — Announce with the deprecation-notice template

Every notice has the same five fields. Missing fields are why notices get
ignored:

```
Status:     DEPRECATED as of 2026-03-01 (advisory | compulsory)
Replacement: new.queue.v2.SendJob() — GA since 2026-02-01
Removal date: 2026-09-01 (hard date | "when <v3 of the lib> ships, no earlier than 6 months")
Reason:     one line, concrete, about the OLD system, never about the new one
Migration guide: link to a guide that runs end to end in under 15 minutes
```

Two rules that determine whether the notice is read: state the removal date as a
date, not as a condition ("no earlier than v3" without a floor date is not a
date), and put the migration link in the first three lines. Deprecation notices
buried in a changelog nobody reads are not deprecation, they are a surprise
later.

### Step 6 — Execute the migration in bounded batches

Not "flip it for everyone". Migrate in batches: a slice of traffic, a subset of
consumers, one region, one tenant tier. Between batches, verify. Fix the failures
the first batch exposed before starting the second. A migration that goes live
against all consumers simultaneously has no batch in which to learn anything.

### Step 7 — Remove, and prove the removal

Delete the old code in its own change, on its own date. Grep for stragglers by
name, not by memory. Then confirm the removal: no references, no imports, no
docs still pointing at it, no CI job still exercising it. Leaving the old path
wired behind a flag "just in case" means paying the maintenance cost in
question 5 forever.

## Database Expand/Contract (the highest-leverage pattern)

**Additive first, destructive last and alone.**

```
EXPAND   -> add the new thing alongside the old one, nullable, unused
MIGRATE  -> dual-write both, then backfill existing rows in batches
CONTRACT -> switch reads to the new one, bake, then drop the old one
                                          in a SEPARATE LATER deploy
```

The whole point is that **every intermediate state is deployable**. After the
expand, the old code alone still works. After dual-write, both are current. After
read-switch, both are still current. The only state that breaks anything is
dropping a column still being read — and that deploy is alone on purpose.

### Worked example: rename `users.name` -> `users.full_name`, in 5 deploys

| Deploy | Action | Why it is safe here |
|---|---|---|
| 1 — Expand | `ADD COLUMN full_name text NULL`, deploy | Old code reads/writes `name` only. The new column is unused and nullable — zero risk. |
| 2 — Dual-write | every insert and update writes both columns, deploy | Readers of either column see the same value. Order matters: write new then old, never old then new, or a crash between them loses data. |
| 3 — Backfill | batches: `UPDATE users SET full_name = name WHERE full_name IS NULL LIMIT 5000`, loop with a sleep, deploy | Batched so no single long transaction holds locks. Measure the rows/second and size the batch so each one stays under ~1s. |
| 4 — Switch reads | queries read `full_name`; still writing both, deploy | Full_name is complete and current, so reads are correct. Keep writing both — this is the bake window that catches stragglers you did not find by grep. |
| 5 — Contract | stop writing `name`, deploy, **bake at least one full business cycle**, then `DROP COLUMN name` in a SEPARATE LATER deploy | The drop is the only irreversible step, so it gets its own deploy with maximum distance from the change that made it safe. |

Step 5's bake is not superstition. It catches the long tail: a monthly report
job, an admin export script, a BI dashboard, a `psql` session someone left open.
Those do not show up in a repo-wide grep.

### The 5 rules

1. **Additive first, destructive last and alone.** Every deploy must be
   deployable on its own. The drop ships by itself.
2. **Every migration has a tested down path — write and run the `down` before
   merging.** An untested down path is a hope, not a rollback plan. If the
   `down` cannot restore data, back the column up first.
3. **Backfill in batches, off the hot path.** Small transactions, sleep between
   them, run during low traffic. A single `UPDATE` over ten million rows is an
   outage wearing a migration's clothes.
4. **Build large indexes without blocking writes (`CREATE INDEX CONCURRENTLY`).**
   A plain `CREATE INDEX` takes a write lock for the whole build. Note: it
   cannot run inside a transaction, and if it fails it leaves an invalid index
   you must drop before retrying.
5. **Decouple from code by feature flag when the cutover is risky.** Schema and
   code deploys are not synchronized in most orgs; the flag is what keeps the
   old code working against the new schema.

## Zombie Code

> **Code that nobody owns but everybody depends on.**

Zombie code is not unused code (that gets deleted) and not abandoned code (that
gets deleted too). It is *load-bearing* code with no owner, and it is the most
expensive thing in a codebase precisely because deleting it breaks production.

**Five checkable signs:**

1. No commits in 6+ months, but it has active consumers (imports, callers,
   HTTP routes, published versions).
2. No maintainer: no CODEOWNERS entry, no assignment, nobody answers when it
   breaks.
3. Failing tests nobody fixes — red for months, or skipped to keep the pipeline
   green.
4. Vulnerable dependencies nobody updates — a CVE with no ticket.
5. Docs reference dead systems: runbooks, architecture diagrams, onboarding
   pages pointing at things that no longer exist.

The response is binary: **it either gets investment or removal.** Not
"documentation" and not "a ticket" — a named owner with capacity, or a removal
plan with a date. The middle state is what produced the zombie in the first
place. Unowned code with active consumers is an outage with a long fuse.

When removing, expand/contract applies to code exactly as it does to schema:
the strangler fig pattern exists to get you from "everybody calls it" to "nobody
calls it" without a flag day.

## Common Rationalizations

| The excuse | The reality |
|---|---|
| "It still works, why remove it?" | Working is not the question — who pays for it is. Every deploy of it, every CVE triage, every engineer's context spent on it. Question 5 quantifies that cost; a system that works and costs 0.3 FTE is a different decision than one that works and costs 3. |
| "Someone might need it later" | Someone might. That is what version control and a spec are for. Code kept for hypothetical futures is code nobody tests, nobody updates, and nobody can delete. Hypothetical needs do not justify a security surface. |
| "The migration is too expensive" | Sometimes true — then that is the answer to question 4, and it is a reason to *plan* the migration, not to skip the decision. Refusing to price it leaves the cost accruing invisibly. Price it, then decide. |
| "We'll deprecate it after we finish the new system" | The new system is never finished; the deprecation date keeps sliding. Write the removal date now, against the current system, and let reality move it. A deprecation with no date is a comment. |
| "Users will migrate on their own" | Some will, silently, until the breaking deploy. Log who still uses the old path and report it; advisory deprecations without adoption metrics never complete. If nobody has moved in N months, the migration is too hard — fix the migration, not the deadline. |
| "Just rename the column, it's one line" | The rename is one line; the deploy is not. Every running version of your application reads that column. Rename without dual-write and every in-flight instance breaks, plus every query, report, and script that never showed up in the grep. |
| "I'll add the column and drop the old one in the same migration" | Then the deploy has no safe state: any instance running the previous build crashes on a missing column. Expand and contract exist precisely so the two steps have distance between them. |
| "We own it, but it's used by other teams" | Owning the infrastructure *is* the obligation to migrate them. Other teams' schedule is your dependency to manage, not a reason to hand them a deadline and no tooling. |
| "It's internal, we don't need a notice" | Internal consumers still have deploy cycles, release branches, and on-call rotations. Internal does not mean synchronous. |

## Red Flags

- A deprecation announcement with no removal **date** (a condition is not a date)
- The replacement does not exist, or exists but has fewer than the old system's
  capabilities (no parity check documented)
- Old and new paths both being written with **different semantics** (order of
  writes, rounding, timezone, null handling)
- The `down` migration is untested, or cannot restore data that was overwritten
- Add and drop in the **same** migration file, or the same deploy
- A backfill that runs as one unbounded `UPDATE` inside the deploy
- Non-`CONCURRENTLY` index creation on a table with live writes
- Zero instrumentation on the old path — you cannot prove adoption or non-adoption
- Removal scheduled before the migration tooling is merged and documented
- A deprecation with no named owner and no tracking issue
- Keeping the old code path "just in case" after the migration completed — the
  flag never gets cleaned up and question 5's cost never goes away
- `DROP COLUMN` in the same release as a rename, with no bake window

## Verification

### After a deprecation

- [ ] All five decision questions answered in writing, in the tracking issue,
      with numbers for consumer count and maintenance cost
- [ ] Advisory vs. compulsory chosen explicitly, with the reason stated
- [ ] Replacement exists and is GA **before** the announcement went out
- [ ] Notice has all five fields: status, replacement, removal date, reason,
      migration guide
- [ ] Migration guide was run end to end by someone who did not write it
- [ ] Backward-compatible shim or codemod exists for the common path, or the
      breaking nature is stated explicitly
- [ ] Adoption is instrumented: a counter or log for old-path usage per consumer
- [ ] Every known consumer contacted directly (not just "announced in the changelog")
- [ ] Rollback: if the removal goes wrong, how does a consumer get back?
- [ ] Old code deleted in its own change, and the repo greps clean for its name
- [ ] Docs, runbooks, and CODEOWNERS updated in the same change as the removal

### After a schema migration

- [ ] `up` and `down` both written; `down` executed against a copy of production
      data and verified, not just compiled
- [ ] Every deploy in the sequence is independently deployable (no deploy
      requires the next one to have happened)
- [ ] Expand deploy: new column/table exists, nullable, unused, old code unaffected
- [ ] Dual-write deploy: writes to both in an order that cannot lose data on
      partial failure
- [ ] Backfill: batched with a size limit, run off-peak, with rows/second measured
      and a resume path
- [ ] Backfill completeness proven with a count check
      (`WHERE full_name IS NULL` returns 0), not assumed from the script exiting 0
- [ ] Read-switch deploy: full traffic on the new column, still dual-writing
- [ ] Bake window: at least one full business cycle (weekly/monthly jobs included)
      between read-switch and drop
- [ ] `DROP` is its own commit, on its own date, with no other change bundled
- [ ] Large indexes built with `CREATE INDEX CONCURRENTLY` outside a transaction
- [ ] Query plans re-checked after the migration (`EXPLAIN ANALYZE` on the hot
      queries) — a migration can turn a fast plan into a sequential scan
- [ ] App, workers, cron jobs, and scheduled reports all confirmed on the new
      column, not just the web tier
- [ ] Rollback plan documented for the window where the drop has happened
- [ ] Data-integrity check: old and new agree for every row (or old is gone)

## See Also

- `references/expand-contract.md` — long-form expand/contract playbook, backfill
  sizing, and the DDL-by-dialect notes
- `references/deprecation-notices.md` — notice templates for APIs, config keys,
  libraries, and databases
- [shipping-and-launch](../shipping-and-launch/SKILL.md) — feature flag lifecycle,
  staged rollout, and the rollout decision thresholds that gate a migration cutover
- [supabase-postgres-best-practices](../supabase-postgres-best-practices/SKILL.md) —
  Postgres index, lock, and query-plan guidance used by expand/contract
- [security-audit](../security-audit/SKILL.md) — evidence for the "compulsory"
  trigger (a real CVE forces a hard deadline)
- [security-threat-model](../security-threat-model/SKILL.md) — for deprecated
  endpoints that still carry a trust boundary
- [tdd-workflow](../tdd-workflow/SKILL.md) — write the migration's `down` test
  first; treat data restoration as the failing test
- [refactor-safe](../refactor-safe/SKILL.md) — the change-one-thing discipline
  that every intermediate deploy depends on
- [git-commit-hygiene](../git-commit-hygiene/SKILL.md) — separate commits per
  expand/contract deploy so the history *is* the rollback path
- [verification-planning](../../verification-planning/SKILL.md) — deciding what
  evidence a risky migration must produce *before* you start writing it