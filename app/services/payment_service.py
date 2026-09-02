from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from ..models import PaymentStatus, PhoneNumber, PaymentMethod, Customer, PaymentRequest
from ..utils import money
class PaymentService:
    def __init__(self,repo,settings): self.repo=repo; self.settings=settings
    async def create_request(self,customer_id,phone_id,method_id,reference,proof=None):
        phone=await self.repo.session.get(PhoneNumber,phone_id); method=await self.repo.session.get(PaymentMethod,method_id); customer=await self.repo.session.get(Customer,customer_id)
        if not phone or phone.customer_id!=customer_id: raise ValueError("الرقم غير متاح لهذا الحساب.")
        if not method or not method.active: raise ValueError("طريقة الدفع غير متاحة.")
        if not customer: raise ValueError("العميل غير موجود.")
        reference=" ".join(str(reference).split())
        if not 2 <= len(reference) <= 255: raise ValueError("مرجع العملية غير صالح.")
        amount=money(await self.settings.get("service_price")); currency=await self.settings.get("currency")
        stmt=insert(PaymentRequest).values(customer_id=customer_id,phone_number_id=phone_id,payment_method_id=method_id,amount=amount,currency=currency,transaction_reference=reference,proof_file_id=proof,status=PaymentStatus.PENDING).on_conflict_do_nothing(index_elements=["phone_number_id","transaction_reference"]).returning(PaymentRequest.id)
        result=await self.repo.session.execute(stmt); pid=result.scalar_one_or_none()
        if pid is None: raise ValueError("يوجد طلب دفع سابق بنفس مرجع العملية لهذا الرقم.")
        return await self.repo.session.get(PaymentRequest,pid)
