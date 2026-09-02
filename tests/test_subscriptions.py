import pytest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from app.services.subscription_service import SubscriptionService
class Settings:
 async def get_int(self,k): return {"subscription_safe_until_day":299,"subscription_near_until_day":349,"subscription_danger_until_day":365}[k]
@pytest.mark.asyncio
@pytest.mark.parametrize("elapsed,expected",[(0,"SAFE"),(299,"SAFE"),(300,"NEAR"),(349,"NEAR"),(350,"DANGER"),(365,"DANGER"),(366,"EXPIRED")])
async def test_subscription_boundaries(elapsed,expected):
    now=datetime(2026,1,1,tzinfo=timezone.utc); sub=SimpleNamespace(start_at=now-timedelta(days=elapsed),end_at=now+timedelta(days=1)); assert await SubscriptionService(None,Settings()).classify(sub,now)==expected
@pytest.mark.asyncio
async def test_old_subscription_classification_does_not_depend_on_current_duration():
    now=datetime(2026,1,1,tzinfo=timezone.utc); sub=SimpleNamespace(start_at=now-timedelta(days=300),end_at=now+timedelta(days=65))
    assert await SubscriptionService(None,Settings()).classify(sub,now)=="NEAR"

@pytest.mark.asyncio
async def test_subscription_exact_end_is_expired():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    Settings2=Settings
    sub=SimpleNamespace(start_at=now-timedelta(days=365),end_at=now)
    assert await SubscriptionService(None,Settings2()).classify(sub,now)=="EXPIRED"
    sub.end_at=now+timedelta(seconds=1)
    assert await SubscriptionService(None,Settings2()).classify(sub,now)=="DANGER"
    sub.end_at=now-timedelta(seconds=1)
    assert await SubscriptionService(None,Settings2()).classify(sub,now)=="EXPIRED"

@pytest.mark.asyncio
async def test_subscription_end_minus_one_second_end_and_plus_one_second():
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    end=start+timedelta(days=365)
    service=SubscriptionService(None,Settings())
    sub=SimpleNamespace(start_at=start,end_at=end)
    assert await service.classify(sub,end-timedelta(seconds=1))=="DANGER"
    assert await service.classify(sub,end)=="EXPIRED"
    assert await service.classify(sub,end+timedelta(seconds=1))=="EXPIRED"
