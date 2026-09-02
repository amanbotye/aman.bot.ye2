from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# استخدام الرابط ومعالجته ليتوافق مع asyncpg
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# إنشاء المحرك مع إضافة خيارات تعطيل الـ prepared statements لتوافق Supabase Pooler
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
)

# إنشاء جلسة الاتصال غير المتزامنة
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()

# دالة للحصول على جلسة قاعدة البيانات
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
