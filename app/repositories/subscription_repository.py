from sqlalchemy import select
from ..models import Subscription
from ..utils import utcnow
class SubscriptionRepository:
 def __init__(self,s): self.s=s
 async def active_for_phone(self,pid): return await self.s.scalar(select(Subscription).where(Subscription.phone_number_id==pid,Subscription.end_at>utcnow()).order_by(Subscription.end_at.desc()))
 async def list_customer(self,cid,limit=20,offset=0): return list((await self.s.scalars(select(Subscription).where(Subscription.customer_id==cid).order_by(Subscription.end_at.desc()).limit(limit).offset(offset))).all())
