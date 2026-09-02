from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def create_session_factory(database_url: str, pool_size: int = 5, max_overflow: int = 5):
    kwargs = {"pool_pre_ping": True, "future": True}
    if database_url.startswith("postgresql+asyncpg://"):
        kwargs.update(pool_size=pool_size, max_overflow=max_overflow, pool_recycle=1800)
    else:
        kwargs["poolclass"] = NullPool
    engine = create_async_engine(database_url, **kwargs)
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession, autoflush=False)
