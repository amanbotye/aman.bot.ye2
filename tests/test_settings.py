import pytest
from app.services.settings_service import SettingsService
class S:
    def __init__(self): self.rows={}
    async def scalar(self,q): return None
@pytest.mark.asyncio
async def test_setting_validation_ranges():
    s=SettingsService(S())
    assert await s.validate("service_price","1000")=="1000.00"
    with pytest.raises(ValueError): await s.validate("service_duration_days","0")
    with pytest.raises(ValueError): await s.validate("currency","12")
