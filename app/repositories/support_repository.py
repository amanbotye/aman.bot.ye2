from sqlalchemy import select, func
from ..models import SupportTicket, SupportMessage
class SupportRepository:
 def __init__(self,s): self.s=s
 async def create_ticket(self,**kw): o=SupportTicket(**kw); self.s.add(o); await self.s.flush(); return o
 async def add_message(self,**kw): o=SupportMessage(**kw); self.s.add(o); await self.s.flush(); return o
 async def get(self,tid): return await self.s.get(SupportTicket,tid)
 async def list_customer(self,cid,limit=20,offset=0): return list((await self.s.scalars(select(SupportTicket).where(SupportTicket.customer_id==cid).order_by(SupportTicket.id.desc()).limit(limit).offset(offset))).all())
 async def list(self,limit=20,offset=0): return list((await self.s.scalars(select(SupportTicket).order_by(SupportTicket.updated_at.desc()).limit(limit).offset(offset))).all())
 async def messages(self,tid,limit=50): return list((await self.s.scalars(select(SupportMessage).where(SupportMessage.ticket_id==tid).order_by(SupportMessage.id).limit(limit))).all())
