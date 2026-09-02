from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import subscription_notifications,followup_notifications
from app.services.notification_service import send_pending
from app.database import SessionLocal
class SchedulerService:
    def __init__(self,bot):self.bot=bot;self.scheduler=AsyncIOScheduler(timezone='UTC')
    def start(self):
        self.scheduler.add_job(subscription_notifications,'interval',hours=6,id='subscription_notifications',replace_existing=True,max_instances=1,coalesce=True)
        self.scheduler.add_job(followup_notifications,'interval',hours=6,id='followup_notifications',replace_existing=True,max_instances=1,coalesce=True)
        self.scheduler.add_job(lambda:send_pending(self.bot,SessionLocal),'interval',minutes=2,id='notification_delivery',replace_existing=True,max_instances=1,coalesce=True)
        self.scheduler.start()
    async def stop(self):
        self.scheduler.shutdown(wait=False)
