from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from app.models import Subscription,SubscriptionStatus,PhoneNumber,PhoneStatus
from app.utils import utcnow
async def active_subscription(db,phone_id): return (await db.execute(select(Subscription).where(Subscription.phone_number_id==phone_id,Subscription.status!=SubscriptionStatus.cancelled).order_by(Subscription.ends_at.desc()))).scalars().first()
def classify_subscription(sub,now=None):
    if not sub or not sub.ends_at:return '⚫ منتهي'
    now=now or utcnow(); elapsed=(now-sub.starts_at).days if sub.starts_at else 0; total=sub.duration_days or 365
    if now>=sub.ends_at:return '⚫ منتهي'
    if elapsed<=299:return '🟢 أمن'
    if elapsed<=349:return '🟠 قريب'
    if elapsed<=365:return '🔴 خطر'
    return '⚫ منتهي'
def remaining(sub,now=None):
    if not sub or not sub.ends_at:return 0
    return max(0,(sub.ends_at-(now or utcnow())).days)
async def set_status(db,sub_id,status,admin_id):
    sub=(await db.execute(select(Subscription).where(Subscription.id==sub_id).with_for_update())).scalar_one_or_none()
    if not sub:return None
    old=sub.status;sub.status=status
    phone=(await db.execute(select(PhoneNumber).where(PhoneNumber.id==sub.phone_number_id).with_for_update())).scalar_one_or_none()
    if phone and status!=SubscriptionStatus.active: phone.status=PhoneStatus.suspended if status==SubscriptionStatus.suspended else PhoneStatus.inactive
    from app.services.audit_service import audit
    await audit(db,admin_id,'subscription_status','subscription',sub.id,{'status':old.value},{'status':status.value});return sub
