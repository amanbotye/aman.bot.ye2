# AMAN — أمان

Production-oriented Telegram bot for managing Yemeni phone-number protection subscriptions.

## Stack
- Python 3.11
- python-telegram-bot 21.10 (polling)
- SQLAlchemy async + asyncpg
- PostgreSQL / Supabase
- APScheduler 3.10.4
- PostgreSQL-backed user sessions (FSM)

## Run locally
1. Copy `.env.example` to `.env` and set `BOT_TOKEN`, `DATABASE_URL`, and `ADMIN_IDS`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run migrations: `alembic upgrade head`.
4. Start: `python main.py`.

## Render
Use a Web Service with start command `./start.sh`. Set environment variables in Render, never in Git.
The small health endpoint listens on `WEB_PORT` and returns `AMAN OK`.
Do not run a second service/worker with the same Telegram bot token: polling must have exactly one active instance to avoid Telegram 409 conflicts.

## Database safety
The project contains no DROP DATABASE, DROP TABLE, or TRUNCATE operations. The included first migration creates only missing tables. Before adding a global unique phone constraint to an existing production database, inspect and reconcile duplicates manually with a reviewed migration.

## Core flows
Customer registration, Yemeni phone normalization/validation, ownership protection, payment methods, transaction reference, optional/required proof, pending-payment deduplication, admin approval/rejection, atomic subscription activation, followup creation, customer notifications, support tickets, FAQ, settings, audit logs and dashboard are implemented in modular services.

## Notes
- Amounts use Decimal/Numeric, never float.
- UTC is used internally.
- Notification delivery is post-commit and bounded by attempts.
- Internal followup/confiscation fields are not exposed in customer UI.
