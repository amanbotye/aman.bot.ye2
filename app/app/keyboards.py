from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)


# ============================================================
# CUSTOMER MAIN MENU
# ============================================================

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


# ============================================================
# CANCEL
# ============================================================

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🔙 إلغاء"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ============================================================
# TELECOM COMPANIES
# ============================================================

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

    rows.append(["🔙 إلغاء"])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
    )


# ============================================================
# PHONE REGISTRATION RESULT
# ============================================================

def phone_registered_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛡️ تفعيل الحماية الآن",
                    callback_data="activate_protection",
                )
            ],
            [
                InlineKeyboardButton(
                    "📱 الانتقال إلى أرقامي",
                    callback_data="my_numbers",
                )
            ],
        ]
    )


# ============================================================
# CONFIRM PHONE
# ============================================================

def phone_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأكيد الرقم",
                    callback_data="confirm_phone",
                ),
                InlineKeyboardButton(
                    "✏️ تعديل الرقم",
                    callback_data="edit_phone",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔙 إلغاء",
                    callback_data="cancel_phone",
                ),
            ],
        ]
    )
