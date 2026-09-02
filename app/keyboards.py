# app/keyboards.py

from telegram import ReplyKeyboardMarkup


# =========================================================
# القائمة الرئيسية
# =========================================================

def customer_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🛡️ حماية رقم"],
            ["📱 أرقامي", "👤 حسابي"],
            ["💬 الدعم", "❓ المساعدة"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================================================
# زر الرجوع
# =========================================================

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🔙 رجوع"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================================================
# شركات الاتصالات
# =========================================================

def companies_keyboard(companies) -> ReplyKeyboardMarkup:
    rows = []
    current_row = []

    for company in companies:

        current_row.append(company.name)

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(["🔙 رجوع"])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================================================
# تأكيد الرقم
# =========================================================

def phone_confirmation_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["✅ تأكيد الرقم"],
            ["✏️ تعديل الرقم"],
            ["🔙 رجوع"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# =========================================================
# بعد تسجيل الرقم
# =========================================================

def phone_registered_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🛡️ تفعيل الحماية"],
            ["📱 أرقامي"],
            ["🏠 الرئيسية"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
