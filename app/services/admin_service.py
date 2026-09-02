from ..models import AdminRole, AdminUser
from ..admin.permissions import role_allows, PERMISSIONS
from sqlalchemy import select
class AdminService:
    def __init__(self,s): self.s=s
    async def get_admin(self,tid): return await self.s.scalar(select(AdminUser).where(AdminUser.telegram_id==tid,AdminUser.active.is_(True)))
    async def can(self,tid,permission):
        a=await self.get_admin(tid); return bool(a and role_allows(a.role,permission))
    async def bootstrap(self,ids):
        for tid in ids:
            row=await self.s.scalar(select(AdminUser).where(AdminUser.telegram_id==tid).with_for_update())
            if row:
                row.active=True
            else:
                self.s.add(AdminUser(telegram_id=tid,role=AdminRole.SUPER_ADMIN,active=True))
        await self.s.flush()
    async def permissions(self,tid):
        a=await self.get_admin(tid); return PERMISSIONS.get(a.role,set()) if a else set()
