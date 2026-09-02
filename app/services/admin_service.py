from sqlalchemy import select,func,or_
from app.models import AdminUser,Customer,PhoneNumber,PaymentRequest,PaymentStatus,Subscription,SubscriptionStatus,SupportTicket,SupportStatus,Followup,FollowupStatus,Notification,NotificationStatus,AuditLog,FAQ,PaymentMethod,TelecomCompany
from app.config import settings
ROLES={'super_admin':{'*'},'finance':{'payments','settings_read','reports'},'support':{'customers','support'},'operations':{'numbers','subscriptions','followups'},'viewer':{'dashboard','reports_read'}}
async def ensure_admins(db):
    for tid in settings.admin_ids:
        x=(await db.execute(select(AdminUser).where(AdminUser.telegram_id==tid))).scalar_one_or_none()
        if not x:db.add(AdminUser(telegram_id=tid,role='super_admin',is_active=True))
    await db.commit()
async def get_admin(db,tid):return (await db.execute(select(AdminUser).where(AdminUser.telegram_id==tid,AdminUser.is_active.is_(True)))).scalar_one_or_none()
async def is_admin(db,tid):return bool(await get_admin(db,tid)) or tid in settings.admin_ids
async def can(db,tid,permission):
    a=await get_admin(db,tid)
    if not a:return tid in settings.admin_ids
    return '*' in ROLES.get(a.role,set()) or permission in ROLES.get(a.role,set())
async def dashboard(db):
    def c(q):return int(q.scalar_one() or 0)
    return {'customers':c(await db.execute(select(func.count(Customer.id)))),'active_customers':c(await db.execute(select(func.count(Customer.id)).where(Customer.status=='active'))),'phones':c(await db.execute(select(func.count(PhoneNumber.id)))),'protected':c(await db.execute(select(func.count(PhoneNumber.id)).where(PhoneNumber.status=='active'))),'pending_payments':c(await db.execute(select(func.count(PaymentRequest.id)).where(PaymentRequest.status==PaymentStatus.pending))),'active_subscriptions':c(await db.execute(select(func.count(Subscription.id)).where(Subscription.status==SubscriptionStatus.active))),'open_tickets':c(await db.execute(select(func.count(SupportTicket.id)).where(SupportTicket.status.in_([SupportStatus.new,SupportStatus.open])))), 'followups_due':c(await db.execute(select(func.count(Followup.id)).where(Followup.status.in_([FollowupStatus.due,FollowupStatus.overdue])))), 'notifications_failed':c(await db.execute(select(func.count(Notification.id)).where(Notification.status==NotificationStatus.failed))), 'faqs':c(await db.execute(select(func.count(FAQ.id)).where(FAQ.is_active.is_(True)))), 'payment_methods':c(await db.execute(select(func.count(PaymentMethod.id)).where(PaymentMethod.is_active.is_(True))))}
