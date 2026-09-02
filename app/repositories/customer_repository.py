from sqlalchemy import select, func, or_
from ..models import Customer
class CustomerRepository:
 def __init__(self, session): self.s=session
 async def get_by_telegram(self,tid): return await self.s.scalar(select(Customer).where(Customer.telegram_id==tid))
 async def create(self,**kw): obj=Customer(**kw); self.s.add(obj); await self.s.flush(); return obj
 async def update_activity(self,obj,now): obj.last_activity_at=now
 async def search(self,term,limit=20,offset=0):
  term=str(term).strip().lstrip("@"); q=select(Customer).where(or_(Customer.username.ilike(f"%{term}%"),Customer.full_name.ilike(f"%{term}%"),func.cast(Customer.telegram_id, __import__('sqlalchemy').String).ilike(f"%{term}%"))).order_by(Customer.id.desc()).limit(limit).offset(offset)
  return list((await self.s.scalars(q)).all())
