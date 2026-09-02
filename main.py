# main.py

import asyncio
import logging

from sqlalchemy import select

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal

from app.models import (
    Customer,
    TelecomCompany,
)

from app.states import CustomerState

from app.keyboards import (
    customer_main_menu,
    cancel_keyboard,
    companies_keyboard,
    phone_confirmation_keyboard,
    phone_registered_keyboard,
)

from app.customer_service import (
    get_or_create_customer,
    seed_default_companies,
    get_active_companies,
    register_phone,
    get_customer_numbers,
    get_customer_number_count,
    get_customer_protected_count,
)

from app.utils import (
    normalize_phone,
    is_valid_yemeni_phone,
    normalize_name,
    is_valid_full_name,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

async def init_db():
    """
    تهيئة قاعدة البيانات وإضافة شركات الاتصالات الافتراضية.
    """

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed_default_companies(db)

    logger.info("تم تهيئة قاعدة البيانات بنجاح.")


# =========================================================
# /start
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    الصفحة الرئيسية.
    """

    if not update.effective_user or not update.message:
        return

    context.user_data.clear()

    user = update.effective_user

    async with AsyncSessionLocal() as db:
        customer = await get_or_create_customer(
            db,
            user,
        )

    welcome_name = customer.full_name or user.first_name or "بك"

    await update.message.reply_text(
        f"مرحباً بك {welcome_name} 👋\n\n"
        "🛡️ أهلاً بك في أمان AMAN.\n"
        "خدمة تساعدك على حماية أرقامك وإدارتها بسهولة.\n\n"
        "اختر الخدمة التي تريدها من القائمة:",
        reply_markup=customer_main_menu(),
    )


# =========================================================
# START PROTECTION
# =========================================================

async def start_protection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    بدء رحلة حماية رقم.
    """

    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user = update.effective_user

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            user,
        )

        companies = await get_active_companies(db)

    context.user_data["customer_id"] = customer.id

    # -----------------------------------------------------
    # الاسم موجود مسبقًا
    # -----------------------------------------------------

    if customer.full_name:

        context.user_data["customer_name"] = customer.full_name

        if not companies:

            await update.message.reply_text(
                "⚠️ لا توجد شركات اتصالات متاحة حاليًا.\n"
                "يرجى المحاولة لاحقًا.",
                reply_markup=customer_main_menu(),
            )

            return ConversationHandler.END

        await update.message.reply_text(
            "📡 اختر شركة الاتصالات:",
            reply_markup=companies_keyboard(companies),
        )

        return CustomerState.COMPANY_SELECTION

    # -----------------------------------------------------
    # الاسم غير موجود
    # -----------------------------------------------------

    await update.message.reply_text(
        "نحتاج اسمك الكامل مرة واحدة فقط "
        "لربط أرقامك بحسابك.\n\n"
        "✍️ اكتب اسمك الكامل:",
        reply_markup=cancel_keyboard(),
    )

    return CustomerState.NAME_INPUT


# =========================================================
# RECEIVE NAME
# =========================================================

