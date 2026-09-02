import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import settings
from database import engine, Base
from models import UserModel, ProtectedPhoneModel

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"مرحباً بك يا {user.first_name} في منصة **أمان (AMAN)** لحماية الأرقام.\n"
        "النظام يعمل بكفاءة وجاهز لخدمتك."
    )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("تم تهيئة وعمل جداول قاعدة البيانات بنجاح.")

def main():
    if not settings.BOT_TOKEN:
        logger.error("خطأ: لم يتم تعيين رمز البوت BOT_TOKEN.")
        return

    asyncio.run(init_db())

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))

    logger.info("جاري تشغيل بوت أمان...")
    app.run_polling()

if __name__ == "__main__":
    main()
