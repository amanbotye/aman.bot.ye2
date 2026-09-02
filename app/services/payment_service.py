from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PaymentRequest,PaymentStatus,PaymentMethod,Subscription,SubscriptionStatus,PhoneNumber,PhoneStatus,Followup,FollowupStatus
from app.services.settings_service import get_decimal,get,get_int
from app.services.audit_service import audit
from app.utils import payment_code,utcnow
async def active_methods(db): return (await db.execute(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.sort_order,PaymentMethod.id))).scalars().all()
async def pending_for(db,customer_id,phone_id): return (await db.execute(select(PaymentRequest).where(PaymentRequest.customer_id==customer_id,PaymentRequest.phone_number_id==phone_id,PaymentRequest.status==PaymentStatus.pending).order_by(PaymentRequest.created_at.desc()))).scalars().first()
async def create_payment(db,customer_id,phone_id,method,reference,proof=None,proof_type=None):
    existing=await pending_for(db,customer_id,phone_id)
    if existing:return existing,False
    amount=await get_decimal(db,'service_price',Decimal('1000')); currency=await get(db,'currency','YER')
    for _ in range(8):
        code=payment_code()
        if not (await db.execute(select(PaymentRequest).where(PaymentRequest.payment_code==code))).scalar_one_or_none(): break
    p=PaymentRequest(payment_code=code,customer_id=customer_id,phone_number_id=phone_id,payment_method_id=method.id,amount=amount,currency=currency,transaction_reference=reference.strip(),proof_file_url=proof,proof_file_type=proof_type); db.add(p); await db.flush(); return p,True
async def approve_payment(db,payment_id,admin_id):
    p=(await db.execute(select(PaymentRequest).where(PaymentRequest.id==payment_id).with_for_update())).scalar_one_or_none()
    if not p or p.status!=PaymentStatus.pending:return None,'already_processed'
    phone=(await db.execute(select(PhoneNumber).where(PhoneNumber.id==p.phone_number_id).with_for_update())).scalar_one_or_none()
    if not phone:return None,'phone_missing'
    now=utcnow(); days=await get_int(db,'service_duration_days',365)
    sub=(await db.execute(select(Subscription).where(Subscription.phone_number_id==phone.id,Subscription.status.in_([SubscriptionStatus.active,SubscriptionStatus.suspended])).order_by(Subscription.ends_at.desc()).with_for_update())).scalars().first()
    if sub and sub.ends_at and sub.ends_at>now:
        start=sub.starts_at or now; end=sub.ends_at+timedelta(days=days); sub.ends_at=end; sub.price=Decimal(p.amount); sub.currency=p.currency; sub.duration_days=days; sub.status=SubscriptionStatus.active
    else:
        start=now; end=now+timedelta(days=days); sub=Subscription(customer_id=p.customer_id,phone_number_id=phone.id,price=Decimal(p.amount),currency=p.currency,duration_days=days,duration_months=days//30,starts_at=start,ends_at=end,status=SubscriptionStatus.active); db.add(sub); await db.flush()
    p.subscription_id=sub.id; p.status=PaymentStatus.approved; p.reviewed_at=now; p.reviewed_by=admin_id; phone.status=PhoneStatus.active; cycle=await get_int(db,'followup_cycle_days',90)
    existing_followup=(await db.execute(select(Followup).where(Followup.phone_number_id==phone.id,Followup.status.in_([FollowupStatus.upcoming,FollowupStatus.due,FollowupStatus.overdue])).order_by(Followup.due_at))).scalars().first()
    if not existing_followup:
        db.add(Followup(phone_number_id=phone.id,subscription_id=sub.id,previous_followup_at=None,due_at=now+timedelta(days=cycle),status=FollowupStatus.upcoming))
    await audit(db,admin_id,'approve_payment','payment_request',p.id,{'status':'pending'},{'status':'approved','subscription_id':sub.id}); return p,'approved'
async def reject_payment(db,payment_id,admin_id,reason):
    p=(await db.execute(select(PaymentRequest).where(PaymentRequest.id==payment_id).with_for_update())).scalar_one_or_none()
    if not p or p.status!=PaymentStatus.pending:return None,'already_processed'
    p.status=PaymentStatus.rejected;p.rejection_reason=reason;p.reviewed_at=utcnow();p.reviewed_by=admin_id;await audit(db,admin_id,'reject_payment','payment_request',p.id,{'status':'pending'},{'status':'rejected','reason':reason});return p,'rejected'
