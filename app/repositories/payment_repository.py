from sqlalchemy import select, or_, func
from ..models import PaymentRequest, PaymentStatus
class PaymentRepository:
 def __init__(self,s): self.s=s
 @property
 def session(self): return self.s
 async def get_for_update(self,pid): return await self.s.scalar(select(PaymentRequest).where(PaymentRequest.id==pid).with_for_update())
 async def create(self,**kw): o=PaymentRequest(**kw); self.s.add(o); await self.s.flush(); return o
 async def list(self,status=None,limit=20,offset=0):
  q=select(PaymentRequest).order_by(PaymentRequest.created_at.desc()).limit(limit).offset(offset)
  if status: q=q.where(PaymentRequest.status==status)
  return list((await self.s.scalars(q)).all())
 async def count(self,status=None):
  q=select(func.count()).select_from(PaymentRequest)
  if status:q=q.where(PaymentRequest.status==status)
  return int(await self.s.scalar(q) or 0)
