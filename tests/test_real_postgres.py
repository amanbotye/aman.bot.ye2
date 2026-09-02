"""Real PostgreSQL integration/concurrency tests.

Set TEST_DATABASE_URL to a dedicated PostgreSQL database before running. These
are intentionally skipped when no real PostgreSQL is available; SQLite and
fake sessions are never used as substitutes.
"""
import asyncio, os
from datetime import timedelta
from decimal import Decimal
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base
from app.models import Customer, TelecomCompany, PaymentMethod, PaymentRequest, PaymentStatus, PhoneNumber, PhoneStatus, Subscription, Followup, AuditLog, Notification, AdminUser
from app.services.fsm_service import FSMService
from app.services.phone_service import PhoneService
from app.repositories.phone_repository import PhoneRepository
from app.services.settings_service import SettingsService
from app.services.subscription_service import SubscriptionService

URL=os.getenv("TEST_DATABASE_URL")
pytestmark=pytest.mark.skipif(not URL, reason="REAL POSTGRESQL TESTS: BLOCKED BY ENVIRONMENT — set TEST_DATABASE_URL")

@pytest.fixture(scope="module")
async def db():
    engine=create_async_engine(URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine,expire_on_commit=False,class_=AsyncSession,autoflush=False)
    await engine.dispose()

@pytest.fixture(autouse=True)
async def clean(db):
    yield
    async with db() as s:
        await s.execute(__import__('sqlalchemy').text("TRUNCATE TABLE notifications, audit_logs, followups, subscriptions, payment_requests, phone_numbers, support_messages, support_tickets, fsm_states, faq_items, payment_methods, telecom_companies, customers, admin_users, system_settings RESTART IDENTITY CASCADE"))
        await s.commit()

@pytest.mark.asyncio
async def test_real_fsm_persistence_after_restart(db):
    async with db() as s:
        f=FSMService(s); state,data=await f.load(1001,2001); data["step"]="PHONE_INPUT"; await f.save(1001,2001,"PHONE_INPUT",data); await s.commit()
    async with db() as s:
        state,data=await FSMService(s).load(1001,2001); assert state=="PHONE_INPUT" and data["step"]=="PHONE_INPUT"; await s.rollback()

@pytest.mark.asyncio
async def test_real_fsm_same_user_updates_are_serialized(db):
    async with db() as s:
        f=FSMService(s); await f.load(1002,2002); await f.save(1002,2002,"BASE",{"n":0}); await s.commit()
    barrier=asyncio.Barrier(2)
    async def worker(label):
        async with db() as s:
            await barrier.wait()
            f=FSMService(s); state,data=await f.load(1002,2002); data["last"]=label; data["seen_state"]=state; await f.save(1002,2002,"UPDATED",data); await s.commit(); return data
    results=await asyncio.gather(worker("A"),worker("B"))
    assert all(r["seen_state"] in {"BASE","UPDATED"} for r in results)
    async with db() as s:
        state,data=await FSMService(s).load(1002,2002); assert state=="UPDATED" and data["last"] in {"A","B"}; await s.rollback()

@pytest.mark.asyncio
async def test_real_phone_unique_constraint_wins_race(db):
    async with db() as s:
        c1=Customer(telegram_id=3001); c2=Customer(telegram_id=3002); co=TelecomCompany(name="TestCo",code="T1"); s.add_all([c1,c2,co]); await s.flush(); ids=(c1.id,c2.id,co.id); await s.commit()
    async def register(cid):
        async with db() as s:
            try:
                p=await PhoneService(PhoneRepository(s)).register(cid,ids[2],"771234567"); await s.commit(); return True,p.id
            except Exception:
                await s.rollback(); return False,None
    results=await asyncio.gather(register(ids[0]),register(ids[1]))
    assert sum(ok for ok,_ in results)==1

