import asyncio
import logging
import os

from alembic import command
from alembic.config import Config

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import settings
from app.database import SessionLocal, close_db
from app.models import PaymentMethod
from app.services.settings_service import seed_defaults
from app.services.customer_service import seed_companies
from app.services.admin_service import ensure_admins
from app.handlers.router import start, message_router
from app.scheduler.runner import SchedulerService
from app.web import run_health_server


logging.basicConfig(
    level=getattr(
        logging,
        settings.LOG_LEVEL.upper(),
        logging.INFO,
    ),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

log = logging.getLogger("aman")


def run_migrations():
    """Run Alembic migrations safely before application initialization."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini = os.path.join(base_dir, "alembic.ini")

    config = Config(alembic_ini)
    command.upgrade(config, "head")


async def initialize_reference_data():
    from sqlalchemy import select

    async with SessionLocal() as db:
        await seed_defaults(db)
        await seed_companies(db)
        await ensure_admins(db)

        test_method = (
            await db.execute(
                select(PaymentMethod).where(
                    PaymentMethod.name == "طريقة دفع تجريبية AMAN TEST"
                )
            )
        ).scalar_one_or_none()

        if not test_method:
            db.add(
                PaymentMethod(
                    name="طريقة دفع تجريبية AMAN TEST",
                    account_name="AMAN TEST",
                    account_number="000000000",
                    instructions="طريقة اختبار فقط — عطّلها من الإدارة قبل الإطلاق التجاري.",
                    proof_required=False,
                    is_active=True,
                    sort_order=999,
                )
            )
            await db.commit()


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    log.exception(
        "Unhandled Telegram error",
        exc_info=context.error,
    )

    try:
        if getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "⚠️ حدث خطأ غير متوقع. حاول مرة أخرى أو أرسل /start."
            )
    except Exception:
        pass


async def main_async():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    # IMPORTANT:
    # Run database migrations BEFORE accessing/creating reference data.
    log.info("Running database migrations...")
    await asyncio.to_thread(run_migrations)
    log.info("Database migrations completed.")

    await initialize_reference_data()

    app = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .build()
    )

    app.add_error_handler(error_handler)

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_router,
        )
    )

    scheduler = SchedulerService(app.bot)
    health = await run_health_server()

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        drop_pending_updates=True
    )

    scheduler.start()

    log.info("AMAN started")

    try:
        await asyncio.Event().wait()

    finally:
        await scheduler.stop()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await health.cleanup()
        await close_db()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
