import os
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app import models  # noqa: F401

config=context.config
target_metadata=Base.metadata

def normalize_url(url):
    if url.startswith("postgres://"): return "postgresql+asyncpg://"+url[len("postgres://"):]
    if url.startswith("postgresql://"): return "postgresql+asyncpg://"+url[len("postgresql://"):]
    return url

def do_run_migrations(connection):
    context.configure(connection=connection,target_metadata=target_metadata,compare_type=True,compare_server_default=True,render_as_batch=False)
    with context.begin_transaction(): context.run_migrations()

async def run_async_migrations():
    url=normalize_url(os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url"))
    if not url: raise RuntimeError("DATABASE_URL is required for Alembic migrations")
    connectable=create_async_engine(url,poolclass=pool.NullPool)
    async with connectable.connect() as connection: await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_offline():
    url=os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url: raise RuntimeError("DATABASE_URL is required for Alembic migrations")
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True,compare_type=True,compare_server_default=True)
    with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_async_migrations())
