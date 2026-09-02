from datetime import timedelta
from sqlalchemy import select
from ..models import Subscription, PhoneNumber, PhoneStatus, PaymentRequest, PaymentStatus, Followup, Customer, Notification, PaymentMethod
from ..utils import utcnow, money
from .audit_service import AuditService

class SubscriptionService:
    def __init__(self, s, settings): self.s=s; self.settings=settings

    async def classify(self, subscription, now=None):
        now = now or utcnow()
        if now >= subscription.end_at: return "EXPIRED"
        elapsed = max(0, (now - subscription.start_at).days)
        safe = await self.settings.get_int("subscription_safe_until_day")
        near = await self.settings.get_int("subscription_near_until_day")
        danger = await self.settings.get_int("subscription_danger_until_day")
        if elapsed <= safe: return "SAFE"
        if elapsed <= near: return "NEAR"
        if elapsed <= danger: return "DANGER"
        return "EXPIRED"

    async def approve_payment(self, payment_id, admin_id):
        now = utcnow()
        payment = await self.s.scalar(select(PaymentRequest).where(PaymentRequest.id == payment_id).with_for_update())
        if not payment: raise ValueError("طلب الدفع غير موجود.")
        if payment.status != PaymentStatus.PENDING: raise ValueError("⚠️ تم التعامل مع هذا الطلب مسبقًا.")
        phone = await self.s.scalar(select(PhoneNumber).where(PhoneNumber.id == payment.phone_number_id).with_for_update())
        customer = await self.s.scalar(select(Customer).where(Customer.id == payment.customer_id).with_for_update())
        if not phone or not customer or phone.customer_id != customer.id: raise ValueError("بيانات الدفع غير صالحة.")
        current = await self.s.scalar(select(Subscription).where(Subscription.phone_number_id == phone.id).order_by(Subscription.end_at.desc()).limit(1).with_for_update())
        duration = await self.settings.get_int("service_duration_days")
        cycle = await self.settings.get_int("followup_cycle_days")
        start = max(now, current.end_at) if current and current.end_at > now else now
        end = start + timedelta(days=duration)
        payment.status = PaymentStatus.APPROVED; payment.reviewed_by = admin_id; payment.reviewed_at = now; payment.rejection_reason = None
        sub = Subscription(customer_id=customer.id, phone_number_id=phone.id, payment_request_id=payment.id, start_at=start, end_at=end, price=money(payment.amount), currency=payment.currency)
        self.s.add(sub); phone.status = PhoneStatus.PROTECTED
        fu = await self.s.scalar(select(Followup).where(Followup.phone_number_id == phone.id).with_for_update())
        if fu: fu.cycle_start = now; fu.cycle_end = now + timedelta(days=cycle); fu.last_followup_at = None
        else: self.s.add(Followup(phone_number_id=phone.id, customer_id=customer.id, cycle_start=now, cycle_end=now + timedelta(days=cycle)))
        notification=Notification(customer_id=customer.id, kind="PAYMENT_APPROVED", body=f"✅ تمت الموافقة على الدفع.\n📱 الرقم: {phone.normalized_phone}\n🛡️ الحماية مفعلة حتى {end.date()}", dedupe_key=f"payment-approved:{payment.id}")
        self.s.add(notification)
        await AuditService().log(self.s, admin_id, "approve_payment", "payment_request", payment.id, new={"status":"APPROVED","subscription_end":end.isoformat()})
        await self.s.flush()
        return sub, customer.telegram_id

    async def reject_payment(self, payment_id, admin_id, reason):
        reason = " ".join(str(reason).split())
        if len(reason) < 3 or len(reason) > 1000: raise ValueError("سبب الرفض مطلوب.")
        payment = await self.s.scalar(select(PaymentRequest).where(PaymentRequest.id == payment_id).with_for_update())
        if not payment: raise ValueError("طلب الدفع غير موجود.")
        if payment.status != PaymentStatus.PENDING: raise ValueError("⚠️ تم التعامل مع هذا الطلب مسبقًا.")
        customer = await self.s.get(Customer, payment.customer_id)
        payment.status=PaymentStatus.REJECTED; payment.reviewed_by=admin_id; payment.reviewed_at=utcnow(); payment.rejection_reason=reason
        notification=Notification(customer_id=customer.id, kind="PAYMENT_REJECTED", body=f"❌ تم رفض طلب الدفع.\nالسبب: {reason}", dedupe_key=f"payment-rejected:{payment.id}")
        self.s.add(notification)
        await AuditService().log(self.s, admin_id, "reject_payment", "payment_request", payment.id, new={"status":"REJECTED","reason":reason})
        await self.s.flush(); return customer.telegram_id

    async def renew(self, phone_id, admin_id, duration_days, price, currency, reason="ADMIN_RENEWAL"):
        now=utcnow(); phone=await self.s.scalar(select(PhoneNumber).where(PhoneNumber.id==phone_id).with_for_update())
        if not phone: raise ValueError("الرقم غير موجود")
        current=await self.s.scalar(select(Subscription).where(Subscription.phone_number_id==phone_id).order_by(Subscription.end_at.desc()).limit(1).with_for_update())
        start=max(now,current.end_at) if current and current.end_at>now else now
        method=await self.s.scalar(select(PaymentMethod).where(PaymentMethod.name=="ADMIN-MANUAL").limit(1))
        if not method:
            method=PaymentMethod(name="ADMIN-MANUAL",account_name="ADMIN",account_number="INTERNAL",instructions="Internal administrative renewal",requires_proof=False,active=False,sort_order=999999); self.s.add(method); await self.s.flush()
        payment=PaymentRequest(customer_id=phone.customer_id,phone_number_id=phone_id,payment_method_id=method.id,amount=money(price),currency=currency,transaction_reference=f"ADMIN-{admin_id}-{int(now.timestamp())}",status=PaymentStatus.APPROVED,reviewed_by=admin_id,reviewed_at=now)
        self.s.add(payment); await self.s.flush()
        sub=Subscription(customer_id=phone.customer_id,phone_number_id=phone_id,payment_request_id=payment.id,start_at=start,end_at=start+timedelta(days=duration_days),price=money(price),currency=currency)
        self.s.add(sub); phone.status=PhoneStatus.PROTECTED
        cycle=await self.settings.get_int("followup_cycle_days")
        fu=await self.s.scalar(select(Followup).where(Followup.phone_number_id==phone_id).with_for_update())
        if fu: fu.cycle_start=now; fu.cycle_end=now+timedelta(days=cycle); fu.last_followup_at=None
        else: self.s.add(Followup(phone_number_id=phone_id,customer_id=phone.customer_id,cycle_start=now,cycle_end=now+timedelta(days=cycle)))
        await AuditService().log(self.s,admin_id,"subscription_renewal","subscription",sub.id,new={"phone_id":phone_id,"days":duration_days,"reason":reason})
        await self.s.flush(); return sub

    async def extend(self, subscription_id, admin_id, extra_days):
        if extra_days < 1 or extra_days > 3650: raise ValueError("مدة التمديد غير صحيحة")
        sub=await self.s.scalar(select(Subscription).where(Subscription.id==subscription_id).with_for_update())
        if not sub: raise ValueError("الاشتراك غير موجود")
        old=sub.end_at; sub.end_at=old+timedelta(days=extra_days)
        await AuditService().log(self.s,admin_id,"subscription_extension","subscription",sub.id,old={"end_at":old.isoformat()},new={"end_at":sub.end_at.isoformat(),"days":extra_days})
        await self.s.flush(); return sub
