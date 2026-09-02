# AMAN — Final Fix & Production Release Audit

**Audit date:** 2026-09-02
**Release:** Final repaired source package

## Verdict

### 🟠 CONDITIONALLY READY

All previously identified code-level Critical/High findings targeted by the independent audit were addressed in the source package. The remaining condition is environmental verification: this execution environment has no PostgreSQL server and does not have the Telegram runtime dependencies installed, so real PostgreSQL transactions/concurrency and real Telegram startup/delivery could not be executed here.

No claim of Production Ready is made without those final environment-level tests.

## Previous findings and disposition

| Finding | Result |
|---|---|
| DB-001 duplicate/broken `final_schema.sql` | FIXED — regenerated from Alembic offline output; duplicate table definitions removed |
| SCH-001 subscription warning `.days` boundary | FIXED — inclusive timedelta warning windows with dedupe |
| NOTIF-001 notification race | FIXED — `FOR UPDATE SKIP LOCKED` atomic claim + processing lease |
| SET-001 notification max attempts split source | FIXED — DB `system_settings` is authoritative and read each scheduler run |
| TX-001 Telegram I/O inside critical transaction | FIXED — dispatch uses deferred replies; payment uses DB outbox records; scheduler sends after DB transaction closes |
| SB-001 Sandbox/Production state consistency | FIXED — mode/FSM pointer remains in Production and business data remains isolated in Sandbox; recovery behavior documented |
| TEST-001 fake-only concurrency coverage | FIXED in test design — real PostgreSQL integration/concurrency suite added; execution is skipped only because no PostgreSQL server is available |
| SB-002 missing `AuditService` import | FIXED |
| LOG-001 support message content in audit | FIXED — audit records metadata/message ID, content remains in `support_messages` |
| PERF-001 reviewed-at reporting index | FIXED — `ix_payment_reviewed_at` added |

## Python / runtime

- `python -m compileall .`: **PASS**
- `pytest -q`: **45 passed, 7 skipped**
- `python -c "import main"`: **NOT TESTED — ENVIRONMENT LIMITATION**. The installed environment lacks `python-telegram-bot` (and other runtime packages from `requirements.txt`); package installation was attempted but external package access is unavailable.

## Tests

The suite now contains real PostgreSQL tests in `tests/test_real_postgres.py` for:

- FSM persistence after restart simulation
- same-user FSM concurrency
- phone uniqueness race
- concurrent payment approval
- payment rollback after database constraint failure
- notification atomic claiming
- notification lease crash recovery

These tests require a dedicated PostgreSQL database through `TEST_DATABASE_URL`. They do not substitute SQLite or fake sessions for transaction/concurrency verification.

**REAL POSTGRESQL TESTS: NOT EXECUTED — ENVIRONMENT LIMITATION**

**REAL TELEGRAM TESTS: NOT EXECUTED — ENVIRONMENT LIMITATION**

## Database / migrations

- PostgreSQL architecture: SQLAlchemy Async + `asyncpg` + PostgreSQL.
- No SQLite, Redis, or MongoDB persistence path was found.
- FSM authoritative storage: `fsm_states` in PostgreSQL.
- Payment approval uses `FOR UPDATE` locking and one business transaction.
- Notification claiming uses PostgreSQL `FOR UPDATE SKIP LOCKED`.
- `alembic upgrade head --sql`: **PASS**
- `alembic downgrade 0002_notification_leases:0001_initial --sql`: **PASS**
- `alembic upgrade head` against a real PostgreSQL server: **NOT TESTED — ENVIRONMENT LIMITATION**

`migrations/final_schema.sql` was regenerated from the current Alembic migration chain. Static verification found exactly one `CREATE TABLE` definition for every model table and all current model columns represented either in `CREATE TABLE` or subsequent migration statements.

## FSM

