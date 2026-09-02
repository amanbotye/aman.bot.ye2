from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from ..models import Subscription, Notification, PhoneNumber, PhoneStatus
from ..utils import utcnow

WARNING_DAYS = (1, 3, 7, 30)

def warning_day_for_remaining(remaining):
    """Return the first warning window containing a positive remaining time."""
    return next((d for d in WARNING_DAYS if timedelta(seconds=0) < remaining <= timedelta(days=d)), None)


async def subscription_job(session_factory, bot=None, batch_size=200):
    now=utcnow()
    last_id=0
    async with session_factory() as s:
        while True:
            # Only the latest subscription for each phone can drive current
            # warnings/expiry. Older historical subscriptions remain intact.
            # Correlated alias keeps historical subscriptions untouched.
            from sqlalchemy.orm import aliased
            later = aliased(Subscription)
            q = (
                select(Subscription,PhoneNumber)
                .join(PhoneNumber,PhoneNumber.id==Subscription.phone_number_id)
                .where(
                    Subscription.id>last_id,
                    ~select(later.id).where(
                        later.phone_number_id==Subscription.phone_number_id,
                        later.end_at>Subscription.end_at,
                    ).exists(),
                )
                .order_by(Subscription.id)
                .limit(batch_size)
            )
            rows=list((await s.execute(q)).all())
            if not rows:
                break
            for sub,phone in rows:
                last_id=sub.id
                if sub.end_at<=now:
                    if phone.status==PhoneStatus.PROTECTED:
                        phone.status=PhoneStatus.EXPIRED
                    n=Notification(
                        customer_id=sub.customer_id,
                        kind="SUBSCRIPTION_EXPIRED",
                        body=f"⚫ انتهت حماية رقمك {phone.normalized_phone}.",
                        dedupe_key=f"subscription-expired:{sub.id}",
                    )
                else:
                    remaining=sub.end_at-now
                    # Warning windows are inclusive. If a daily job runs a few seconds
                    # late, the 30/7/3/1-day warning is still emitted exactly once
                    # through the notification dedupe key.
                    days=warning_day_for_remaining(remaining)
                    if days is None:
                        continue
                    n=Notification(
                        customer_id=sub.customer_id,
                        kind="SUBSCRIPTION_WARNING",
                        body=f"🔔 تنبيه: تبقى {days} يومًا على انتهاء حماية رقمك {phone.normalized_phone}.",
                        dedupe_key=f"subscription-warning:{sub.id}:{days}",
                    )
                stmt=(
                    insert(Notification)
                    .values(customer_id=n.customer_id,kind=n.kind,body=n.body,dedupe_key=n.dedupe_key)
                    .on_conflict_do_nothing(index_elements=["dedupe_key"])
                )
                await s.execute(stmt)
            await s.flush()
        await s.commit()
