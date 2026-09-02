import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from sqlalchemy import select

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
    phone_registered_keyboard,
    phone_confirmation_keyboard,
)

from app.utils import (
    normalize_phone,
    is_valid_yemeni_phone,
    normalize_name,
    is_valid_full_name,
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


logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger("AMAN")


# ============================================================
# DATABASE
# ============================================================

async def init_db():
    """
    إنشاء الجداول الموجودة في Models فقط إذا لم تكن موجودة.
    لا يحذف أي بيانات.
    """

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    async with AsyncSessionLocal() as db:
        await seed_default_companies(db)

    logger.info(
        "AMAN database initialization completed."
    )


# ============================================================
# START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # بدء نظيف لأي رحلة سابقة
    context.user_data.clear()

    user = update.effective_user

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            user,
        )

    display_name = (
        customer.full_name
        or user.first_name
        or "صديقنا"
    )

    await update.message.reply_text(
        f"مرحبًا {display_name} 👋\n\n"
        "أهلًا بك في **أمان AMAN** 🛡️\n\n"
        "خدمة تساعدك على حماية أرقامك "
        "ومتابعة اشتراكاتك بسهولة.\n\n"
        "اختر الخدمة التي تريدها:",
        parse_mode="Markdown",
        reply_markup=customer_main_menu(),
    )

    return ConversationHandler.END


# ============================================================
# PROTECT NUMBER
# ============================================================

async def protect_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            update.effective_user,
        )

        context.user_data["customer_id"] = customer.id

        if not customer.full_name:

            await update.message.reply_text(
                "نحتاج اسمك الكامل مرة واحدة فقط "
                "لربط أرقامك بحسابك.\n\n"
                "✍️ اكتب اسمك الكامل:",
                reply_markup=cancel_keyboard(),
            )

            return CustomerState.NAME_INPUT

        companies = await get_active_companies(db)

    if not companies:

        await update.message.reply_text(
            "⚠️ لا توجد شركات اتصالات متاحة حاليًا.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    await update.message.reply_text(
        "🏢 اختر شركة الاتصالات الخاصة بالرقم:",
        reply_markup=companies_keyboard(
            companies
        ),
    )

    return CustomerState.COMPANY_SELECTION


# ============================================================
# NAME
# ============================================================

async def receive_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    name = normalize_name(
        update.message.text
    )

    if name == "🔙 إلغاء":

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    if not is_valid_full_name(name):

        await update.message.reply_text(
            "❌ يرجى كتابة اسمك بشكل صحيح.",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.NAME_INPUT

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(Customer).where(
                Customer.telegram_id
                == update.effective_user.id
            )
        )

        customer = result.scalar_one_or_none()

        if customer is None:

            await update.message.reply_text(
                "⚠️ حدث خطأ في الحساب. "
                "أرسل /start وحاول مرة أخرى.",
                reply_markup=customer_main_menu(),
            )

            return ConversationHandler.END

        customer.full_name = name

        await db.commit()

        companies = await get_active_companies(db)

    await update.message.reply_text(
        "✅ تم حفظ اسمك.\n\n"
        "الآن اختر شركة الاتصالات:",
        reply_markup=companies_keyboard(
            companies
        ),
    )

    return CustomerState.COMPANY_SELECTION


# ============================================================
# COMPANY
# ============================================================

