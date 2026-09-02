from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from ..models import Notification, Customer

class NotificationRepository:
    def __init__(self, s): self.s=s

    async def create(self, **kw):
        stmt=insert(Notification).values(**kw).on_conflict_do_nothing(index_elements=["dedupe_key"]).returning(Notification.id)
        result=await self.s.execute(stmt); nid=result.scalar_one_or_none()
        return await self.s.get(Notification,nid) if nid is not None else None

    async def get_customer(self,cid): return await self.s.get(Customer,cid)

    async def claim_pending(self, limit=50, max_attempts=3, lease_seconds=300):
        now=datetime.now(timezone.utc); lease_until=now+timedelta(seconds=lease_seconds)
        q=(select(Notification)
           .where(Notification.sent_at.is_(None), Notification.attempts < max_attempts,
                 ((Notification.next_attempt_at.is_(None)) | (Notification.next_attempt_at <= now)),
                 ((Notification.processing_until.is_(None)) | (Notification.processing_until <= now)))
           .order_by(Notification.id).limit(limit).with_for_update(skip_locked=True))
        rows=list((await self.s.scalars(q)).all())
        claims=[]
        for row in rows:
            token=uuid4().hex
            row.processing_token=token; row.processing_started_at=now; row.processing_until=lease_until; row.attempts += 1
            claims.append((row.id, token))
        await self.s.flush()
        return claims

    async def delivery_payload(self, notification_id, token):
        q=(select(Notification.id, Notification.body, Customer.telegram_id)
           .join(Customer, Customer.id==Notification.customer_id)
           .where(Notification.id==notification_id, Notification.processing_token==token, Notification.sent_at.is_(None)))
        row=(await self.s.execute(q)).one_or_none()
        return row

    async def mark_sent(self, notification_id, token, sent_at):
        stmt=(update(Notification).where(Notification.id==notification_id, Notification.processing_token==token, Notification.sent_at.is_(None))
              .values(sent_at=sent_at,last_error=None,next_attempt_at=None,processing_token=None,processing_started_at=None,processing_until=None))
        result=await self.s.execute(stmt); return result.rowcount == 1

    async def mark_failed(self, notification_id, token, error, next_attempt_at):
        stmt=(update(Notification).where(Notification.id==notification_id, Notification.processing_token==token, Notification.sent_at.is_(None))
              .values(last_error=error[:500], next_attempt_at=next_attempt_at, processing_token=None,processing_started_at=None,processing_until=None))
        result=await self.s.execute(stmt); return result.rowcount == 1
