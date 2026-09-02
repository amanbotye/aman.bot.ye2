from datetime import timedelta
from sqlalchemy import select
from app.models import Notification,NotificationStatus
from app.utils import utcnow
async def queue_notification(db,recipient,kind,text,dedupe_key):
    x=(await db.execute(select(Notification).where(Notification.dedupe_key==dedupe_key))).scalar_one_or_none()
    if x:return x
    x=Notification(recipient_telegram_id=recipient,kind=kind,text=text,dedupe_key=dedupe_key);db.add(x);await db.flush();return x
async def send_pending(bot,session_factory,max_attempts=3):
    from sqlalchemy import select
    from app.models import Notification
    async with session_factory() as db:
        rows=(await db.execute(select(Notification).where(Notification.status==NotificationStatus.pending,Notification.attempts<max_attempts).order_by(Notification.created_at).limit(50).with_for_update(skip_locked=True))).scalars().all()
        for n in rows:
            n.attempts+=1
            try:
                await bot.send_message(chat_id=n.recipient_telegram_id,text=n.text)
                n.status=NotificationStatus.sent;n.sent_at=utcnow();n.last_error=None
            except Exception as exc:
                n.status=NotificationStatus.failed if n.attempts>=max_attempts else NotificationStatus.pending;n.last_error=str(exc)[:1000]
        await db.commit()
