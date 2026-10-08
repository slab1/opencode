# Expand/Contract — long-form playbook

The technique in `SKILL.md` gets the decision and the 5-deploy rename. This file
covers the parts that only matter once the table is big, the writers are many,
or the dialect is not the one you assumed.

## Why the phases exist

Expand/contract is a state machine over a table that **many application versions
read concurrently**. In a rolling deploy, for hours or days, old code and new code
run at the same time against the same schema. Every rule below exists to keep all
of those states valid:

| State | Old code | New code |
|---|---|---|
| After expand | works | works |
| After dual-write | works | works |
| After backfill | works | works |
| After read-switch | works | works |
| After drop | **CRASHES** | works |

The only breaking transition is the drop. Therefore the drop ships alone.

## Phase 1 — EXPAND

```sql
ALTER TABLE users ADD COLUMN full_name text NULL;
```

- Nullable, or with the same default as the old column. `NOT NULL` without a
  default makes the deploy fail on the first row read.
- **No code reads it yet.** The whole point of this deploy is that it changes
  nothing. If you are shipping reader code in the same deploy, you skipped the
  measurement window.
- In MySQL 8 / MariaDB 10.3+ `ALGORITHM=INSTANT` avoids a table copy; check
  `ALTER TABLE ... ALGORITHM=INSTANT` is accepted before relying on it.
- In Postgres 11+ adding a nullable column with no default is metadata-only —
  instant.

## Phase 2 — MIGRATE (dual-write, then backfill)

**Order matters.** Write the new column *first*:

```python
# correct
row.full_name = compute(row.name)
row.name = compute(row.name)
```

If you write old first and the process dies between the two assignments, the new
column is stale while old is current — the read-switch then serves stale data
that no amount of backfill will fix, because backfill skips non-null rows. Either
order can produce a crash-inconsistent state; putting the new column first makes
the failure mode "new column ahead of old" which the backfill repairs.

Wrap both writes in one transaction so partial failure cannot persist:

```sql
UPDATE users SET full_name = $1, name = $1 WHERE id = $2;
```

**Then backfill**, in batches:

```sql
-- Postgres
UPDATE users SET full_name = name
WHERE full_name IS NULL AND id IN (
  SELECT id FROM users WHERE full_name IS NULL LIMIT 5000
);
```

- Loop with a `pg_sleep(0.05)`-class pause between batches so replication and
  WAL keep up.
- Size the batch by *measured duration*, not by row count. 5000 rows of a wide
  table can be 30s; 5000 narrow rows can be 20ms. Target <1s per batch.
- Record progress in a table so a crashed backfill resumes instead of restarting.
- Backfills run long. Deploy them as a **job**, not as part of the migration
  deploy, so a slow backfill cannot hold a deploy open.
- Never backfill during peak traffic; never in the same transaction as DDL.

**Dual-write must cover every writer**: web tier, workers, cron, admin scripts,
the one-off `psql` command someone runs during an incident. Find writers with
`information_schema` triggers, query logs, and the `INSERT`/`UPDATE` inventory —
not with a grep of application code alone.

## Phase 3 — Switch reads

Change every read to the new column while still writing both. This is the bake
window, and it is the highest-value measurement in the whole migration:

- Compare row counts and checksums old vs. new. Divergence means a writer you
  missed.
- Run with the old column still present so you can `SELECT old, new` from the
  same row in a live query.
- Time the bake to one full business cycle — weekly report, monthly close,
  anything cron-shaped. Then wait another cycle. Then drop.

## Phase 4 — CONTRACT

1. Deploy that stops writing the old column. Keep it readable.
2. Bake.
3. **Separate deploy:** `ALTER TABLE users DROP COLUMN name;`

In Postgres, dropping a column with a dependent view/index/constraint fails —
find the dependents first:

```sql
SELECT dependent_ns.nspname, dependent.relname, dependent.relkind
FROM pg_depend d
JOIN pg_rewrite r ON d.objid = r.oid
JOIN pg_class dependent ON r.ev_class = dependent.oid
JOIN pg_namespace dependent_ns ON dependent.relnamespace = dependent_ns.oid
JOIN pg_class referenced ON d.refobjid = referenced.oid
WHERE referenced.relname = 'users' AND dependent.relname != 'users';
```

Also check non-code consumers before dropping: BI tools, exports, ad-hoc
dashboards, third-party integrations with column-level access grants. Column
grants do not appear in your repository.

## Reversing the direction (un-migrate)

If the read-switch deploy is bad, you can revert the *code* — both columns are
still current, so old code works immediately. This is the payoff for keeping
dual-writes on during the bake. After the `DROP` deploy, reverting means
restoring data, which is why the drop is on its own date with a documented
backup.

## Testing a migration

- **Migration test harness**: apply every migration from empty, then apply each
  `down`, then apply all again. Fails loudly if `up` is not idempotent-safe or
  `down` is broken.
- **Data-preservation test**: seed known rows, run the migration, assert the data.
- **Constraint-order test**: if you add a foreign key, assert it is added
  `NOT VALID` then `VALIDATE CONSTRAINT` separately, so validation does not
  take the write lock.
- Test against a **production-sized snapshot**, not a 10-row fixture. Backfill
  batching and index builds only reveal their problems at scale.

## Dialect notes

| Operation | Postgres | MySQL 8 | SQLite |
|---|---|---|---|
| Add nullable column | instant (11+) | instant w/ `ALGORITHM=INSTANT` | instant |
| Add column + default | metadata-only if immutable default (11+) | instant from 8.0.13 in some cases | table rewrite |
| Non-blocking index | `CREATE INDEX CONCURRENTLY` (not in a txn) | `ALGORITHM=INPLACE, LOCK=NONE` | single-writer DB anyway |
| Add FK without lock | `NOT VALID` then `VALIDATE` | — | — |
| Batched update | `WHERE id IN (SELECT ... LIMIT n)` | same | needs keyset pagination |

**`CREATE INDEX CONCURRENTLY` gotchas**: it cannot run inside a transaction
block; if it fails it leaves an `INVALID` index that must be dropped before
retrying; and you must check for it, because `CREATE INDEX` returning without
error is not proof the index is valid.

## Batch sizing method

1. Run one batch of N rows and time it.
2. Scale N down until the batch is under ~1s.
3. Check locks during the batch (`pg_locks`, `SHOW PROCESSLIST`) — you want no
   long-held row locks competing with live traffic.
4. Measure rows/second, multiply by the available window, confirm the full
   backfill fits. If it does not, you need either a bigger window or a
   `partition`-style incremental approach, not a bigger batch.