from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from app.services.subscription_service import classify_subscription,remaining

def test_classification():
    now=datetime(2026,1,1,tzinfo=timezone.utc); sub=SimpleNamespace(starts_at=now,ends_at=now+timedelta(days=365),duration_days=365)
    assert classify_subscription(sub,now)=='🟢 أمن'
    assert classify_subscription(SimpleNamespace(starts_at=now,ends_at=now+timedelta(days=365),duration_days=365),now+timedelta(days=350))=='🔴 خطر'
    assert classify_subscription(sub,now+timedelta(days=366))=='⚫ منتهي'
def test_remaining():
    now=datetime(2026,1,1,tzinfo=timezone.utc);sub=SimpleNamespace(ends_at=now+timedelta(days=10));assert remaining(sub,now)==10
