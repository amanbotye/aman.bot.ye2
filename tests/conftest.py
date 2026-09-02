import pytest
from types import SimpleNamespace
from datetime import datetime, timezone
@pytest.fixture
def fake_customer(): return SimpleNamespace(id=1,telegram_id=123,full_name=None)
