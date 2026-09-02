from sqlalchemy.dialects.postgresql import insert
from ..models import PhoneNumber, PhoneStatus
from ..utils import normalize_yemen_phone
class PhoneService:
    def __init__(self,repo): self.repo=repo
    def normalize(self,value): return normalize_yemen_phone(value)
    async def register(self,customer_id,company_id,value):
        n=normalize_yemen_phone(value)
        if await self.repo.get_by_normalized(n): raise ValueError("هذا الرقم مسجل مسبقًا.")
        stmt=insert(PhoneNumber).values(customer_id=customer_id,telecom_company_id=company_id,phone_number=n,normalized_phone=n,status=PhoneStatus.UNPROTECTED).on_conflict_do_nothing(index_elements=["normalized_phone"]).returning(PhoneNumber.id)
        result=await self.repo.s.execute(stmt); pid=result.scalar_one_or_none()
        if pid is None: raise ValueError("هذا الرقم مسجل مسبقًا.")
        return await self.repo.s.get(PhoneNumber,pid)
    async def set_status(self,phone,status): phone.status=status; return phone