async def receive_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    استقبال الاسم.
    """

    if not update.message:
        return CustomerState.NAME_INPUT

    text = (update.message.text or "").strip()

    # -----------------------------------------------------
    # الرجوع
    # -----------------------------------------------------

    if text == "🔙 رجوع" or text == "🔙 إلغاء":

        return await cancel_text_flow(
            update,
            context,
        )

    # -----------------------------------------------------
    # تجاهل أزرار القائمة أثناء الإدخال
    # -----------------------------------------------------

    if text in {
        "🛡️ حماية رقم",
        "📱 أرقامي",
        "👤 حسابي",
        "💬 الدعم",
        "❓ المساعدة",
    }:

        await update.message.reply_text(
            "⚠️ أنت الآن في خطوة إدخال الاسم.\n\n"
            "✍️ اكتب اسمك الكامل أو اضغط «🔙 رجوع».",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.NAME_INPUT

    name = normalize_name(text)

    if not is_valid_full_name(name):

        await update.message.reply_text(
            "⚠️ يرجى كتابة اسمك الكامل بشكل صحيح.",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.NAME_INPUT

    customer_id = context.user_data.get("customer_id")

    if not customer_id:

        await update.message.reply_text(
            "⚠️ انتهت جلسة العملية.\n"
            "أرسل /start وحاول مرة أخرى.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    async with AsyncSessionLocal() as db:

        customer = await db.get(
            Customer,
            customer_id,
        )

        if not customer:

            await update.message.reply_text(
                "⚠️ تعذر العثور على حسابك.\n"
                "أرسل /start وحاول مرة أخرى.",
                reply_markup=customer_main_menu(),
            )

            return ConversationHandler.END

        customer.full_name = name

        await db.commit()

        companies = await get_active_companies(db)

    context.user_data["customer_name"] = name

    if not companies:

        await update.message.reply_text(
            "⚠️ لا توجد شركات اتصالات متاحة حاليًا.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    await update.message.reply_text(
        "✅ تم حفظ اسمك.\n\n"
        "📡 الآن اختر شركة الاتصالات:",
        reply_markup=companies_keyboard(companies),
    )

    return CustomerState.COMPANY_SELECTION


# =========================================================
# RECEIVE COMPANY
# =========================================================

async def receive_company(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    استقبال شركة الاتصالات.
    """

    if not update.message:
        return CustomerState.COMPANY_SELECTION

    text = (update.message.text or "").strip()

    # -----------------------------------------------------
    # الرجوع
    # -----------------------------------------------------

    if text == "🔙 رجوع" or text == "🔙 إلغاء":

        context.user_data.clear()

        await update.message.reply_text(
            "تم الرجوع إلى القائمة الرئيسية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    # -----------------------------------------------------
    # التحقق من الشركة
    # -----------------------------------------------------

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(TelecomCompany).where(
                TelecomCompany.name == text,
                TelecomCompany.is_active.is_(True),
            )
        )

        company = result.scalar_one_or_none()

    if not company:

        async with AsyncSessionLocal() as db:
            companies = await get_active_companies(db)

        await update.message.reply_text(
            "⚠️ اختر شركة من الأزرار الموجودة أمامك.",
            reply_markup=companies_keyboard(companies),
        )

        return CustomerState.COMPANY_SELECTION

    context.user_data["company_id"] = company.id
    context.user_data["company_name"] = company.name

    await update.message.reply_text(
        f"📡 شركة الاتصالات: {company.name}\n\n"
        "✍️ اكتب رقم الهاتف الذي تريد حمايته.\n\n"
        "يمكنك كتابته بأي من الصيغ التالية:\n"
        "• 771234567\n"
        "• 967771234567\n"
        "• +967771234567\n\n"
        "⚠️ اكتب الرقم يدويًا، ولا ترسل جهة اتصال.",
        reply_markup=cancel_keyboard(),
    )

    return CustomerState.PHONE_INPUT


# =========================================================
# RECEIVE PHONE
# =========================================================

