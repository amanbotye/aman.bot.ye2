import asyncio, logging, os, copy
from sqlalchemy import select
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from app.config import Settings
from app.database import create_session_factory
from app.models import AdminUser, SystemSetting, TelecomCompany, PaymentMethod, FAQItem
from app.repositories.customer_repository import CustomerRepository
from app.repositories.phone_repository import PhoneRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.support_repository import SupportRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.customer_service import CustomerService
from app.services.phone_service import PhoneService
from app.services.payment_service import PaymentService
from app.services.settings_service import SettingsService
from app.services.subscription_service import SubscriptionService
from app.services.support_service import SupportService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.services.admin_service import AdminService
from app.services.fsm_service import FSMService
from app.services.audit_service import AuditService
from app.scheduler.scheduler import build_scheduler
from app.handlers.customer import start_customer, protect, text_router, my_phones, account, faq
from app.handlers.payment import begin_payment, payment_router, proof_router
from app.handlers.support import start_support, support_router
from app.handlers.admin import start_admin, admin_text, admin_state_router, ensure_admin
from app.keyboards import customer_home, admin_home
from app.admin.permissions import PERMISSIONS

logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),format="%(asctime)s %(levelname)s %(name)s %(message)s")
log=logging.getLogger("aman")


def make_services(session):
    settings=SettingsService(session)
    cr=CustomerRepository(session); pr=PhoneRepository(session); pay=PaymentRepository(session); sr=SupportRepository(session); nr=NotificationRepository(session)
    return {"customer":CustomerService(cr),"phone":PhoneService(pr),"phone_repo":pr,"customer_repo":cr,"payment":PaymentService(pay,settings),"payment_repo":pay,"settings":settings,"subscription":SubscriptionService(session,settings),"support":SupportService(sr),"support_repo":sr,"notification":NotificationService(nr),"report":ReportService(),"admin":AdminService(session),"fsm":FSMService(session)}

async def seed_runtime(session,settings,production_admins=None,production_session=None):
    await SettingsService(session).seed_defaults()
    if production_admins is not None:
        for src in production_admins:
            row=await session.scalar(select(AdminUser).where(AdminUser.telegram_id==src.telegram_id))
            if row: row.role=src.role; row.active=True
            else: session.add(AdminUser(telegram_id=src.telegram_id,role=src.role,active=True))
    if production_session is not None:
        companies=list((await production_session.scalars(select(TelecomCompany).where(TelecomCompany.active.is_(True)))).all())
        for src in companies:
            row=await session.scalar(select(TelecomCompany).where(TelecomCompany.code==src.code))
            if row: row.name=src.name; row.active=True; row.sort_order=src.sort_order
            else: session.add(TelecomCompany(name=src.name,code=src.code,active=True,sort_order=src.sort_order))
        methods=list((await production_session.scalars(select(PaymentMethod).where(PaymentMethod.active.is_(True)))).all())
        for src in methods:
            row=await session.scalar(select(PaymentMethod).where(PaymentMethod.name==src.name))
            if row: row.account_name=src.account_name; row.account_number=src.account_number; row.instructions=src.instructions; row.requires_proof=src.requires_proof; row.active=True; row.sort_order=src.sort_order
            else: session.add(PaymentMethod(name=src.name,account_name=src.account_name,account_number=src.account_number,instructions=src.instructions,requires_proof=src.requires_proof,active=True,sort_order=src.sort_order))
        faqs=list((await production_session.scalars(select(FAQItem).where(FAQItem.active.is_(True)))).all())
        for src in faqs:
            row=await session.scalar(select(FAQItem).where(FAQItem.question==src.question))
            if row: row.answer=src.answer; row.active=True; row.sort_order=src.sort_order
            else: session.add(FAQItem(question=src.question,answer=src.answer,active=True,sort_order=src.sort_order))
    await session.flush()

async def notify_admins(bot,admin_ids,payment_id):
    for tid in admin_ids:
        try: await bot.send_message(chat_id=tid,text=f"💰 طلب دفع جديد #{payment_id}\nافتح قسم المدفوعات لمراجعته.")
        except Exception: log.warning("admin notification failed for %s",tid)

