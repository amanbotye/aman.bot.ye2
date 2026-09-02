from datetime import timedelta
from ..services.notification_service import NotificationService
from ..repositories.notification_repository import NotificationRepository
from ..services.settings_service import SettingsService
from ..utils import utcnow
from sqlalchemy import select
from ..models import Notification

async def notification_job(session_factory,bot):
    # Read the authoritative retry limit on every run; no restart is required
    # after an administrator changes the setting.
    async with session_factory() as s:
        max_attempts=await SettingsService(s).get_int("notification_max_attempts")
        service=NotificationService(NotificationRepository(s))
        claims=await service.claim_pending(50,max_attempts)
        await s.commit()

    for notification_id, token in claims:
        # Read the delivery target in a short-lived transaction, then close it
        # before touching Telegram. Telegram I/O is never performed while a DB
        # transaction is open.
        async with session_factory() as s:
            repo=NotificationRepository(s)
            payload=await repo.delivery_payload(notification_id,token)
            await s.rollback()
        if not payload:
            continue

        try:
            await bot.send_message(chat_id=payload.telegram_id,text=payload.body)
        except Exception as exc:
            async with session_factory() as s:
                repo=NotificationRepository(s)
                row=await s.scalar(select(Notification).where(Notification.id==notification_id,Notification.processing_token==token))
                attempts=row.attempts if row else max_attempts
                retry_at=(utcnow()+timedelta(seconds=min(3600,30*(2**max(0,attempts-1))))) if attempts < max_attempts else None
                await repo.mark_failed(notification_id,token,str(exc),retry_at)
                await s.commit()
            continue

        async with session_factory() as s:
            repo=NotificationRepository(s)
            await repo.mark_sent(notification_id,token,utcnow())
            await s.commit()