async def receive_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    استقبال رقم الهاتف والتحقق منه.
    """

    if not update.message:
        return CustomerState.PHONE_INPUT

    text = (update.message.text or "").strip()

    # -----------------------------------------------------
    # الرجوع
    # -----------------------------------------------------

    if text == "🔙 رجوع" or text == "🔙 إلغاء":

        context.user_data.clear()

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    # -----------------------------------------------------
    # منع استخدام أزرار القائمة أثناء إدخال الرقم
    # -----------------------------------------------------

    if text in {
        "🛡️ حماية رقم",
        "📱 أرقامي",
        "👤 حسابي",
        "💬 الدعم",
        "❓ المساعدة",
    }:

        await update.message.reply_text(
            "⚠️ أنت الآن في خطوة إدخال الرقم.\n\n"
            "✍️ اكتب رقم الهاتف أو اضغط «🔙 رجوع».",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.PHONE_INPUT

    phone = normalize_phone(text)

    if not is_valid_yemeni_phone(phone):

        await update.message.reply_text(
            "❌ رقم الهاتف غير صحيح.\n\n"
            "أدخل رقم جوال يمني مكونًا من 9 أرقام "
            "ويبدأ بـ 7.\n\n"
            "مثال:\n"
            "771234567",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.PHONE_INPUT

    customer_id = context.user_data.get("customer_id")
    company_id = context.user_data.get("company_id")

    if not customer_id or not company_id:

        await update.message.reply_text(
            "⚠️ انتهت جلسة العملية.\n"
            "أرسل /start وحاول مرة أخرى.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    context.user_data["pending_phone"] = phone

    await update.message.reply_text(
        "📱 الرقم الذي أدخلته:\n\n"
        f"{phone}\n\n"
        "هل الرقم صحيح؟",
        reply_markup=phone_confirmation_keyboard(),
    )

    return CustomerState.PHONE_CONFIRMATION


# =========================================================
# CONFIRM PHONE
# =========================================================

async def confirm_phone_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    تأكيد الرقم باستخدام Reply Keyboard.
    """

    if not update.message:
        return CustomerState.PHONE_CONFIRMATION

    text = (update.message.text or "").strip()

    customer_id = context.user_data.get("customer_id")
    company_id = context.user_data.get("company_id")
    phone_number = context.user_data.get("pending_phone")

    # -----------------------------------------------------
    # تعديل الرقم
    # -----------------------------------------------------

    if text == "✏️ تعديل الرقم":

        await update.message.reply_text(
            "✏️ اكتب رقم الهاتف الصحيح:",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.PHONE_INPUT

    # -----------------------------------------------------
    # إلغاء
    # -----------------------------------------------------

    if text == "🔙 رجوع" or text == "🔙 إلغاء":

        context.user_data.clear()

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    # -----------------------------------------------------
    # تأكيد
    # -----------------------------------------------------

    if text != "✅ تأكيد الرقم":

        await update.message.reply_text(
            "⚠️ اختر أحد الخيارات من الأزرار.",
            reply_markup=phone_confirmation_keyboard(),
        )

        return CustomerState.PHONE_CONFIRMATION

    if not customer_id or not company_id or not phone_number:

        await update.message.reply_text(
            "⚠️ انتهت جلسة العملية.\n"
            "أرسل /start وحاول مرة أخرى.",
            reply_markup=customer_main_menu(),
        )

        context.user_data.clear()

        return ConversationHandler.END

    async with AsyncSessionLocal() as db:

        customer = await db.get(
            Customer,
            customer_id,
        )

        company = await db.get(
            TelecomCompany,
            company_id,
        )

        if not customer or not company:

            await update.message.reply_text(
                "⚠️ تعذر إكمال العملية.",
                reply_markup=customer_main_menu(),
            )

            context.user_data.clear()

            return ConversationHandler.END

        phone, result = await register_phone(
            db,
            customer,
            company,
            phone_number,
        )

    context.user_data.pop(
        "pending_phone",
        None,
    )

    # -----------------------------------------------------
    # الرقم ملك مستخدم آخر
    # -----------------------------------------------------

    if result == "owned_by_other":

        await update.message.reply_text(
            "❌ لا يمكن تسجيل هذا الرقم.\n\n"
            "هذا الرقم مرتبط بحساب آخر.",
            reply_markup=customer_main_menu(),
        )

        context.user_data.clear()

        return ConversationHandler.END

    # -----------------------------------------------------
    # الرقم موجود مسبقًا
    # -----------------------------------------------------

    if result == "owned":

        await update.message.reply_text(
            "ℹ️ هذا الرقم مسجل لديك بالفعل.\n\n"
            f"📱 الرقم: {phone_number}\n\n"
            "يمكنك إدارة الرقم من قسم «📱 أرقامي».",
            reply_markup=customer_main_menu(),
        )

        context.user_data.clear()

        return ConversationHandler.END

    # -----------------------------------------------------
    # رقم جديد
    # -----------------------------------------------------

    await update.message.reply_text(
        "✅ تم تسجيل الرقم بنجاح.\n\n"
        f"📱 الرقم: {phone_number}\n"
        f"📡 الشركة: {company.name}\n\n"
        "حالة الحماية الحالية:\n"
        "🟡 الحماية غير مفعلة.",
        reply_markup=phone_registered_keyboard(),
    )

    context.user_data["phone_id"] = phone.id
    context.user_data["customer_id"] = customer.id

    return ConversationHandler.END


# =========================================================
# MY NUMBERS
# =========================================================

async def send_my_numbers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    عرض أرقام العميل.
    """

    if not update.effective_user or not update.message:
        return

    user = update.effective_user

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            user,
        )

        numbers = await get_customer_numbers(
            db,
            customer.id,
        )

    if not numbers:

        await update.message.reply_text(
            "📱 أرقامك\n\n"
            "لا توجد أرقام مسجلة في حسابك حتى الآن.\n\n"
            "اضغط «🛡️ حماية رقم» لإضافة رقم.",
            reply_markup=customer_main_menu(),
        )

        return

    lines = ["📱 أرقامك:\n"]

    for index, phone in enumerate(
        numbers,
        start=1,
    ):

        company_name = (
            phone.telecom_company.name
            if phone.telecom_company
            else "غير محدد"
        )

        if phone.status.value == "active":
            status = "🟢 الحماية مفعلة"

        elif phone.status.value == "inactive":
            status = "🟡 الحماية غير مفعلة"

        elif phone.status.value == "suspended":
            status = "🟠 موقوفة"

        else:
            status = "⚫ ملغاة"

        lines.append(
            f"{index}. 📱 {phone.phone_number}\n"
            f"   📡 {company_name}\n"
            f"   {status}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=customer_main_menu(),
    )


# =========================================================
# ACCOUNT
# =========================================================

async def account_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    حساب العميل.
    """

    if not update.effective_user or not update.message:
        return

    user = update.effective_user

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            user,
        )

        total = await get_customer_number_count(
            db,
            customer.id,
        )

        protected = await get_customer_protected_count(
            db,
            customer.id,
        )

    name = customer.full_name or "غير مسجل"

    username = (
        f"@{customer.telegram_username}"
        if customer.telegram_username
        else "غير متوفر"
    )

    await update.message.reply_text(
        "👤 حسابي\n\n"
        f"الاسم: {name}\n"
        f"المستخدم: {username}\n\n"
        f"📱 عدد الأرقام: {total}\n"
        f"🛡️ الأرقام المحمية: {protected}",
        reply_markup=customer_main_menu(),
    )


