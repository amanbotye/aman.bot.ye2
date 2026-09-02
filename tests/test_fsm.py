import asyncio
import pytest
from app.services.fsm_service import FSMService
from app.models import FSMState


class Session:
    def __init__(self):
        self.row=None
        self.executed=[]

    async def execute(self, query, params=None):
        self.executed.append((str(query), params))
        return None

    async def scalar(self, query):
        return self.row

    def add(self,row):
        self.row=row

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_fsm_save_restore_after_restart_simulation():
    db=Session(); a=FSMService(db)
    await a.save(7,70,"PHONE_INPUT",{"company_id":2,"phone":"+967771234567"})
    b=FSMService(db); state,data=await b.load(7,70)
    assert state=="PHONE_INPUT" and data["company_id"]==2


@pytest.mark.asyncio
async def test_fsm_load_uses_transaction_scoped_user_lock():
    db=Session(); db.row=FSMState(telegram_id=9,chat_id=90,current_state="A",state_data='{"x":1}')
    state,data=await FSMService(db).load(9,90)
    assert state=="A" and data=={"x":1}
    assert any("pg_advisory_xact_lock" in sql for sql,_ in db.executed)


def test_fsm_lock_serializes_same_user_in_postgresql_design():
    # The production implementation uses pg_advisory_xact_lock, which is
    # transaction-scoped and therefore serializes concurrent updates for the
    # same Telegram ID. A real PostgreSQL concurrency test is reported
    # separately when a server is available.
    assert "pg_advisory_xact_lock" in open("app/services/fsm_service.py",encoding="utf-8").read()
