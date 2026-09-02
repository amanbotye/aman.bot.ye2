from datetime import timedelta
from sqlalchemy import select, func, case
from ..models import Customer, PhoneNumber, Subscription, PaymentRequest, PaymentStatus, SupportTicket, TicketStatus, PhoneStatus, CustomerStatus
from ..utils import utcnow
class ReportService:
    async def dashboard(self,s,settings=None):
        now=utcnow(); today=now.replace(hour=0,minute=0,second=0,microsecond=0); week=today-timedelta(days=today.weekday()); month=today.replace(day=1)
        async def count(model,*conds): return int(await s.scalar(select(func.count()).select_from(model).where(*conds)) or 0)
        safe=await settings.get_int("subscription_safe_until_day") if settings else 299; near=await settings.get_int("subscription_near_until_day") if settings else 349; danger=await settings.get_int("subscription_danger_until_day") if settings else 365
        elapsed=func.floor(func.extract("epoch", now - Subscription.start_at) / 86400)
        cls=case((Subscription.end_at<=now,"EXPIRED"),(elapsed<=safe,"SAFE"),(elapsed<=near,"NEAR"),(elapsed<=danger,"DANGER"),else_="EXPIRED")
        sub_counts=dict((row[0],int(row[1])) for row in (await s.execute(select(cls,func.count()).select_from(Subscription).group_by(cls))).all())
        revenue=lambda start:s.scalar(select(func.coalesce(func.sum(PaymentRequest.amount),0)).where(PaymentRequest.status==PaymentStatus.APPROVED,PaymentRequest.reviewed_at>=start))
        ranked_sub = (
            select(
                Subscription.phone_number_id,
                Subscription.start_at,
                Subscription.end_at,
                func.row_number().over(
                    partition_by=Subscription.phone_number_id,
                    order_by=(Subscription.end_at.desc(), Subscription.id.desc()),
                ).label("rn"),
            )
            .subquery()
        )
        latest_sub = select(
            ranked_sub.c.phone_number_id, ranked_sub.c.start_at, ranked_sub.c.end_at
        ).where(ranked_sub.c.rn == 1).subquery()
        phone_elapsed = func.floor(func.extract("epoch", now - latest_sub.c.start_at) / 86400)
        phone_class = case(
            (latest_sub.c.end_at <= now, "EXPIRED"),
            (phone_elapsed <= safe, "SAFE"),
            (phone_elapsed <= near, "NEAR"),
            (phone_elapsed <= danger, "DANGER"),
            else_="EXPIRED",
        )
        phone_counts = dict(
            (row[0], int(row[1]))
            for row in (
                await s.execute(
                    select(phone_class, func.count())
                    .select_from(latest_sub)
                    .group_by(phone_class)
                )
            ).all()
        )
        return {
          "customers_total":await count(Customer),"customers_active":await count(Customer,Customer.status==CustomerStatus.ACTIVE),"customers_blocked":await count(Customer,Customer.status==CustomerStatus.BLOCKED),"customers_today":await count(Customer,Customer.created_at>=today),"customers_week":await count(Customer,Customer.created_at>=week),
          "phones_total":await count(PhoneNumber),"phones_protected":await count(PhoneNumber,PhoneNumber.status==PhoneStatus.PROTECTED),"phones_unprotected":await count(PhoneNumber,PhoneNumber.status==PhoneStatus.UNPROTECTED),"phones_expired":await count(PhoneNumber,PhoneNumber.status==PhoneStatus.EXPIRED),"phones_near":phone_counts.get("NEAR",0),"phones_danger":phone_counts.get("DANGER",0),
          "subscriptions_safe":sub_counts.get("SAFE",0),"subscriptions_near":sub_counts.get("NEAR",0),"subscriptions_danger":sub_counts.get("DANGER",0),"subscriptions_expired":sub_counts.get("EXPIRED",0),
          "payments_pending":await count(PaymentRequest,PaymentRequest.status==PaymentStatus.PENDING),"payments_approved":await count(PaymentRequest,PaymentRequest.status==PaymentStatus.APPROVED),"payments_rejected":await count(PaymentRequest,PaymentRequest.status==PaymentStatus.REJECTED),"revenue_today":await revenue(today),"revenue_month":await revenue(month),
          "support_new":await count(SupportTicket,SupportTicket.status==TicketStatus.OPEN),"support_pending":await count(SupportTicket,SupportTicket.status==TicketStatus.PENDING_CUSTOMER)
        }
    async def period(self,s,start,end):
        return {"customers":int(await s.scalar(select(func.count()).select_from(Customer).where(Customer.created_at>=start,Customer.created_at<end)) or 0),"payments":int(await s.scalar(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.created_at>=start,PaymentRequest.created_at<end)) or 0),"revenue":await s.scalar(select(func.coalesce(func.sum(PaymentRequest.amount),0)).where(PaymentRequest.status==PaymentStatus.APPROVED,PaymentRequest.reviewed_at>=start,PaymentRequest.reviewed_at<end))}