@pytest.mark.asyncio
async def test_real_payment_approval_concurrency_is_single_winner(db):
    async with db() as s:
        c=Customer(telegram_id=4001,full_name="Test Customer"); co=TelecomCompany(name="TestCo",code="T2"); pm=PaymentMethod(name="TestPay",account_name="A",account_number="1",instructions="I"); a1=AdminUser(telegram_id=9001,role="finance"); a2=AdminUser(telegram_id=9002,role="finance"); s.add_all([c,co,pm,a1,a2]); await s.flush(); p=PhoneNumber(customer_id=c.id,telecom_company_id=co.id,phone_number="+967771234567",normalized_phone="+967771234567"); s.add(p); await s.flush(); pay=PaymentRequest(customer_id=c.id,phone_number_id=p.id,payment_method_id=pm.id,amount=Decimal("1000.00"),currency="YER",transaction_reference="R1"); s.add(pay); await s.commit(); pid=pay.id; c1=a1.id; c2=a2.id
    async def approve(admin_id):
        async with db() as s:
            try:
                sub,chat=await SubscriptionService(s,SettingsService(s)).approve_payment(pid,admin_id); await s.commit(); return True
            except ValueError:
                await s.rollback(); return False
    results=await asyncio.gather(approve(c1),approve(c2)); assert sum(results)==1
    async with db() as s:
        assert (await s.scalar(select(PaymentRequest.status).where(PaymentRequest.id==pid)))==PaymentStatus.APPROVED
        assert await s.scalar(select(__import__('sqlalchemy').func.count()).select_from(Subscription).where(Subscription.payment_request_id==pid))==1
        assert await s.scalar(select(__import__('sqlalchemy').func.count()).select_from(Followup).where(Followup.phone_number_id==phone_id))==1
        assert await s.scalar(select(__import__('sqlalchemy').func.count()).select_from(Notification).where(Notification.kind=="PAYMENT_APPROVED"))==1
        assert await s.scalar(select(__import__('sqlalchemy').func.count()).select_from(AuditLog).where(AuditLog.action=="approve_payment"))==1

@pytest.mark.asyncio
async def test_real_payment_approval_rolls_back_on_fk_failure(db):
    async with db() as s:
        c=Customer(telegram_id=5001,full_name="Rollback"); co=TelecomCompany(name="RollbackCo",code="RB"); pm=PaymentMethod(name="RollbackPay",account_name="A",account_number="1",instructions="I"); s.add_all([c,co,pm]); await s.flush(); p=PhoneNumber(customer_id=c.id,telecom_company_id=co.id,phone_number="+967771234568",normalized_phone="+967771234568"); s.add(p); await s.flush(); pay=PaymentRequest(customer_id=c.id,phone_number_id=p.id,payment_method_id=pm.id,amount=Decimal("1000.00"),currency="YER",transaction_reference="RB1"); s.add(pay); await s.commit(); pid=pay.id; phone_id=p.id
    async with db() as s:
        with pytest.raises(Exception):
            await SubscriptionService(s,SettingsService(s)).approve_payment(pid,999999999)
        await s.rollback()
    async with db() as s:
        pay=await s.get(PaymentRequest,pid); phone=await s.get(PhoneNumber,phone_id)
        assert pay.status==PaymentStatus.PENDING and phone.status==PhoneStatus.UNPROTECTED
        assert await s.scalar(__import__('sqlalchemy').select(__import__('sqlalchemy').func.count()).select_from(Subscription).where(Subscription.payment_request_id==pid))==0

@pytest.mark.asyncio
async def test_real_notification_claims_are_skip_locked_and_single_owner(db):
    from app.repositories.notification_repository import NotificationRepository
    async with db() as s:
        c=Customer(telegram_id=6001); s.add(c); await s.flush(); n=Notification(customer_id=c.id,kind="TEST",body="hello",dedupe_key="real-claim-1"); s.add(n); await s.commit()
    async def claim():
        async with db() as s:
            r=NotificationRepository(s); claims=await r.claim_pending(1,3,300); await s.commit(); return claims
    a,b=await asyncio.gather(claim(),claim())
    assert len(a)+len(b)==1

@pytest.mark.asyncio
async def test_real_notification_lease_recovers_after_crash(db):
    from app.repositories.notification_repository import NotificationRepository
    from sqlalchemy import text
    async with db() as s:
        c=Customer(telegram_id=6002); s.add(c); await s.flush(); n=Notification(customer_id=c.id,kind="TEST",body="hello",dedupe_key="real-lease-1"); s.add(n); await s.commit()
    async with db() as s:
        claims=await NotificationRepository(s).claim_pending(1,3,1); await s.commit()
        assert len(claims)==1
    async with db() as s:
        await s.execute(text("UPDATE notifications SET processing_until=now()-interval '1 second' WHERE dedupe_key='real-lease-1'")); await s.commit()
    async with db() as s:
        claims=await NotificationRepository(s).claim_pending(1,3,300); await s.commit(); assert len(claims)==1