async def dispatch(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_chat or not update.message:
        return
    sf=context.application.bot_data["session_factory"]
    settings=context.application.bot_data["settings"]
    tid=update.effective_user.id
    chat=update.effective_chat.id
    original_message=update.message
    deferred_message=DeferredMessage(original_message)
    update=copy.copy(update)
    update.message=deferred_message

    # Production mode deliberately uses one DB session for both FSM and
    # business data. This makes the FSM write and the business transaction
    # atomic. Sandbox keeps the authoritative FSM in Production only as a
    # small mode pointer; all customer/business records live in Sandbox DB.
    async with sf() as production_session:
        prod_fsm=FSMService(production_session)
        state,data=await prod_fsm.load(tid,chat)
        context.user_data.clear()
        context.user_data.update(data,state=state)
        prod_admin=await ensure_admin(production_session,tid)
        text=(update.message.text or "").strip()
        sandbox=bool(context.user_data.get("sandbox"))
        business_session=production_session
        sandbox_session=None
        try:
            if sandbox:
                sandbox_sf=context.application.bot_data.get("sandbox_session_factory")
                if not sandbox_sf:
                    raise PermissionError("Sandbox غير مهيأ.")
                sandbox_session=sandbox_sf()
                business_session=await sandbox_session.__aenter__()
                if not context.user_data.get("sandbox_initialized"):
                    prod_admins=list((await production_session.scalars(select(AdminUser).where(AdminUser.active.is_(True)))).all())
                    await seed_runtime(business_session,settings,prod_admins,production_session)
                    context.user_data["sandbox_initialized"]=True

            services=make_services(business_session)
            admin=await ensure_admin(business_session,tid) if sandbox else prod_admin

            if text.lower()=="a" and prod_admin and context.user_data.get("mode")=="customer":
                context.user_data["mode"]="admin"
                context.user_data["state"]="IDLE"
                await update.message.reply_text(
                    ("🧪 عدت إلى إدارة Sandbox." if sandbox else "🛡️ عدت إلى الإدارة."),
                    reply_markup=admin_home((await AdminService(business_session).permissions(tid)),sandbox=sandbox),
                )
            elif text=="/start":
                if prod_admin:
                    await start_admin(update,context,business_session,services)
                else:
                    await start_customer(update,context,business_session,services)
            elif admin and context.user_data.get("mode")!="customer" and context.user_data.get("state") not in ("IDLE",None):
                await admin_state_router(update,context,business_session,services)
            elif admin and context.user_data.get("mode")!="customer":
                if text=="🧪 الخروج من الاختبار" and sandbox:
                    await AuditService().log(production_session,tid,"sandbox_exit","sandbox",tid,new={"sandbox":False})
                    context.user_data.update(sandbox=False,mode="admin",state="IDLE")
                    await update.message.reply_text(
                        "تم الخروج من Sandbox.",
                        reply_markup=admin_home((await AdminService(production_session).permissions(tid))),
                    )
                else:
                    await admin_text(update,context,business_session,services)
            elif text=="🛡️ حماية رقم":
                await protect(update,context,business_session,services)
            elif text=="📱 أرقامي":
                await my_phones(update,context,business_session,services)
            elif text=="👤 حسابي":
                await account(update,context,business_session,services)
            elif text=="❓ المساعدة":
                await faq(update,context,business_session,services)
            elif text=="💬 الدعم":
                await start_support(update,context)
            elif text=="🛡️ تفعيل الحماية":
                c=await services["customer"].get_or_create(tid)
                context.user_data["customer_id"]=c.id
                await begin_payment(update,context,business_session,services,context.user_data.get("phone_id"))
            elif context.user_data.get("state")=="PAYMENT_PROOF" and (update.message.photo or update.message.document):
                await proof_router(update,context,business_session,services)
            elif str(context.user_data.get("state","")).startswith("PAYMENT_"):
                await payment_router(update,context,business_session,services)
            elif str(context.user_data.get("state","")).startswith("SUPPORT_"):
                await support_router(update,context,business_session,services)
            else:
                await text_router(update,context,business_session,services)

            payment_id=context.user_data.pop("admin_payment_created",None)
            post_commit_admin_message=context.user_data.pop("post_commit_admin_message",None)
            context.user_data.pop("post_commit_message",None)
            context.user_data.pop("post_commit_chat",None)

            serializable={
                k:v for k,v in context.user_data.items()
                if k!="state" and isinstance(v,(str,int,bool,type(None),dict,list))
            }
            # In production this commits business changes and FSM together.
            # In sandbox, commit isolated business data first, then the
            # production FSM mode/state pointer.
            await prod_fsm.save(tid,chat,context.user_data.get("state","IDLE"),serializable)
            if sandbox:
                await business_session.commit()
                await production_session.commit()
            else:
                await production_session.commit()

            # The transaction has committed. Only now perform Telegram I/O.
            for args,kwargs in deferred_message.outbox:
                try:
                    await original_message.reply_text(*args,**kwargs)
                except Exception:
                    log.exception("Post-commit Telegram reply failed")
            if post_commit_admin_message:
                try:
                    await original_message.reply_text(
                        post_commit_admin_message,
                        reply_markup=admin_home(PERMISSIONS[prod_admin.role] if prod_admin else set(),sandbox=sandbox),
                    )
                except Exception:
                    log.exception("Post-commit admin Telegram reply failed")
            if payment_id and not sandbox:
                await notify_admins(context.bot,settings.admin_ids,payment_id)
        except (PermissionError,ValueError) as exc:
            await production_session.rollback()
            if sandbox and sandbox_session is not None:
                await business_session.rollback()
            await original_message.reply_text(
                str(exc),
                reply_markup=customer_home() if context.user_data.get("mode")=="customer" else None,
            )
        except Exception:
            await production_session.rollback()
            if sandbox and sandbox_session is not None:
                await business_session.rollback()
            log.exception("Unhandled update")
            await original_message.reply_text("حدث خطأ غير متوقع. حاول مرة أخرى.")
        finally:
            if sandbox_session is not None:
                await sandbox_session.__aexit__(None,None,None)

class DeferredMessage:
    """Proxy Telegram Message so handlers queue replies until DB commit.

    This keeps Telegram network I/O outside the critical database transaction
    without changing the existing handlers/UX.
    """
    def __init__(self, original):
        self._original=original
        self.outbox=[]
    def __getattr__(self,name): return getattr(self._original,name)
    async def reply_text(self,*args,**kwargs):
        self.outbox.append((args,kwargs))
        return None

async def error_handler(update,context): log.error("Telegram update error: %s",context.error)

async def run():
    settings=Settings.from_env(); engine,sf=create_session_factory(settings.database_url,settings.db_pool_size,settings.db_max_overflow)
    async with sf() as s:
        await SettingsService(s).seed_defaults(); await AdminService(s).bootstrap(settings.admin_ids); await s.commit()
    sandbox_engine=sandbox_sf=None
    if settings.sandbox_database_url:
        sandbox_engine,sandbox_sf=create_session_factory(settings.sandbox_database_url,settings.db_pool_size,settings.db_max_overflow)
    application=Application.builder().token(settings.bot_token).build()
    application.bot_data.update(session_factory=sf,settings=settings,sandbox_session_factory=sandbox_sf)
    application.add_handler(CommandHandler("start",dispatch)); application.add_handler(MessageHandler(filters.ALL,dispatch)); application.add_error_handler(error_handler)
    scheduler=None
    try:
        await application.initialize(); await application.start(); await application.updater.start_polling(drop_pending_updates=False)
        scheduler=build_scheduler(settings.timezone,sf,application.bot); scheduler.start()
        await asyncio.Event().wait()
    finally:
        if scheduler is not None: scheduler.shutdown(wait=False)
        await application.updater.stop(); await application.stop(); await application.shutdown(); await engine.dispose()
        if sandbox_engine: await sandbox_engine.dispose()

if __name__=="__main__": asyncio.run(run())
