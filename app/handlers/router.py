from telegram import Update
from telegram.ext import ContextTypes
from app.database import SessionLocal
from app.states import State
from app.services.session_service import load
from app.services.admin_service import is_admin
from app.customer.flow import customer_start, protect_start, handle_state, my_numbers, activate_start, account, support, help_customer
from app.admin.flow import admin_entry, dashboard_handler, payments, admin_state, section, admin_extended_state

CUSTOMER_BUTTONS={'🛡️ حماية رقم':protect_start,'📱 أرقامي':my_numbers,'👤 حسابي':account,'💬 الدعم':support,'❓ المساعدة':help_customer,'🛡️ تفعيل الحماية':activate_start,'🏠 الرئيسية':customer_start}
ADMIN_BUTTONS={'🏠 لوحة التحكم':dashboard_handler,'💳 المدفوعات':payments,'👥 العملاء':lambda u,c:section(u,c,'customers'),'📱 الأرقام':lambda u,c:section(u,c,'numbers'),'🛡️ الاشتراكات':lambda u,c:section(u,c,'subscriptions'),'🔄 المتابعة':lambda u,c:section(u,c,'followups'),'💬 الدعم':lambda u,c:section(u,c,'support'),'🔔 الإشعارات':lambda u,c:section(u,c,'notifications'),'📊 التقارير':lambda u,c:section(u,c,'reports'),'❓ الأسئلة الشائعة':lambda u,c:section(u,c,'faq'),'⚙️ الإعدادات':lambda u,c:section(u,c,'settings'),'🧾 سجل العمليات':lambda u,c:section(u,c,'audit')}

async def start(update,context):
    async with SessionLocal() as db: admin=await is_admin(db,update.effective_user.id)
    if admin: await admin_entry(update,context)
    else: await customer_start(update,context)

async def message_router(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:return
    uid=update.effective_user.id
    async with SessionLocal() as db: state,data=await load(db,uid); admin=await is_admin(db,uid)
    text=(update.message.text or '').strip()
    if admin:
        if text in ADMIN_BUTTONS:return await ADMIN_BUTTONS[text](update,context)
        if text.startswith(('✅ قبول ','❌ رفض ')):return await admin_state(update,context,state or State.ADMIN_MENU,data)
        if state and str(state).startswith('admin_'):
            if state in (State.ADMIN_SETTINGS_VALUE,State.ADMIN_SETTINGS_CONFIRM,State.ADMIN_TICKET_SELECT,State.ADMIN_TICKET_REPLY): return await admin_extended_state(update,context,state,data)
            return await admin_state(update,context,state,data)
    if text in CUSTOMER_BUTTONS and (not state or state==State.IDLE):return await CUSTOMER_BUTTONS[text](update,context)
    if state and state!=State.IDLE:return await handle_state(update,context,state,data)
    await update.message.reply_text('اختر إحدى الخدمات من القائمة:',reply_markup=__import__('app.keyboards',fromlist=['customer_main_menu']).customer_main_menu())