PostgreSQL is the authoritative source. Each update loads state from PostgreSQL and saves it back. A transaction-scoped PostgreSQL advisory lock serializes updates for the same Telegram ID, with a row lock on the FSM record.

`context.user_data` is a working cache only; the next update clears it and reloads authoritative state from PostgreSQL.

Real concurrent PostgreSQL FSM verification: **NOT EXECUTED — ENVIRONMENT LIMITATION**.

## Payments

Approval sequence remains:

`lock payment → approve → subscription → phone → followup → notification record → audit → commit`

Duplicate approval is rejected by the locked payment status. Notifications are recorded in the transaction but Telegram delivery is deferred to the notification worker.

Real concurrent approval and rollback tests: **NOT EXECUTED — ENVIRONMENT LIMITATION**.

## Subscriptions / followups

Subscription classification preserves:

- 0–299 SAFE
- 300–349 NEAR
- 350–365 DANGER
- `now >= end_at` EXPIRED

Followup classification preserves:

- 0–79 SAFE
- 80–84 NEAR
- 85–90 DANGER
- after cycle end EXPIRED

Scheduler warning windows use inclusive `timedelta` comparisons so a job delayed by one second does not lose the 30/7/3/1-day warning. Dedupe keys prevent repeated creation of the same warning.

## Notifications

Notification lifecycle:

`pending → atomic claim → processing lease → Telegram delivery → sent`

Claims use `FOR UPDATE SKIP LOCKED`. A crashed worker leaves a lease that can be reclaimed after expiry. Telegram delivery is intentionally **at-least-once**; exactly-once cannot be guaranteed by Telegram API because there is no application idempotency key for this send operation.

`notification_max_attempts` is read from `system_settings` on each scheduler run, so an Admin change takes effect without restart.

## Scheduler

APScheduler jobs:

- subscription warnings
- followup cycles
- notification queue every minute

Jobs are bounded/paginated and use dedupe/lease/database guarantees rather than assuming one process is the only worker.

Multi-process Render behavior still requires the real PostgreSQL environment test before operational sign-off.

## Sandbox

Sandbox business data uses a separate PostgreSQL connection. Production customer/payment/subscription/support records are not routed to the Sandbox database.

Mode/FSM state remains a small Production pointer so an administrator can recover mode after restart. A crash between separate database commits cannot turn Sandbox data into Production data; the documented outcome can be an orphaned Sandbox session that remains isolated and recoverable.

## Security / RBAC

- Roles: `super_admin`, `finance`, `support`, `operations`, `viewer`.
- Authorization is checked server-side.
- `A/a` return to Admin Mode is guarded by the Production Admin record.
- No real secrets were found in source files.
- `.env` is ignored; `.env.example` contains placeholders only.
- No BOT token/password/database credential is logged intentionally.
- Support audit records metadata rather than full support message text.

## Performance

- Aggregates are performed in SQL for dashboard counts/revenue.
- Dashboard does not load all historical records into Python for its main metrics.
- Customer phone listing uses eager loading for telecom company data.
- Scheduler work is paginated/bounded.
- `payment_requests.reviewed_at` now has a reporting index.

A production load test with real Supabase data was not executed.

## Final package hygiene

Before packaging, generated caches, `.pyc`, `.pytest_cache`, `.git`, `.env`, temporary files, and old ZIP files are removed from the release directory.

## SHA-256 note

The final archive SHA-256 is supplied in the release response. Embedding the exact SHA-256 of an archive inside that same archive is self-referential: changing the audit file to add the hash changes the archive hash. Therefore the exact final archive hash is intentionally reported externally rather than making a mathematically invalid self-reference inside the ZIP.

## Final assessment

**FINAL VERDICT: 🟠 CONDITIONALLY READY**

There are no known remaining Critical/High code findings from the requested audit list after the fixes. Release approval is conditional on running the real PostgreSQL/Supabase migration and concurrency suite and a real Telegram startup/send smoke test in the target deployment environment.
