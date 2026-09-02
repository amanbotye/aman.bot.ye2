import pytest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from app.models import PaymentStatus, PhoneStatus
from app.services.subscription_service import SubscriptionService
class Settings:
 async def get_int(self,k): return {"service_duration_days":365,"followup_cycle_days":90}.get(k,299)
class Session:
 def __init__(self,items): self.items=list(items); self.added=[]
 async def scalar(self,*a,**k): return self.items.pop(0)
 def add(self,o): self.added.append(o)
 async def flush(self): return None
@pytest.mark.asyncio
async def test_customer_payment_approval_subscription_followup_notification_path():
 p=SimpleNamespace(id=1,status=PaymentStatus.PENDING,phone_number_id=2,customer_id=3,amount=Decimal("1000"),currency="YER",reviewed_by=None,reviewed_at=None,rejection_reason=None)
 ph=SimpleNamespace(id=2,customer_id=3,status=PhoneStatus.UNPROTECTED,normalized_phone="+967771234567")
 c=SimpleNamespace(id=3,telegram_id=555); s=Session([p,ph,c,None,None]); sub,chat=await SubscriptionService(s,Settings()).approve_payment(1,99)
 assert p.status==PaymentStatus.APPROVED and sub.phone_number_id==2 and ph.status==PhoneStatus.PROTECTED and chat==555
 assert any(getattr(x,"kind",None)=="PAYMENT_APPROVED" for x in s.added) and any(x.__class__.__name__=="Followup" for x in s.added)