# =========================================================
# HELP
# =========================================================

async def help_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    المساعدة.
    """

    if not update.message:
        return

    await update.message.reply_text(
        "❓ المساعدة\n\n"
        "🛡️ حماية رقم\n"
        "إضافة رقم جديد إلى حسابك وطلب تفعيل الحماية.\n\n"
        "📱 أرقامي\n"
        "عرض الأرقام المرتبطة بحسابك وحالة الحماية.\n\n"
        "👤 حسابي\n"
        "عرض معلومات حسابك.\n\n"
        "💬 الدعم\n"
        "للتواصل مع فريق أمان.\n\n"
        "إذا واجهتك مشكلة، يمكنك التواصل مع الدعم.",
        reply_markup=customer_main_menu(),
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    الدعم - مؤقت حتى تركيب النظام الكامل.
    """

    if not update.message:
        return

    await update.message.reply_text(
        "💬 الدعم\n\n"
        "سيتم تجهيز نظام الدعم الكامل في المرحلة التالية.",
        reply_markup=customer_main_menu(),
    )


# =========================================================
# ACTIVATE PROTECTION
# =========================================================

async def activate_protection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    الانتقال إلى تفعيل الحماية.
    """

    if not update.message:
        return

    await update.message.reply_text(
        "🛡️ تفعيل الحماية\n\n"
        "سيتم الآن الانتقال إلى خطوات الدفع "
        "وتفعيل الاشتراك.",
        reply_markup=customer_main_menu(),
    )


# =========================================================
# MAIN MENU
# =========================================================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    القائمة الرئيسية.
    """

    if not update.message:
        return

    text = (update.message.text or "").strip()

    if text == "📱 أرقامي":

        await send_my_numbers(
            update,
            context,
        )

    elif text == "👤 حسابي":

        await account_handler(
            update,
            context,
        )

    elif text == "❓ المساعدة":

        await help_handler(
            update,
            context,
        )

    elif text == "💬 الدعم":

        await support_handler(
            update,
            context,
        )

    elif text == "🛡️ تفعيل الحماية":

        await activate_protection(
            update,
            context,
        )

    else:

        await update.message.reply_text(
            "اختر إحدى الخدمات من القائمة:",
            reply_markup=customer_main_menu(),
        )


