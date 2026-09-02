from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .subscription_jobs import subscription_job
from .followup_jobs import followup_job
from .notification_jobs import notification_job

def build_scheduler(timezone,session_factory,bot):
    s=AsyncIOScheduler(timezone=timezone)
    s.add_job(subscription_job,"cron",hour=1,minute=5,args=[session_factory,bot],id="subscription_warnings",replace_existing=True,max_instances=1,coalesce=True)
    s.add_job(followup_job,"cron",hour=1,minute=20,args=[session_factory,bot],id="followup_cycle",replace_existing=True,max_instances=1,coalesce=True)
    s.add_job(notification_job,"interval",minutes=1,args=[session_factory,bot],id="notifications",replace_existing=True,max_instances=1,coalesce=True)
    return s
