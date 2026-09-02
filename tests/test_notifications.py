import pytest
from types import SimpleNamespace
from app.services.notification_service import NotificationService

class Repo:
    async def create(self, **kw):
        return SimpleNamespace(**kw, attempts=0, sent_at=None, last_error=None, next_attempt_at=None)

@pytest.mark.asyncio
async def test_notification_enqueue_uses_database_dedupe_repository_contract():
    row=await NotificationService(Repo()).enqueue(9,"TEST","hello","u1")
    assert row.customer_id==9 and row.dedupe_key=="u1"
