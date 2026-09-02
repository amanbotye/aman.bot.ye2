import pytest
from datetime import datetime,timedelta,timezone
from app.services.followup_service import FollowupService
@pytest.mark.asyncio
@pytest.mark.parametrize("days,expected",[(79,"SAFE"),(80,"NEAR"),(84,"NEAR"),(85,"DANGER"),(90,"DANGER"),(91,"EXPIRED")])
async def test_followup_boundaries(days,expected):
    now=datetime(2026,1,1,tzinfo=timezone.utc); start=now-timedelta(days=days); end=now+timedelta(days=1) if days<91 else now-timedelta(days=1)
    assert await FollowupService().classify(start,end,now)==expected

@pytest.mark.asyncio
async def test_followup_thresholds_are_loaded_from_settings():
    class Settings:
        async def get_int(self,k):
            return {"followup_safe_until_day":10,"followup_near_until_day":12,"followup_danger_until_day":15,"followup_cycle_days":30}[k]
    service=FollowupService(Settings())
    now=datetime(2026,1,16,tzinfo=timezone.utc)
    assert await service.classify(now-timedelta(days=10),now+timedelta(days=1),now)=="SAFE"
    assert await service.classify(now-timedelta(days=11),now+timedelta(days=1),now)=="NEAR"
    assert await service.classify(now-timedelta(days=15),now,now)=="DANGER"
    assert await service.classify(now-timedelta(days=16),now,now)=="EXPIRED"

@pytest.mark.asyncio
async def test_followup_91_days_is_expired_even_when_cycle_end_is_future():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    service=FollowupService()
    assert await service.classify(now-timedelta(days=91), now+timedelta(days=1), now)=="EXPIRED"
