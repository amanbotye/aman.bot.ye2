import pytest
from decimal import Decimal
from types import SimpleNamespace
from app.models import PaymentStatus,PhoneStatus
from app.services.subscription_service import SubscriptionService
class Settings:
 async def get_int(self,k): return {"service_duration_days":365,"followup_cycle_days":90}.get(k,299)
class Session:
 def __init__(self,payment,phone,customer,current=None,fu=None): self.items=[payment,phone,customer,current,fu]; self.added=[]
 async def scalar(self,*a,**k): return self.items.pop(0)
 def add(self,o): self.added.append(o)
 async def flush(self): return None
@pytest.mark.asyncio
async def test_duplicate_approval_is_rejected():
    p=SimpleNamespace(id=1,status=PaymentStatus.APPROVED); s=Session(p,None,None); svc=SubscriptionService(s,Settings())
    with pytest.raises(ValueError,match="تم التعامل"): await svc.approve_payment(1,9)
@pytest.mark.asyncio
async def test_approval_is_atomic_business_sequence_and_uses_telegram_id():
    p=SimpleNamespace(id=1,status=PaymentStatus.PENDING,phone_number_id=2,customer_id=3,amount=Decimal("1000.00"),currency="YER",reviewed_by=None,reviewed_at=None,rejection_reason=None)
    ph=SimpleNamespace(id=2,customer_id=3,status=PhoneStatus.UNPROTECTED,normalized_phone="+967771234567")
    c=SimpleNamespace(id=3,telegram_id=555); s=Session(p,ph,c,None,None); sub,chat=await SubscriptionService(s,Settings()).approve_payment(1,99)
    assert p.status==PaymentStatus.APPROVED and ph.status==PhoneStatus.PROTECTED and chat==555 and sub.end_at>sub.start_at
    assert any(getattr(x,"kind",None)=="PAYMENT_APPROVED" for x in s.added)

@pytest.mark.asyncio
async def test_approval_locks_payment_row_before_status_check():
    class LockAwareSession(Session):
        def __init__(self, payment):
            super().__init__(payment,None,None,None,None)
            self.locked=False
        async def scalar(self, statement, *args, **kwargs):
            if not self.items[0] is None:
                # The SQLAlchemy statement passed to the first scalar must
                # contain a FOR UPDATE clause for the payment row.
                sql=str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
                self.locked = "for update" in sql
            return await super().scalar(statement,*args,**kwargs)
    p=SimpleNamespace(id=1,status=PaymentStatus.APPROVED)
    s=LockAwareSession(p)
    svc=SubscriptionService(s,Settings())
    with pytest.raises(ValueError,match="تم التعامل"):
        await svc.approve_payment(1,9)
    assert s.locked
