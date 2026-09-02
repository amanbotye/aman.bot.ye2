import pytest
from types import SimpleNamespace
from app.services.support_service import SupportService
from app.models import TicketStatus
class Repo:
    def __init__(self): self.t=SimpleNamespace(id=1,status=TicketStatus.OPEN); self.msg=[]
    async def create_ticket(self,**kw): return self.t
    async def get(self,tid): return self.t if tid==1 else None
    async def add_message(self,**kw): self.msg.append(kw); return SimpleNamespace(**kw)
@pytest.mark.asyncio
async def test_closed_ticket_restriction_and_reopen():
    r=Repo(); s=SupportService(r); r.t.status=TicketStatus.CLOSED
    with pytest.raises(ValueError): await s.message(1,1,"hello")
    await s.reopen(1); await s.message(1,1,"hello"); assert r.msg
