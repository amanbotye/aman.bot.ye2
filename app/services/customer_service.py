from sqlalchemy.dialects.postgresql import insert
from ..models import Customer
from ..utils import utcnow
class CustomerService:
    def __init__(self,repo): self.repo=repo
    async def get_or_create(self,tid,username=None,first_name=None,last_name=None):
        c=await self.repo.get_by_telegram(tid)
        if not c:
            stmt=insert(Customer).values(telegram_id=tid,username=username,first_name=first_name,last_name=last_name).on_conflict_do_nothing(index_elements=["telegram_id"])
            await self.repo.s.execute(stmt); c=await self.repo.get_by_telegram(tid)
        if username is not None: c.username=username
        if first_name is not None: c.first_name=first_name
        if last_name is not None: c.last_name=last_name
        await self.repo.update_activity(c,utcnow()); return c
    async def set_name(self,c,full_name):
        name=" ".join(str(full_name).split())
        if len(name)<3 or len(name)>255: raise ValueError("يرجى إدخال الاسم الكامل بشكل صحيح.")
        c.full_name=name; return c
