from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from ..models import Followup, Notification
from ..services.followup_service import FollowupService
from ..services.settings_service import SettingsService
from ..utils import utcnow


async def followup_job(session_factory, bot=None, batch_size=200):
    now = utcnow()
    last_id = 0
    async with session_factory() as s:
        settings = SettingsService(s)
        service = FollowupService(settings)
        cycle = await service.cycle_days()
        while True:
            rows = list(
                (
                    await s.scalars(
                        select(Followup)
                        .where(Followup.id > last_id)
                        .order_by(Followup.id)
                        .limit(batch_size)
                    )
                ).all()
            )
            if not rows:
                break
            for fu in rows:
                last_id = fu.id
                classification = await service.classify(fu.cycle_start, fu.cycle_end, now)
                if fu.cycle_end <= now:
                    # Classification is intentionally calculated by the same
                    # service used everywhere else. The due event is emitted
                    # once per completed cycle, then the next cycle is advanced.
                    due_key = f"followup:{fu.id}:{fu.cycle_end.isoformat()}"
                    body = "🔄 حان موعد المتابعة الدورية لحماية الرقم."
                    if classification == "EXPIRED":
                        body = "🔄 انتهت دورة المتابعة الداخلية ويجب تنفيذ المتابعة الدورية."
                    stmt = (
                        insert(Notification)
                        .values(
                            customer_id=fu.customer_id,
                            kind="FOLLOWUP_DUE",
                            body=body,
                            dedupe_key=due_key,
                        )
                        .on_conflict_do_nothing(index_elements=["dedupe_key"])
                    )
                    await s.execute(stmt)
                    while fu.cycle_end <= now:
                        fu.cycle_start = fu.cycle_end
                        fu.cycle_end = fu.cycle_end + timedelta(days=cycle)
                    fu.last_followup_at = now
            await s.flush()
        await s.commit()
