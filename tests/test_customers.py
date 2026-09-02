import pytest
from types import SimpleNamespace
from app.services.customer_service import CustomerService
class Repo:
    def __init__(self): self.rows={}; self.s=SimpleNamespace()
    async def get_by_telegram(self,t): return self.rows.get(t)
    async def update_activity(self,o,n): o.last_activity_at=n
@pytest.mark.asyncio
async def test_name_validation_and_existing_customer():
    r=Repo(); r.rows[1]=SimpleNamespace(telegram_id=1,username=None,first_name=None,last_name=None,full_name=None); s=CustomerService(r)
    c=await s.get_or_create(1,"u","A","B"); assert c.username=="u" and c.full_name is None
    await s.set_name(c,"  علي   حسن "); assert c.full_name=="علي حسن"
    with pytest.raises(ValueError): await s.set_name(c,"x")
