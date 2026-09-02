import pytest
from types import SimpleNamespace
from app.utils import normalize_yemen_phone
from app.services.phone_service import PhoneService
@pytest.mark.parametrize("v",["771234567","0771234567","+967771234567","967771234567","00 967 771234567","+967 771 234 567"])
def test_normalization(v): assert normalize_yemen_phone(v)=="+967771234567"
@pytest.mark.parametrize("v",["12345","77123456","+9677712345689"])
def test_invalid(v):
    with pytest.raises(ValueError): normalize_yemen_phone(v)
class Repo:
    def __init__(self): self.s=SimpleNamespace(); self.rows={}
    async def get_by_normalized(self,n): return self.rows.get(n)
@pytest.mark.asyncio
async def test_duplicate_phone_rejected_before_insert():
    r=Repo(); r.rows["+967771234567"]=object();
    with pytest.raises(ValueError): await PhoneService(r).register(1,1,"771234567")
