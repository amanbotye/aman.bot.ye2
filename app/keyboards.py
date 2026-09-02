from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

def kb(rows): return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)
def customer_home(): return kb([["🛡️ حماية رقم","📱 أرقامي"],["👤 حسابي","💬 الدعم"],["❓ المساعدة"]])
def admin_home(permissions=None, sandbox=False):
    p=permissions or {"*"}
    if "*" in p:
        rows=[["📊 لوحة التحكم","👥 العملاء"],["📱 الأرقام","💳 الاشتراكات"],["💰 المدفوعات","🔄 المتابعات"],["💬 الدعم","🔔 الإشعارات"],["📈 التقارير","❓ الأسئلة الشائعة"],["⚙️ الإعدادات","🧪 وضع الاختبار"],["📋 سجل العمليات","👤 وضع العميل"]]
    else:
        mapping={"read":"📊 لوحة التحكم","customers.read":"👥 العملاء","phones.read":"📱 الأرقام","subscriptions.read":"💳 الاشتراكات","payments.read":"💰 المدفوعات","followups.read":"🔄 المتابعات","support.read":"💬 الدعم","notifications.read":"🔔 الإشعارات","reports.read":"📈 التقارير","faq.read":"❓ الأسئلة الشائعة","settings.read":"⚙️ الإعدادات","audit.read":"📋 سجل العمليات","sandbox":"🧪 وضع الاختبار"}
        allowed=[mapping[x] for x in p if x in mapping]
        if "customers.edit" in p: allowed.append("👤 وضع العميل")
        rows=[allowed[i:i+2] for i in range(0,len(allowed),2)]
    if sandbox: rows.append(["🧪 الخروج من الاختبار"])
    return kb(rows or [["📊 لوحة التحكم"]])
def back_home(): return kb([["🔙 رجوع","🏠 الرئيسية"]])
def confirm(): return kb([["✅ تأكيد الرقم","✏️ تعديل الرقم"],["🔙 رجوع","🏠 الرئيسية"]])
def phone_actions(): return kb([["🛡️ تفعيل الحماية"],["📱 أرقامي","🏠 الرئيسية"]])
def remove(): return ReplyKeyboardRemove()
