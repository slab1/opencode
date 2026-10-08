# Deprecation notice templates

Fill in every field. A missing field is why a notice gets ignored.

## The five fields, and why each exists

| Field | Why it is mandatory |
|---|---|
| **Status** | Distinguishes "you may migrate" from "you will be broken". Consumers behave completely differently. |
| **Replacement** | Without a concrete replacement the notice is just bad news. |
| **Removal date** | An absolute date is what makes planning possible. A condition ("when v3 ships") with no floor is not a date. |
| **Reason** | The reason is about the *old* system, not the new one. "Migrating to the new thing" is not a reason. |
| **Migration guide** | Must be runnable end to end in under 15 minutes by someone who has never seen the system. |

---

## API / endpoint

```
DEPRECATED: POST /v1/jobs

Status:        DEPRECATED as of 2026-03-01 — advisory. Still supported, still
               covered by the SLA. No behaviour change before the removal date.
Replacement:   POST /v2/jobs (GA since 2026-02-01). v1 is frozen: no new
               fields will be added.
Removal date:  2026-09-01 (earliest).
Reason:        v1 cannot express job priority or cancellation, which is why 40%
               of current traffic uses v2. Maintaining both costs one engineer a
               quarter, and the split doubles the auth surface we must audit.
Migration:     https://docs.example.com/jobs/v1-to-v2
               For 95% of callers this is a single field rename:
                 jobs.create(payload)   -> v2.jobs.create(payload)
               Run `npx codemod jobs/v1-to-v2` for the automatic case.
Owner:         @team-platform    Issue: PLAT-1234
Adoption:      track v1 usage at https://metrics.internal/jobs-api-version
```

## Config key / environment variable / flag

```
DEPRECATED: DATABASE_LEGACY_HOST

Status:        DEPRECATED as of 2026-04-15 — advisory.
Replacement:   DATABASE_HOST (single host; the legacy pair splits port and host
               and is the reason half our connection bugs are hard to read).
Removal date:  2026-10-01 (earliest). Config using it logs a WARNING at startup
               and a WARN line per connection attempt.
Reason:        two keys describe one database, so a misconfiguration is silent.
Migration:     set DATABASE_HOST, delete DATABASE_LEGACY_HOST. Behaviour is
               identical unless you were relying on the legacy default, which
               was <prod-host> — check if you relied on the default.
Owner:         @team-platform
```

Always state the **old default's literal value**. Half the migrations that break
are people who relied on a default they never wrote down.

## Library / published API

```
Deprecated: Client.getUserProfile(id) -> Client.getUser(id)

Status:        DEPRECATED as of 3.2.0 — advisory.
Replacement:   Client.getUser(id) — same signature, same return type. The old
               name is a thin alias over the new one and will stay working
               through the entire 3.x line.
Removal date:  first 4.0 release, no earlier than 2026-09-01.
Reason:        the "Profile" name implies a second round-trip that does not
               exist; the extra call encouraged an anti-pattern.
Migration:     rename the call. No behaviour change; a codemod is not required
               because the alias is in the shipped code.
Owner:         @team-sdk
```

A rename you ship with a shipped alias is advisory by construction. If there is
no alias, be honest: say "breaking change", name the version, and give a codemod.

## Database column / table

```
DEPRECATED: users.name  ->  users.full_name

Status:        DEPRECATED as of 2026-05-01 — advisory.
Replacement:   users.full_name (populated and dual-written since 2026-05-01).
Removal date:  DROP lands no earlier than 2026-11-01, in a separate release, and
               only after a full monthly reporting cycle on full_name.
Reason:        `name` is ambiguous (person name? display name? username?) and
               three integrations have silently picked different meanings for it.
Migration:     no action required to keep working. To move your queries now,
               read full_name. Queries reading `name` will break when the column
               is dropped, not before.
Owner:         @team-data    Issue: DATA-88
```

The line "will break when the column is dropped, not before" is the sentence
that makes the date actionable instead of alarming.

## Dependency / internal service

```
DEPRECATED: internal-auth-service (the sidecar)

Status:        DEPRECATED as of 2026-06-01 — COMPULSORY.
Reason:        CVE-2026-1187 (session fixation) has no vendor fix on the 2.x
               line. This is the compulsory trigger: we will not ship a known
               exploitable session-fixation path in a system that handles
               sessions.
Replacement:   platform-sso 4.x, already deployed to all environments.
Removal date:  2026-07-01. The sidecar will refuse to start on that date.
Migration:     run `./scripts/migrate-sso.sh --env <env> --dry-run` first.
               It prints every config key you still have and validates the
               resulting session cookie against the new issuer. Rollback for
               14 days: re-enable the sidecar with the saved config dump.
Owner:         @team-security, reviewed by security-audit sign-off
Support:       dedicated migration channel, daily office hours through 07-01
```

Compulsory notices must carry: the CVE or hard blocker (not "we want to"),
migration tooling that runs, a dry-run mode, a named support channel, and a
rollback window measured in days rather than hours.

---

## Announcement channel order

1. **Direct contact** — every known consumer owner, individually, at least 8 weeks
   before a compulsory removal. An issue in a tracker is not contact.
2. **Runtime deprecation notice** — a warning at startup / a `Deprecation` header
   / a `console.warn` naming the replacement. This is the only channel that
   reliably reaches people who never read the changelog.
3. **Changelog / release notes** — full text.
4. **Migration guide + tooling** — linked from all of the above, not only the
   changelog.
5. **Dashboard** — usage by consumer, so "who has not migrated" is a query, not
   a guess.

## Removing the notice

When the thing is gone, delete the notice from the changelog and update any doc
that still points at it. A notice that outlives the thing it deprecates becomes
the doc someone trusts and follows into a 404.