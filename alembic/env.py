from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.models import Base

import asyncio


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

# حماية من توقف Alembic إذا كان alembic.ini لا يحتوي
# على إعدادات logging الكاملة.
if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except (KeyError, ValueError):
        pass


target_metadata = Base.metadata


def do_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async():
    connectable = async_engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_migrations)

    await connectable.dispose()


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    asyncio.run(run_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