async def receive_company(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    company_name = (
        update.message.text.strip()
    )

    if company_name == "🔙 إلغاء":

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(TelecomCompany).where(
                TelecomCompany.name
                == company_name,
                TelecomCompany.is_active.is_(True),
            )
        )

        company = result.scalar_one_or_none()

    if company is None:

        async with AsyncSessionLocal() as db:
            companies = await get_active_companies(
                db
            )

        await update.message.reply_text(
            "❌ يرجى اختيار شركة من القائمة.",
            reply_markup=companies_keyboard(
                companies
            ),
        )

        return CustomerState.COMPANY_SELECTION

    context.user_data[
        "company_id"
    ] = company.id

    context.user_data[
        "company_name"
    ] = company.name

    await update.message.reply_text(
        "📱 اكتب رقم الهاتف الذي تريد حمايته.\n\n"
        "يمكنك كتابته مثل:\n"
        "`771234567`\n"
        "أو:\n"
        "`+967771234567`\n\n"
        "لا تستخدم زر مشاركة جهة الاتصال.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    return CustomerState.PHONE_INPUT


# ============================================================
# PHONE
# ============================================================

async def receive_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    raw_phone = update.message.text.strip()

    if raw_phone == "🔙 إلغاء":

        await update.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return ConversationHandler.END

    phone = normalize_phone(
        raw_phone
    )

    if not is_valid_yemeni_phone(phone):

        await update.message.reply_text(
            "❌ رقم الهاتف غير صحيح.\n\n"
            "أدخل رقمًا يمنيًا صحيحًا، مثل:\n"
            "771234567",
            reply_markup=cancel_keyboard(),
        )

        return CustomerState.PHONE_INPUT

    context.user_data[
        "phone_number"
    ] = phone

    await update.message.reply_text(
        "📱 تأكيد الرقم\n\n"
        f"الرقم: `{phone}`\n"
        f"الشركة: {context.user_data['company_name']}\n\n"
        "هل البيانات صحيحة؟",
        parse_mode="Markdown",
        reply_markup=phone_confirmation_keyboard(),
    )

    return CustomerState.PHONE_CONFIRMATION


# ============================================================
# CALLBACKS
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    action = query.data

    # --------------------------------------------------------
    # CONFIRM PHONE
    # --------------------------------------------------------

    if action == "confirm_phone":

        phone = context.user_data.get(
            "phone_number"
        )

        company_id = context.user_data.get(
            "company_id"
        )

        customer_id = context.user_data.get(
            "customer_id"
        )

        if not phone or not company_id or not customer_id:

            await query.message.reply_text(
                "⚠️ انتهت صلاحية العملية.\n"
                "اضغط «🛡️ حماية رقم» وابدأ من جديد.",
                reply_markup=customer_main_menu(),
            )

            return

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

                await query.message.reply_text(
                    "⚠️ تعذر إكمال العملية.",
                    reply_markup=customer_main_menu(),
                )

                return

            phone_obj, result = await register_phone(
                db,
                customer,
                company,
                phone,
            )

        context.user_data.clear()

        if result == "owned_by_other":

            await query.message.reply_text(
                "❌ لا يمكن تسجيل هذا الرقم.\n\n"
                "هذا الرقم مرتبط بحساب آخر.",
                reply_markup=customer_main_menu(),
            )

            return

        if result == "owned":

            await query.message.reply_text(
                "ℹ️ هذا الرقم مسجل بالفعل في حسابك.\n\n"
                f"📱 {phone}\n"
                f"🏢 {company.name}",
                reply_markup=customer_main_menu(),
            )

            return

        await query.message.reply_text(
            "✅ تم تسجيل الرقم بنجاح.\n\n"
            f"📱 الرقم: {phone}\n"
            f"🏢 الشركة: {company.name}\n\n"
            "يمكنك الآن بدء إجراءات تفعيل الحماية.",
            reply_markup=phone_registered_keyboard(),
        )

        return

    # --------------------------------------------------------
    # EDIT PHONE
    # --------------------------------------------------------

    if action == "edit_phone":

        context.user_data.pop(
            "phone_number",
            None,
        )

        await query.message.reply_text(
            "✏️ اكتب الرقم الصحيح:",
            reply_markup=cancel_keyboard(),
        )

        return

    # --------------------------------------------------------
    # CANCEL
    # --------------------------------------------------------

    if action == "cancel_phone":

        context.user_data.clear()

        await query.message.reply_text(
            "تم إلغاء العملية.",
            reply_markup=customer_main_menu(),
        )

        return

    # --------------------------------------------------------
    # MY NUMBERS
    # --------------------------------------------------------

    if action == "my_numbers":

        await send_my_numbers(
            query.message,
            query.from_user,
        )

        return

    # --------------------------------------------------------
    # ACTIVATE PROTECTION
    # --------------------------------------------------------

    if action == "activate_protection":

        await query.message.reply_text(
            "💳 سننتقل إلى خطوات الدفع وتفعيل الحماية "
            "في المرحلة التالية.",
            reply_markup=customer_main_menu(),
        )

        return


# ============================================================
# MY NUMBERS
# ============================================================

async def send_my_numbers(
    message,
    telegram_user,
):

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            telegram_user,
        )

        numbers = await get_customer_numbers(
            db,
            customer.id,
        )

    if not numbers:

        await message.reply_text(
            "📱 لا توجد أرقام مسجلة في حسابك حاليًا.\n\n"
            "اضغط «🛡️ حماية رقم» لإضافة رقم.",
            reply_markup=customer_main_menu(),
        )

        return

    text = "📱 **أرقامك**\n\n"

    async with AsyncSessionLocal() as db:

        for number in numbers:

            company = await db.get(
                TelecomCompany,
                number.telecom_company_id,
            )

            company_name = (
                company.name
                if company
                else "غير محدد"
            )

            status = (
                "🟢 الحماية مفعلة"
                if number.status.value == "active"
                else "🟡 الحماية غير مفعلة"
            )

            text += (
                f"📱 `{number.phone_number}`\n"
                f"🏢 {company_name}\n"
                f"{status}\n\n"
            )

    await message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=customer_main_menu(),
    )