# =========================================================
# CANCEL TEXT FLOW
# =========================================================

async def cancel_text_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    إلغاء أي مرحلة نصية.
    """

    context.user_data.clear()

    if update.message:

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

    return ConversationHandler.END


# =========================================================
# MAIN
# =========================================================

async def main_async():

    if not settings.BOT_TOKEN:

        logger.error(
            "❌ BOT_TOKEN غير موجود."
        )

        return

    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    await init_db()

    # -----------------------------------------------------
    # Telegram Application
    # -----------------------------------------------------

    application = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .build()
    )

    # =====================================================
    # حماية رقم
    # =====================================================

    protection_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(r"^🛡️ حماية رقم$"),
                start_protection,
            )
        ],

        states={

            # -------------------------------------------------
            # الاسم
            # -------------------------------------------------

            CustomerState.NAME_INPUT: [

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_name,
                ),
            ],

            # -------------------------------------------------
            # الشركة
            # -------------------------------------------------

            CustomerState.COMPANY_SELECTION: [

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_company,
                ),
            ],

            # -------------------------------------------------
            # الرقم
            # -------------------------------------------------

            CustomerState.PHONE_INPUT: [

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_phone,
                ),
            ],

            # -------------------------------------------------
            # تأكيد الرقم
            # -------------------------------------------------

            CustomerState.PHONE_CONFIRMATION: [

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    confirm_phone_text,
                ),
            ],
        },

        fallbacks=[

            CommandHandler(
                "start",
                start_command,
            ),

            MessageHandler(
                filters.Regex(r"^🔙 (إلغاء|رجوع)$"),
                cancel_text_flow,
            ),
        ],

        allow_reentry=True,

    )

    # =====================================================
    # /start
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    # =====================================================
    # حماية رقم
    # =====================================================

    application.add_handler(
        protection_conversation
    )

    # =====================================================
    # القائمة الرئيسية
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_handler,
        )
    )

    # =====================================================
    # التشغيل
    # =====================================================

    logger.info(
        "🚀 بوت أمان AMAN يعمل الآن..."
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        drop_pending_updates=True
    )

    stop_event = asyncio.Event()

    try:

        await stop_event.wait()

    finally:

        await application.updater.stop()
        await application.stop()
        await application.shutdown()


# =========================================================
# ENTRY POINT
# =========================================================

def main():

    try:

        asyncio.run(
            main_async()
        )

    except (
        KeyboardInterrupt,
        SystemExit,
    ):

        logger.info(
            "تم إيقاف بوت أمان."
        )


if __name__ == "__main__":
    main()
