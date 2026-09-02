# app/database.py

import os

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from sqlalchemy.orm import declarative_base


# =========================================================
# DATABASE URL
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost/dbname",
)


# Render / Supabase compatibility
if DATABASE_URL.startswith("postgres://"):

    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1,
    )

elif (
    DATABASE_URL.startswith("postgresql://")
    and "+asyncpg" not in DATABASE_URL
):

    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )


# =========================================================
# ENGINE
# =========================================================

engine = create_async_engine(
    DATABASE_URL,

    echo=False,

    future=True,

    # مهم جدًا مع Supabase PgBouncer
    connect_args={
        "statement_cache_size": 0,
    },
)


# =========================================================
# SESSION
# =========================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# BASE
# =========================================================

Base = declarative_base()


# =========================================================
# DATABASE SESSION
# =========================================================

async def get_db():

    async with AsyncSessionLocal() as session:

        try:

            yield session

        finally:

            await session.close()
