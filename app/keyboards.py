from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

def kb(rows): return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)
def customer_main_menu(): return kb([['🛡️ حماية رقم'],['📱 أرقامي','👤 حسابي'],['💬 الدعم','❓ المساعدة']])
def back_menu(): return kb([['🔙 رجوع'],['🏠 الرئيسية']])
def companies_keyboard(items): return kb([[x.name] for x in items]+[['🔙 رجوع','🏠 الرئيسية']])
def phone_confirmation_keyboard(): return kb([['✅ تأكيد الرقم'],['✏️ تعديل الرقم'],['🔙 رجوع']])
def phone_registered_keyboard(): return kb([['🛡️ تفعيل الحماية'],['📱 أرقامي','🏠 الرئيسية']])
def phone_list_keyboard(items, include_back=True):
    rows=[[x] for x in items]
    if include_back: rows.append(['🔙 رجوع','🏠 الرئيسية'])
    return kb(rows)
def payment_methods_keyboard(items): return kb([[x.name] for x in items]+[['🔙 رجوع','🏠 الرئيسية']])
def admin_menu(): return kb([['🏠 لوحة التحكم'],['👥 العملاء','📱 الأرقام'],['💳 المدفوعات','🛡️ الاشتراكات'],['🔄 المتابعة','💬 الدعم'],['🔔 الإشعارات','📊 التقارير'],['❓ الأسئلة الشائعة','⚙️ الإعدادات'],['🧾 سجل العمليات','👤 وضع العميل'],['🧪 Sandbox','🔴 REAL MODE']])
def admin_back(): return kb([['🔙 رجوع','🏠 لوحة التحكم']])
def faq_keyboard(items): return kb([[f'❓ {x.question[:50]}'] for x in items]+[['🔙 رجوع','🏠 الرئيسية']])
def remove(): return ReplyKeyboardRemove()
