# app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# قراءة رابط قاعدة البيانات من متغيرات البيئة أو استخدام قيمة افتراضية محلية
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")

# إنشاء محرك الاتصال غير المتزامن (Async Engine)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# إنتاج جلسات الاتصال (Sessionmaker)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# القاعدة الأساسية التي ترث منها جميع الجداول والنماذج
Base = declarative_base()

# دالة للحصول على جلسة قاعدة البيانات (Dependency)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

