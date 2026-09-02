# AMAN migrations

The SQL snapshot is generated from `app.models.Base.metadata` and the Alembic migration imports the same metadata. Models are the schema source of truth.

Run:
`alembic upgrade head`