# ============================================================
# ACCOUNT
# ============================================================

async def account_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    async with AsyncSessionLocal() as db:

        customer = await get_or_create_customer(
            db,
            update.effective_user,
        )

        total = await get_customer_number_count(
            db,
            customer.id,
        )

        protected = await get_customer_protected_count(
            db,
            customer.id,
        )

    username = (
        f"@{customer.telegram_username}"
        if customer.telegram_username
        else "غير مضاف"
    )

    await update.message.reply_text(
        "👤 **حسابي**\n\n"
        f"الاسم: {customer.full_name or 'غير مسجل'}\n"
        f"المستخدم: {username}\n"
        f"عدد الأرقام: {total}\n"
        f"الأرقام المحمية: {protected}",
        parse_mode="Markdown",
        reply_markup=customer_main_menu(),
    )


# ============================================================
# HELP
# ============================================================

async def help_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "❓ **المساعدة**\n\n"
        "🛡️ حماية رقم\n"
        "تسجيل رقم جديد وبدء إجراءات حمايته.\n\n"
        "📱 أرقامي\n"
        "عرض أرقامك وحالة الحماية.\n\n"
        "👤 حسابي\n"
        "عرض معلومات حسابك.\n\n"
        "💬 الدعم\n"
        "سيتم تفعيل نظام الدعم في المرحلة التالية.",
        parse_mode="Markdown",
        reply_markup=customer_main_menu(),
    )


# ============================================================
# GENERAL MENU
# ============================================================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text

    if text == "📱 أرقامي":

        await send_my_numbers(
            update.message,
            update.effective_user,
        )

        return

    if text == "👤 حسابي":

        await account_handler(
            update,
            context,
        )

        return

    if text == "❓ المساعدة":

        await help_handler(
            update,
            context,
        )

        return

    if text == "💬 الدعم":

        await update.message.reply_text(
            "💬 نظام الدعم سيتم تفعيله في المرحلة التالية.",
            reply_markup=customer_main_menu(),
        )

        return

    await update.message.reply_text(
        "اختر إحدى الخدمات من القائمة.",
        reply_markup=customer_main_menu(),
    )


# ============================================================
# MAIN
# ============================================================

async def main_async():

    if not settings.BOT_TOKEN:

        logger.error(
            "BOT_TOKEN غير موجود في Environment Variables."
        )

        return

    await init_db()

    application = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # CUSTOMER PROTECTION FLOW
    # --------------------------------------------------------

    protection_flow = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex("^🛡️ حماية رقم$"),
                protect_start,
            )
        ],

        states={

            CustomerState.NAME_INPUT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_name,
                )
            ],

            CustomerState.COMPANY_SELECTION: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_company,
                )
            ],

            CustomerState.PHONE_INPUT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    receive_phone,
                )
            ],

        },

        fallbacks=[
            CommandHandler(
                "start",
                start_command,
            )
        ],

        allow_reentry=True,
    )

    # --------------------------------------------------------
    # HANDLERS
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        protection_flow
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_handler,
        )
    )

    logger.info(
        "AMAN bot starting..."
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        drop_pending_updates=True
    )

    stop_event = asyncio.Event()

    await stop_event.wait()


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
            "AMAN stopped."
        )


if __name__ == "__main__":
    main()
