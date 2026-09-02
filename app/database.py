from __future__ import annotations
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

if not settings.database_url:
    raise RuntimeError('DATABASE_URL is required')

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={'statement_cache_size': 0, 'prepared_statement_cache_size': 0},
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

@asynccontextmanager
async def db_session():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

async def close_db() -> None:
    await engine.dispose()
