# main.py
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from app.config import settings
from app.database import engine, Base
from app.models import Customer, PhoneNumber

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"مرحباً بك يا {user.first_name} في منصة **أمان (AMAN)** لحماية الأرقام.\n"
        "النظام يعمل بكفاءة وجاهز لخدمتك.\n\n"
        "استخدم الأمر /protect لبدء حماية رقم هاتفك."
    )

async def request_phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض زر للمستخدم لمشاركة رقم هاتفه"""
    keyboard = [[KeyboardButton("📱 مشاركة رقم الهاتف للحماية", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "حتى نتمكن من حماية رقمك وإضافته إلى نظام أمان، يرجى الضغط على الزر أدناه لمشاركة رقم هاتفك:",
        reply_markup=reply_markup
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رقم الهاتف ومعالجته"""
    contact = update.message.contact
    if contact:
        phone_number = contact.phone_number
        user_id = contact.user_id
        first_name = contact.first_name or "مستخدم"
        
        logger.info/("تم استلام رقم هاتف جديد من المستخدم %s: %s", user_id, phone_number)
        
        await update.message.reply_text(
            f"تم استقبال رقمك بنجاح: {phone_number}\nتمت إضافتك إلى نظام أمان وحماية رقمك بنجاح!"
        )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("تم تهيئة وعمل جداول قاعدة البيانات بنجاح.")

async def main_async():
    if not settings.BOT_TOKEN:
        logger.error("خطأ: لم يتم تعيين رمز البوت BOT_TOKEN.")
        return

    await init_db()

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    
    # تسجيل الأوامر والمعالجات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("protect", request_phone_handler))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    logger.info("جاري تشغيل بوت أمان...")
    
    # التشغيل بالطريقة غير المتزامنة وتجاهل الطلبات القديمة لمنع خطأ 409 Conflict
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    # الحفاظ على تشغيل البوت
    stop_event = asyncio.Event()
    await stop_event.wait()

def main():
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("تم إيقاف البوت.")

if __name__ == "__main__":
    main()
