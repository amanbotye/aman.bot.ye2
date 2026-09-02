from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from ..models import PhoneNumber
class PhoneRepository:
 def __init__(self,s): self.s=s
 async def get_by_normalized(self,n): return await self.s.scalar(select(PhoneNumber).where(PhoneNumber.normalized_phone==n))
 async def list_customer(self,cid,limit=20,offset=0): return list((await self.s.scalars(select(PhoneNumber).options(selectinload(PhoneNumber.telecom_company)).where(PhoneNumber.customer_id==cid).order_by(PhoneNumber.id.desc()).limit(limit).offset(offset))).all())
 async def create(self,**kw): o=PhoneNumber(**kw); self.s.add(o); await self.s.flush(); return o
 async def search(self,term,limit=20,offset=0):
  q=select(PhoneNumber).where(or_(PhoneNumber.normalized_phone.ilike(f"%{term}%"),PhoneNumber.phone_number.ilike(f"%{term}%"))).order_by(PhoneNumber.id.desc()).limit(limit).offset(offset); return list((await self.s.scalars(q)).all())
