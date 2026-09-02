from sqlalchemy import select
from ..models import AdminUser, SystemSetting
from .settings_service import SettingsService

class SandboxService:
    MARKER="SANDBOX"
    def __init__(self,session_factory): self.session_factory=session_factory
    @staticmethod
    def enabled(session_factory): return session_factory is not None
    async def prepare(self,production_session):
        if not self.session_factory: raise PermissionError("SANDBOX_DATABASE_URL غير مهيأ.")
        admins=list((await production_session.scalars(select(AdminUser).where(AdminUser.active.is_(True)))).all())
        async with self.session_factory() as s:
            await SettingsService(s).seed_defaults()
            for src in admins:
                row=await s.scalar(select(AdminUser).where(AdminUser.telegram_id==src.telegram_id))
                if row: row.role=src.role; row.active=True
                else: s.add(AdminUser(telegram_id=src.telegram_id,role=src.role,active=True))
            await s.commit()
