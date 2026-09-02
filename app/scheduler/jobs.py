from datetime import timedelta
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Subscription,SubscriptionStatus,Customer,PhoneNumber,Followup,FollowupStatus
from app.services.notification_service import queue_notification
from app.utils import utcnow
async def subscription_notifications():
    async with SessionLocal() as db:
        now=utcnow(); rows=(await db.execute(select(Subscription).where(Subscription.status==SubscriptionStatus.active,Subscription.ends_at.is_not(None)))).scalars().all()
        for s in rows:
            days=(s.ends_at-now).days; c=await db.get(Customer,s.customer_id); p=await db.get(PhoneNumber,s.phone_number_id)
            if not c or not p: continue
            if days<0: kind='subscription_expired'; text=f'⚫ انتهت حماية رقمك {p.phone_number}.'
            elif days<=15: kind='subscription_danger'; text=f'🔴 تبقى {days} يومًا على انتهاء حماية رقمك {p.phone_number}.'
            elif days<=65: kind='subscription_near'; text=f'🟠 تبقى {days} يومًا على انتهاء حماية رقمك {p.phone_number}.'
            else: continue
            await queue_notification(db,c.telegram_id,kind,text,f'{kind}:{s.id}:{s.ends_at.date()}')
        await db.commit()
async def followup_notifications():
    async with SessionLocal() as db:
        now=utcnow(); rows=(await db.execute(select(Followup).where(Followup.status.in_([FollowupStatus.upcoming,FollowupStatus.due,FollowupStatus.overdue]),Followup.due_at<=now+timedelta(days=7)))).scalars().all()
        for f in rows:
            p=await db.get(PhoneNumber,f.phone_number_id); c=await db.get(Customer,p.customer_id) if p else None
            if not c: continue
            kind='followup_due' if f.due_at<=now else 'followup_near'
            await queue_notification(db,c.telegram_id,'system','لديك متابعة مستحقة ضمن نظام أمان.',f'{kind}:{f.id}:{f.due_at.date()}')
        await db.commit()
