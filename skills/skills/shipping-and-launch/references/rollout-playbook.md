# Staged rollout runbook

A runbook for the window between "deployed with the flag OFF" and "flag removed".
Timestamps are illustrative; the *order* is the runbook.

## T-1 day — before the deploy

1. Capture the **baseline**: error rate, P95/P99 latency, the business metric, and
   the client-error breakdown, for the same population the rollout will serve.
   Write the numbers down. Without these, "within 10%" is unfalsifiable.
2. Confirm the dashboards for those metrics exist, load, and are filtered to the
   right traffic class.
3. Send a test alert through the on-call path. An alert that has never fired is an
   alert that does not work.
4. Write the rollback plan (template in `SKILL.md`) and give it to on-call.
5. Confirm the flag is in the system with an owner and an expiration date, and
   that a flag-off is genuinely under a minute for the person who will do it.

## T0 — deploy with the flag OFF

6. Deploy. The code is live and inert.
7. **Watch for 15-30 minutes.** The flag being OFF isolates this deploy from the
   change, so anything that breaks here is a bug in the plumbing: a bad migration,
   a missing config key, a startup failure on a code path the flag does not
   cover. Fix it now — do not advance to stage 3 with a red baseline.
8. Confirm the flag evaluates OFF for a real user request (not just in the flag
   UI). Check the metrics did not move at all.

## T0+1h — stage 3: team

9. Enable for the team / internal allowlist.
10. Watch 2 hours. Expected: new error types at zero, business metrics identical.
11. Team members use it for real work — not just clicking through once. Internal
    users are the cheapest bug-finding cohort you have; a 15-minute smoke test
    wastes them.

## T0+1d — stage 4: canary at 5%

12. Enable for 5% of users.
13. **Run the 24-48 hour window.** Do not advance early. The window must include:
    - the daily traffic peak and the daily trough
    - any scheduled job (reports, emails, reconciliation) that touches this path
    - at least one full day boundary, because date/timezone-dependent bugs live
    there
14. At the end of each window, evaluate against the thresholds table. Record the
    comparison in the issue. "Looks fine" is not a record; a number and a
    timestamp is.
15. On yellow: **hold**. Do not advance and do not roll back yet. Read the
    comparison at a finer time granularity — a 5% regression visible at 24h is
    usually one bad hour hiding inside it. Then decide.
16. On red: roll back now, diagnose offline. Do not debug in production while
    users are on the change.

## T0+2d — 25% → 50%

17. Advance one stage at a time, one observation window at a time.
18. Between stages, confirm nothing changed *except* the flag percentage: no
    config edit, no deploy, no schema change. Two variables is zero variables.

## T0+3-4d — 100%, then a week of monitoring

19. At 100%, keep the flag for a full week. This is where the long tail shows up:
    the monthly report, the enterprise customer's nightly job, the account that
    uses this once a quarter.
20. Only after that week: cleanup.

## Cleanup

21. Remove the flag **and** the dead branch it was guarding. A flag permanently on
    is a second code path nobody tests. Deadline: 2 weeks from 100% or from the
    revert, whichever came first.
22. Remove the temporary instrumentation you added, or promote it to real
    permanent alerting.
23. Post the outcome in the issue: stages completed, the numbers, whether it was
    green/yellow anywhere, and what you learned. This is the only artifact that
    makes the *next* launch faster.

## Rollback runbook (the part to rehearse)

```
Trigger fires
  |
  +-- 0:00  Flag OFF                          <1 min
  |           Verify the change is actually inert (check a real user response)
  |
  +-- 0:05  Error rate trending back to baseline over 5 min?  --> yes: STOP HERE
  |                                                                    monitor
  +-- 0:10  Still elevated --> redeploy previous release       <5 min
  |           Note: deploys and flag changes are separate actions. Record which
  |           one you did, and why.
  |
  +-- 0:15  Still elevated, or data integrity suspect --> database rollback
  |           See the Database Considerations section. If the migration was
  |           destructive, this is a RESTORE, not a reverse migration. Know the
  |           restore point *before* you need it.
  |
  +-- after:  do not re-push the same commit. Fix, then a new rollout from 5%.
```

**Rehearsal matters more than the plan.** Roll back a flag in staging at least
once. If the person on call has never done it, their first attempt takes three
times as long, and that is measured in the incident.

## Post-rollback

- Revert commit in git (`revert`, never `reset` on a shared branch — see
  `git-commit-hygiene`) so history records the decision.
- If data was written by the bad version: state precisely what shape it is in, who
  is affected, and what the repair is. "Probably fine" is not a data answer.
- Blameless review, scheduled within a week while memory is fresh.
- Feed the finding back into the flag's scope: why did the threshold catch it (or
  fail to)? If no threshold would have caught it, the monitoring gap is the
  real bug.