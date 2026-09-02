from decimal import Decimal
from datetime import timedelta
from telegram import ReplyKeyboardMarkup
from sqlalchemy import select, func, or_, cast, String
from ..models import *
from ..keyboards import admin_home, customer_home, back_home
from ..admin.permissions import role_allows, PERMISSIONS
from ..utils import utcnow, normalize_yemen_phone, money
from ..services.audit_service import AuditService

async def ensure_admin(session, tid):
    return await session.scalar(select(AdminUser).where(AdminUser.telegram_id==tid, AdminUser.active.is_(True)))

def allowed(admin, permission): return bool(admin and role_allows(admin.role, permission))
def menu(*rows): return ReplyKeyboardMarkup([list(r) for r in rows],resize_keyboard=True)

def set_state(context,state,**data): context.user_data.update(data); context.user_data["state"]=state

async def start_admin(update,context,session,services):
    a=await ensure_admin(session,update.effective_user.id)
    if not a:return False
    context.user_data.update(mode="admin",state="IDLE",sandbox=False)
    await update.message.reply_text("🛡️ لوحة إدارة أمان",reply_markup=admin_home(PERMISSIONS[a.role])); return True

async def switch_customer_mode(update,context,session,services):
    a=await ensure_admin(session,update.effective_user.id)
    if not a or not allowed(a,"customers.edit"): raise PermissionError("ليس لديك صلاحية وضع العميل.")
    c=await services["customer"].get_or_create(update.effective_user.id)
    context.user_data.update(mode="customer",state="IDLE",customer_id=c.id)
    await update.message.reply_text("👤 وضع العميل الحقيقي\nأنت تستخدم نفس واجهة العميل. أرسل A أو a للعودة إلى الإدارة.",reply_markup=customer_home())

async def dashboard(session,services=None):
    if services is not None:
        return await services["report"].dashboard(session,services["settings"])
    return {}

async def admin_text(update,context,session,services):
    a=await ensure_admin(session,update.effective_user.id)
    if not a or context.user_data.get("mode")=="customer": return
    text=(update.message.text or "").strip()
    if text=="📊 لوحة التحكم":
        if not allowed(a,"read"): raise PermissionError("لا تملك صلاحية القراءة.")
        v=await dashboard(session,services)
        await update.message.reply_text(f"📊 لوحة التحكم\n\n👥 العملاء: {v['customers_total']} | 🟢 {v['customers_active']} | 🔴 {v['customers_blocked']}\n🆕 اليوم: {v['customers_today']} | الأسبوع: {v['customers_week']}\n📱 الأرقام: {v['phones_total']} | 🛡️ محمية: {v['phones_protected']} | 🟡 غير محمية: {v['phones_unprotected']} | 🟠 قريب: {v['phones_near']} | 🔴 خطر: {v['phones_danger']} | ⚫ منتهية: {v['phones_expired']}\n💳 الاشتراكات: 🟢 {v['subscriptions_safe']} | 🟠 {v['subscriptions_near']} | 🔴 {v['subscriptions_danger']} | ⚫ {v['subscriptions_expired']}\n💰 الدفع: P {v['payments_pending']} | A {v['payments_approved']} | R {v['payments_rejected']}\n💵 اليوم: {v['revenue_today']} | الشهر: {v['revenue_month']}\n💬 الدعم: مفتوح {v['support_new']} | يحتاج رد {v['support_pending']}",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if text=="👤 وضع العميل": await switch_customer_mode(update,context,session,services); return
    if text=="🧪 وضع الاختبار":
        if not allowed(a,"sandbox"): raise PermissionError("ليس لديك صلاحية Sandbox.")
        if not context.application.bot_data.get("sandbox_session_factory"): raise ValueError("SANDBOX_DATABASE_URL غير مهيأ. أنشئ قاعدة PostgreSQL منفصلة وشغّل عليها alembic upgrade head.")
        context.user_data.update(mode="customer",sandbox=True,sandbox_initialized=False,state="IDLE")
        await AuditService().log(session,a.telegram_id,"sandbox_enter","sandbox",a.telegram_id,new={"sandbox":True})
        await update.message.reply_text("🧪 Sandbox مفصول عن Production. أنت الآن داخل واجهة العميل التجريبية. كل البيانات تُحفظ في قاعدة الاختبار فقط. أرسل A للعودة.",reply_markup=customer_home()); return
    actions={
      "👥 العملاء":("customers.read","ADMIN_CUSTOMER_SEARCH","أرسل Telegram ID أو username أو الاسم أو رقم الهاتف."),
      "📱 الأرقام":("phones.read","ADMIN_PHONE_SEARCH","أرسل رقم الهاتف أو اكتب: شركات الاتصالات."),
      "💳 الاشتراكات":("subscriptions.read","ADMIN_SUB_SEARCH","أرسل رقم الاشتراك أو رقم الهاتف."),
      "💰 المدفوعات":("payments.read","ADMIN_PAYMENT_LIST","اختر: المعلقة / الكل / رقم الطلب / طرق الدفع"),
      "🔄 المتابعات":("followups.read","ADMIN_FOLLOWUP_LIST","أرسل رقم المتابعة أو رقم الهاتف، أو اكتب الكل."),
      "💬 الدعم":("support.read","ADMIN_SUPPORT_LIST","أرسل رقم التذكرة أو اكتب الكل."),
      "🔔 الإشعارات":("notifications.read","ADMIN_NOTIFICATION_LIST","اكتب الكل لعرض آخر الإشعارات أو إرسال لإعلان."),
      "📈 التقارير":("reports.read","ADMIN_REPORTS","اكتب اليوم أو الشهر أو فترة بصيغة YYYY-MM-DD YYYY-MM-DD."),
      "❓ الأسئلة الشائعة":("faq.read","ADMIN_FAQ_MENU","اختر: إضافة / تعديل / حذف / تفعيل / تعطيل / ترتيب / عرض"),
      "⚙️ الإعدادات":("settings.read","ADMIN_SETTINGS","اختر إعدادًا من القائمة."),
      "📋 سجل العمليات":("audit.read","ADMIN_AUDIT","اكتب الكل أو نوع العملية."),
      "🧪 وضع الاختبار":("sandbox","ADMIN_SANDBOX",""),
    }
    if text in actions:
        perm,state,prompt=actions[text]
        if not allowed(a,perm): raise PermissionError("ليس لديك الصلاحية لهذا القسم.")
        if state=="ADMIN_PAYMENT_LIST":
            set_state(context,state); await update.message.reply_text(prompt,reply_markup=menu(("المعلقة","الكل"),("🔙 رجوع","🏠 الرئيسية"))); return
        if state=="ADMIN_FAQ_MENU": set_state(context,state); await update.message.reply_text(prompt,reply_markup=menu(("إضافة","تعديل"),("حذف","تفعيل"),("تعطيل","ترتيب"),("عرض",),("🔙 رجوع","🏠 الرئيسية"))); return
        if state=="ADMIN_SETTINGS":
            from ..services.settings_service import DEFAULTS
            set_state(context,state); await update.message.reply_text("⚙️ الإعدادات:\n"+"\n".join(f"{k} = {await services['settings'].get(k)}" for k in DEFAULTS)+"\n\nأرسل اسم الإعداد.",reply_markup=back_home()); return
        set_state(context,state); await update.message.reply_text(prompt or "استخدم الخيارات.",reply_markup=back_home()); return
    await update.message.reply_text("اختر قسمًا من لوحة الإدارة.",reply_markup=admin_home(PERMISSIONS[a.role]))

async def admin_state_router(update,context,session,services):
    a=await ensure_admin(session,update.effective_user.id)
    if not a:return
    text=(update.message.text or "").strip(); state=context.user_data.get("state")
    if text in ("🔙 رجوع","🏠 الرئيسية"):
        context.user_data["state"]="IDLE"; await update.message.reply_text("تم الرجوع.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PAYMENT_LIST" and text=="طرق الدفع":
        if not allowed(a,"payments.read"): raise PermissionError("ليس لديك صلاحية طرق الدفع.")
        rows=list((await session.scalars(select(PaymentMethod).order_by(PaymentMethod.sort_order,PaymentMethod.id))).all())
        set_state(context,"ADMIN_PAYMENT_METHODS")
        await update.message.reply_text("💳 طرق الدفع:\n"+"\n".join(f"#{m.id} | {m.name} | {'فعال' if m.active else 'متوقف'} | proof={m.requires_proof} | order={m.sort_order}" for m in rows) + "\n\nاختر: إضافة / تعديل / تفعيل / تعطيل / حذف / ترتيب ثم رقم الطريقة.",reply_markup=back_home()); return
    if state=="ADMIN_PAYMENT_LIST":
        if not allowed(a,"payments.read"): raise PermissionError("ليس لديك صلاحية قراءة المدفوعات.")
        q=select(PaymentRequest).order_by(PaymentRequest.created_at.desc()).limit(20)
        if text=="المعلقة": q=q.where(PaymentRequest.status==PaymentStatus.PENDING)
        elif text not in ("الكل",):
            try:q=q.where(PaymentRequest.id==int(text))
            except ValueError: await update.message.reply_text("اكتب: المعلقة أو الكل أو رقم الطلب."); return
        rows=list((await session.scalars(q)).all())
        if not rows: await update.message.reply_text("لا توجد نتائج."); return
        await update.message.reply_text("💰 المدفوعات:\n"+"\n".join(f"#{p.id} | {p.status.value} | {p.amount} {p.currency} | مرجع {p.transaction_reference}" for p in rows)+"\n\nأرسل رقم الطلب لفتحه.",reply_markup=back_home()); set_state(context,"ADMIN_PAYMENT_OPEN",payment_ids=[p.id for p in rows]); return
    if state=="ADMIN_PAYMENT_METHODS":
        if not allowed(a,"payments.read"): raise PermissionError("ليس لديك صلاحية قراءة طرق الدفع.")
        action=text
        if action=="إضافة":
            if not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية إدارة طرق الدفع.")
            set_state(context,"ADMIN_PM_ADD"); await update.message.reply_text("أرسل: الاسم | اسم الحساب | رقم الحساب | التعليمات | proof(نعم/لا) | الترتيب",reply_markup=back_home()); return
        parts=action.split()
        if len(parts)!=2 or parts[0] not in ("تعديل","تفعيل","تعطيل","حذف","ترتيب"):
            await update.message.reply_text("استخدم: إضافة أو تعديل/تفعيل/تعطيل/حذف/ترتيب + رقم الطريقة."); return
        try:mid=int(parts[1])
        except ValueError: raise ValueError("رقم طريقة الدفع غير صحيح.")
        m=await session.get(PaymentMethod,mid)
        if not m: raise ValueError("طريقة الدفع غير موجودة.")
        act=parts[0]
        if act=="تعديل": set_state(context,"ADMIN_PM_EDIT",payment_method_id=mid); await update.message.reply_text("أرسل: الاسم | اسم الحساب | رقم الحساب | التعليمات | proof(نعم/لا) | الترتيب",reply_markup=back_home()); return
        if not allowed(a,"settings.write") and not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية تعديل طرق الدفع.")
        if act=="تفعيل": m.active=True
        elif act=="تعطيل": m.active=False
        elif act=="حذف": await session.delete(m)
        else: set_state(context,"ADMIN_PM_ORDER",payment_method_id=mid); await update.message.reply_text("أرسل رقم الترتيب."); return
        await AuditService().log(session,a.telegram_id,"payment_method_change","payment_method",mid,new={"action":act}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التنفيذ.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PM_ADD":
        if not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية إدارة طرق الدفع.")
        parts=[x.strip() for x in text.split("|")]
        if len(parts)!=6 or parts[4] not in ("نعم","لا"): raise ValueError("الصيغة غير صحيحة.")
        name,an,anum,instr,proof,order=parts
        try:order=int(order)
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        m=PaymentMethod(name=name,account_name=an,account_number=anum,instructions=instr,requires_proof=proof=="نعم",active=True,sort_order=order); session.add(m); await session.flush(); await AuditService().log(session,a.telegram_id,"payment_method_create","payment_method",m.id,new={"name":name}); set_state(context,"IDLE"); await update.message.reply_text("✅ تمت إضافة طريقة الدفع.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PM_EDIT":
        if not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية إدارة طرق الدفع.")
        parts=[x.strip() for x in text.split("|")]
        if len(parts)!=6 or parts[4] not in ("نعم","لا"): raise ValueError("الصيغة غير صحيحة.")
        m=await session.get(PaymentMethod,context.user_data["payment_method_id"]); name,an,anum,instr,proof,order=parts
        try:order=int(order)
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        m.name=name;m.account_name=an;m.account_number=anum;m.instructions=instr;m.requires_proof=proof=="نعم";m.sort_order=order; await AuditService().log(session,a.telegram_id,"payment_method_edit","payment_method",m.id,new={"name":name}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التعديل.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PM_ORDER":
        if not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية إدارة طرق الدفع.")
        try:n=int(text)
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        m=await session.get(PaymentMethod,context.user_data["payment_method_id"]); m.sort_order=n; await AuditService().log(session,a.telegram_id,"payment_method_reorder","payment_method",m.id,new={"sort_order":n}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم الترتيب.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PAYMENT_OPEN":
        if not allowed(a,"payments.read"): raise PermissionError("ليس لديك صلاحية قراءة المدفوعات.")
        try: pid=int(text)
        except ValueError: await update.message.reply_text("أرسل رقم الطلب."); return
        p=await session.get(PaymentRequest,pid)
        if not p: raise ValueError("الطلب غير موجود.")
        phone=await session.get(PhoneNumber,p.phone_number_id); c=await session.get(Customer,p.customer_id); m=await session.get(PaymentMethod,p.payment_method_id)
        context.user_data["selected_payment"]=pid
        buttons=[("موافقة","رفض")] if p.status==PaymentStatus.PENDING else []
        await update.message.reply_text(f"💰 طلب #{p.id}\nالعميل: {c.full_name or '—'} | TG {c.telegram_id}\n📱 {phone.normalized_phone}\n📡 الشركة: {(await session.get(TelecomCompany,phone.telecom_company_id)).name}\nطريقة الدفع: {m.name}\nالمبلغ: {p.amount} {p.currency}\nالمرجع: {p.transaction_reference}\nالإثبات: {'موجود' if p.proof_file_id else 'غير موجود'}\nالحالة: {p.status.value}"+(f"\nسبب الرفض: {p.rejection_reason}" if p.rejection_reason else ""),reply_markup=menu(*buttons,("🔙 رجوع","🏠 الرئيسية"))); set_state(context,"ADMIN_PAYMENT_ACTION") ; return
    if state=="ADMIN_PAYMENT_ACTION":
        pid=context.user_data["selected_payment"]
        if text=="موافقة":
            if not allowed(a,"payments.approve"): raise PermissionError("ليس لديك صلاحية اعتماد المدفوعات.")
            sub,chat=await services["subscription"].approve_payment(pid,a.id); context.user_data["post_commit_chat"]=chat; context.user_data["post_commit_message"]=f"✅ تمت الموافقة على الدفع.\n🛡️ الحماية مفعلة حتى {sub.end_at.date()}."; context.user_data["post_commit_admin_message"]=f"✅ تمت الموافقة. الاشتراك #{sub.id} حتى {sub.end_at.date()}."; context.user_data["state"]="IDLE"; return
        if text=="رفض":
            if not allowed(a,"payments.reject"): raise PermissionError("ليس لديك صلاحية رفض المدفوعات.")
            set_state(context,"ADMIN_REJECT_REASON"); await update.message.reply_text("أرسل سبب الرفض.",reply_markup=back_home()); return
    if state=="ADMIN_REJECT_REASON":
        if not allowed(a,"payments.reject"): raise PermissionError("ليس لديك صلاحية رفض المدفوعات.")
        chat=await services["subscription"].reject_payment(context.user_data["selected_payment"],a.id,text); context.user_data["post_commit_chat"]=chat; context.user_data["state"]="IDLE"; await update.message.reply_text("❌ تم الرفض وتسجيل السبب.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PHONE_SEARCH" and text=="شركات الاتصالات":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        rows=list((await session.scalars(select(TelecomCompany).order_by(TelecomCompany.sort_order,TelecomCompany.id))).all()); set_state(context,"ADMIN_COMPANIES"); await update.message.reply_text("📡 الشركات:\n"+"\n".join(f"#{x.id} | {x.name} | {x.code} | {'فعال' if x.active else 'متوقف'} | {x.sort_order}" for x in rows)+"\n\nأرسل: إضافة أو تعديل/تفعيل/تعطيل/حذف/ترتيب + رقم الشركة.",reply_markup=back_home()); return
    if state=="ADMIN_COMPANIES":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        if text=="إضافة": set_state(context,"ADMIN_COMPANY_ADD"); await update.message.reply_text("أرسل: الاسم | الكود | الترتيب",reply_markup=back_home()); return
        parts=text.split()
        if len(parts)!=2 or parts[0] not in ("تعديل","تفعيل","تعطيل","حذف","ترتيب"): raise ValueError("صيغة غير صحيحة.")
        try:cid=int(parts[1])
        except ValueError: raise ValueError("رقم الشركة غير صحيح.")
        c=await session.get(TelecomCompany,cid)
        if not c: raise ValueError("الشركة غير موجودة.")
        if parts[0]=="تعديل": set_state(context,"ADMIN_COMPANY_EDIT",company_id=cid); await update.message.reply_text("أرسل: الاسم | الكود | الترتيب",reply_markup=back_home()); return
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        if parts[0]=="تفعيل": c.active=True
        elif parts[0]=="تعطيل": c.active=False
        elif parts[0]=="حذف":
            used=await session.scalar(select(func.count()).select_from(PhoneNumber).where(PhoneNumber.telecom_company_id==cid))
            if used: raise ValueError("لا يمكن حذف شركة مرتبطة بأرقام. عطّلها بدلًا من الحذف.")
            await session.delete(c)
        else: set_state(context,"ADMIN_COMPANY_ORDER",company_id=cid); await update.message.reply_text("أرسل رقم الترتيب."); return
        await AuditService().log(session,a.telegram_id,"telecom_company_change","telecom_company",cid,new={"action":parts[0]}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التنفيذ.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_COMPANY_ADD":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        parts=[x.strip() for x in text.split("|")]
        if len(parts)!=3: raise ValueError("الصيغة: الاسم | الكود | الترتيب")
        try:order=int(parts[2])
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        c=TelecomCompany(name=parts[0],code=parts[1],sort_order=order,active=True); session.add(c); await session.flush(); await AuditService().log(session,a.telegram_id,"telecom_company_create","telecom_company",c.id,new={"name":c.name}); set_state(context,"IDLE"); await update.message.reply_text("✅ تمت إضافة الشركة.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_COMPANY_EDIT":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        parts=[x.strip() for x in text.split("|")]
        if len(parts)!=3: raise ValueError("الصيغة: الاسم | الكود | الترتيب")
        try:order=int(parts[2])
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        c=await session.get(TelecomCompany,context.user_data["company_id"]); c.name=parts[0];c.code=parts[1];c.sort_order=order; await AuditService().log(session,a.telegram_id,"telecom_company_edit","telecom_company",c.id,new={"name":c.name}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التعديل.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_COMPANY_ORDER":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية إدارة الشركات.")
        try:n=int(text)
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        c=await session.get(TelecomCompany,context.user_data["company_id"]); c.sort_order=n; await AuditService().log(session,a.telegram_id,"telecom_company_reorder","telecom_company",c.id,new={"sort_order":n}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم الترتيب.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_CUSTOMER_SEARCH":
        if not allowed(a,"customers.read"): raise PermissionError("ليس لديك صلاحية قراءة العملاء.")
        rows=await services["customer_repo"].search(text,20,0)
        if not rows:
            try:
                n=normalize_yemen_phone(text); ph=await services["phone_repo"].get_by_normalized(n); rows=[await session.get(Customer,ph.customer_id)] if ph else []
            except ValueError: rows=[]
        out="\n".join(f"#{x.id} | {x.full_name or '—'} | TG {x.telegram_id} | {x.status.value}" for x in rows if x)
        set_state(context,"ADMIN_CUSTOMER_OPEN",customer_ids=[x.id for x in rows if x]); await update.message.reply_text(out or "لا توجد نتائج.",reply_markup=back_home()); return
    if state=="ADMIN_PHONE_SEARCH":
        if not allowed(a,"phones.read"): raise PermissionError("ليس لديك صلاحية قراءة الأرقام.")
        rows=await services["phone_repo"].search(text,20,0); set_state(context,"ADMIN_PHONE_OPEN",phone_ids=[x.id for x in rows]); await update.message.reply_text("\n".join(f"#{x.id} | {x.normalized_phone} | {x.status.value} | customer#{x.customer_id}" for x in rows) or "لا توجد نتائج.",reply_markup=back_home()); return
    if state=="ADMIN_SUB_SEARCH":
        if not allowed(a,"subscriptions.read"): raise PermissionError("ليس لديك صلاحية قراءة الاشتراكات.")
        try: sid=int(text)
        except ValueError: sid=None
        if sid:
            sub=await session.get(Subscription,sid); rows=[sub] if sub else []
        else:
            try:n=normalize_yemen_phone(text); ph=await services["phone_repo"].get_by_normalized(n); rows=list((await session.scalars(select(Subscription).where(Subscription.phone_number_id==ph.id).order_by(Subscription.end_at.desc()))).all()) if ph else []
            except ValueError: rows=[]
        await update.message.reply_text("\n".join(f"#{x.id} | {x.start_at.date()} → {x.end_at.date()} | {x.price} {x.currency} | phone#{x.phone_number_id}" for x in rows) or "لا توجد نتائج.",reply_markup=back_home()); set_state(context,"ADMIN_SUB_ACTION",subscription_ids=[x.id for x in rows]); return
    if state=="ADMIN_SUB_ACTION":
        parts=text.split()
        if len(parts)!=2 or parts[0] not in ("تجديد","تمديد") or not parts[1].startswith("#"): raise ValueError("استخدم: تجديد #ID أو تمديد #ID")
        try:sid=int(parts[1][1:])
        except ValueError: raise ValueError("رقم الاشتراك غير صحيح")
        if sid not in context.user_data.get("subscription_ids",[]): raise ValueError("الاشتراك غير موجود في القائمة")
        sub=await session.get(Subscription,sid)
        if parts[0]=="تمديد":
            if not allowed(a,"subscriptions.extend"): raise PermissionError("ليس لديك صلاحية التمديد.")
            set_state(context,"ADMIN_SUB_EXTEND",subscription_id=sid); await update.message.reply_text("أرسل عدد أيام التمديد.",reply_markup=back_home()); return
        if not allowed(a,"subscriptions.renew"): raise PermissionError("ليس لديك صلاحية التجديد.")
        set_state(context,"ADMIN_SUB_RENEW",subscription_id=sid); await update.message.reply_text("أرسل: عدد الأيام | المبلغ | العملة",reply_markup=back_home()); return
    if state=="ADMIN_SUB_EXTEND":
        if not allowed(a,"subscriptions.extend"): raise PermissionError("ليس لديك صلاحية التمديد.")
        try:n=int(text)
        except ValueError: raise ValueError("عدد الأيام يجب أن يكون رقمًا.")
        sub=await services["subscription"].extend(context.user_data["subscription_id"],a.telegram_id,n); set_state(context,"IDLE"); await update.message.reply_text(f"✅ تم التمديد حتى {sub.end_at.date()}.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_SUB_RENEW":
        if not allowed(a,"subscriptions.renew"): raise PermissionError("ليس لديك صلاحية التجديد.")
        parts=[x.strip() for x in text.split("|")]
        if len(parts)!=3: raise ValueError("الصيغة: الأيام | المبلغ | العملة")
        try:days=int(parts[0])
        except ValueError: raise ValueError("الأيام غير صحيحة")
        sub=await session.get(Subscription,context.user_data["subscription_id"]); phone=await session.get(PhoneNumber,sub.phone_number_id); renewed=await services["subscription"].renew(phone.id,a.telegram_id,days,money(parts[1]),parts[2]); set_state(context,"IDLE"); await update.message.reply_text(f"✅ تم التجديد باشتراك جديد #{renewed.id} حتى {renewed.end_at.date()}.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_CUSTOMER_OPEN":
        if not allowed(a,"customers.read"): raise PermissionError("ليس لديك صلاحية قراءة العملاء.")
        try: cid=int(text)
        except ValueError: cid=None
        if cid not in context.user_data.get("customer_ids",[]): raise ValueError("اختر رقم عميل من النتائج.")
        c=await session.get(Customer,cid); phones=list((await session.scalars(select(PhoneNumber).where(PhoneNumber.customer_id==cid))).all()); payments=list((await session.scalars(select(PaymentRequest).where(PaymentRequest.customer_id==cid).order_by(PaymentRequest.id.desc()).limit(10))).all()); tickets=list((await session.scalars(select(SupportTicket).where(SupportTicket.customer_id==cid).order_by(SupportTicket.id.desc()).limit(10))).all())
        context.user_data["selected_customer"]=cid
        await update.message.reply_text(f"👤 العميل #{c.id}\nالاسم: {c.full_name or '—'}\nTG: {c.telegram_id}\nالحالة: {c.status.value}\nالأرقام: {len(phones)}\nالمدفوعات: {len(payments)}\nالتذاكر: {len(tickets)}",reply_markup=menu(("حظر","إلغاء الحظر"),("تعليق","تفعيل"),("التاريخ الكامل",),("🔙 رجوع","🏠 الرئيسية"))); set_state(context,"ADMIN_CUSTOMER_ACTION"); return
    if state=="ADMIN_CUSTOMER_ACTION":
        if text in ("تعليق","تفعيل") and not allowed(a,"customers.edit"): raise PermissionError("ليس لديك صلاحية تعديل العميل.")
        if text=="التاريخ الكامل" and not allowed(a,"customers.read"): raise PermissionError("ليس لديك صلاحية قراءة سجل العميل.")
        if not allowed(a,"customers.edit") and text not in ("حظر","إلغاء الحظر","تعليق","تفعيل"): raise PermissionError("ليس لديك صلاحية تعديل العميل.")
        cid=context.user_data["selected_customer"]; c=await session.get(Customer,cid); old=c.status.value
        if text=="حظر":
            if not allowed(a,"customers.block"): raise PermissionError("ليس لديك صلاحية الحظر.")
            c.status=CustomerStatus.BLOCKED
        elif text=="إلغاء الحظر":
            if not allowed(a,"customers.block"): raise PermissionError("ليس لديك صلاحية الحظر.")
            c.status=CustomerStatus.ACTIVE
        elif text=="تعليق": c.status=CustomerStatus.SUSPENDED
        elif text=="تفعيل": c.status=CustomerStatus.ACTIVE
        elif text=="التاريخ الكامل":
            rows=list((await session.scalars(select(AuditLog).where(AuditLog.entity_type=="customer",AuditLog.entity_id==str(cid)).order_by(AuditLog.created_at.desc()).limit(30))).all()); await update.message.reply_text("\n".join(f"{x.created_at:%Y-%m-%d %H:%M} {x.action}" for x in rows) or "لا يوجد سجل.",reply_markup=back_home()); return
        else:return
        await AuditService().log(session,a.telegram_id,"customer_status_change","customer",cid,old={"status":old},new={"status":c.status.value}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم تحديث حالة العميل.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_PHONE_OPEN":
        if not allowed(a,"phones.read"): raise PermissionError("ليس لديك صلاحية قراءة الأرقام.")
        try: pid=int(text)
        except ValueError: raise ValueError("أرسل رقم الهاتف الداخلي من النتائج.")
        if pid not in context.user_data.get("phone_ids",[]): raise ValueError("الرقم غير موجود في النتائج.")
        p=await session.get(PhoneNumber,pid); company=await session.get(TelecomCompany,p.telecom_company_id)
        await update.message.reply_text(f"📱 #{p.id}\n{p.normalized_phone}\n📡 {company.name}\nالحالة: {p.status.value}\nالعميل: #{p.customer_id}",reply_markup=menu(("تعليق الرقم","تفعيل الرقم"),("منتهي",),("🔙 رجوع","🏠 الرئيسية"))); set_state(context,"ADMIN_PHONE_ACTION",phone_id=pid); return
    if state=="ADMIN_PHONE_ACTION":
        if not allowed(a,"phones.edit"): raise PermissionError("ليس لديك صلاحية تعديل الأرقام.")
        p=await session.get(PhoneNumber,context.user_data["phone_id"]); old=p.status.value
        mapping={"تعليق الرقم":PhoneStatus.SUSPENDED,"تفعيل الرقم":PhoneStatus.PROTECTED,"منتهي":PhoneStatus.EXPIRED}
        if text not in mapping:return
        p.status=mapping[text]; await AuditService().log(session,a.telegram_id,"phone_status_change","phone_number",p.id,old={"status":old},new={"status":p.status.value}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم تحديث الرقم.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_SUPPORT_LIST":
        if not allowed(a,"support.read"): raise PermissionError("ليس لديك صلاحية قراءة الدعم.")
        q=select(SupportTicket).order_by(SupportTicket.updated_at.desc()).limit(20)
        if text!="الكل":
            try:q=q.where(SupportTicket.id==int(text))
            except ValueError: await update.message.reply_text("أرسل رقم التذكرة أو الكل."); return
        rows=list((await session.scalars(q)).all()); set_state(context,"ADMIN_SUPPORT_OPEN",ticket_ids=[x.id for x in rows]); await update.message.reply_text("\n".join(f"#{x.id} | {x.status.value} | {x.subject} | customer#{x.customer_id}" for x in rows) or "لا توجد تذاكر.",reply_markup=back_home()); return
    if state=="ADMIN_SUPPORT_OPEN":
        if not allowed(a,"support.read"): raise PermissionError("ليس لديك صلاحية قراءة الدعم.")
        try:tid=int(text)
        except ValueError: raise ValueError("رقم تذكرة غير صحيح.")
        if tid not in context.user_data.get("ticket_ids",[]): raise ValueError("التذكرة غير موجودة في القائمة.")
        t=await session.get(SupportTicket,tid); msgs=await services["support_repo"].messages(tid,50); await update.message.reply_text(f"💬 #{tid} | {t.status.value}\n{t.subject}\n\n"+"\n".join(f"{m.sender_telegram_id}: {m.message_text}" for m in msgs),reply_markup=menu(("رد", "إغلاق"),("إعادة فتح","تعيين"),("🔙 رجوع","🏠 الرئيسية"))); set_state(context,"ADMIN_SUPPORT_ACTION",ticket_id=tid); return
    if state=="ADMIN_SUPPORT_ACTION":
        if text=="رد":
            if not allowed(a,"support.reply"): raise PermissionError("ليس لديك صلاحية الرد.")
            set_state(context,"ADMIN_SUPPORT_MESSAGE"); await update.message.reply_text("أرسل الرد.",reply_markup=back_home()); return
        t=await session.get(SupportTicket,context.user_data["ticket_id"])
        if text=="إغلاق":
            if not allowed(a,"support.close"): raise PermissionError("ليس لديك صلاحية الإغلاق.")
            t.status=TicketStatus.CLOSED
        elif text=="إعادة فتح":
            if not allowed(a,"support.reopen"): raise PermissionError("ليس لديك صلاحية إعادة الفتح.")
            t.status=TicketStatus.OPEN
        elif text=="تعيين":
            if not allowed(a,"support.assign"): raise PermissionError("ليس لديك صلاحية التعيين.")
            set_state(context,"ADMIN_SUPPORT_ASSIGN"); await update.message.reply_text("أرسل Telegram ID للموظف الإداري.",reply_markup=back_home()); return
        else:return
        await AuditService().log(session,a.telegram_id,"support_status_change","support_ticket",t.id,new={"status":t.status.value}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم تحديث التذكرة.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_SUPPORT_MESSAGE":
        if not allowed(a,"support.reply"): raise PermissionError("ليس لديك صلاحية الرد.")
        t=await session.get(SupportTicket,context.user_data["ticket_id"])
        if t.status==TicketStatus.CLOSED: raise ValueError("التذكرة مغلقة. أعد فتحها أولًا.")
        msg=await services["support_repo"].add_message(ticket_id=t.id,sender_telegram_id=a.telegram_id,message_text=text); t.status=TicketStatus.PENDING_CUSTOMER
        c=await session.get(Customer,t.customer_id); services["notification"].repo.s.add(Notification(customer_id=c.id,kind="SUPPORT",body=f"💬 رد الدعم على التذكرة #{t.id}:\n{text}",dedupe_key=f"support:{t.id}:message:{msg.id}")); await AuditService().log(session,a.telegram_id,"support_reply","support_ticket",t.id,new={"message_id":msg.id,"sender_telegram_id":a.telegram_id}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم إرسال الرد.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_SUPPORT_ASSIGN":
        if not allowed(a,"support.assign"): raise PermissionError("ليس لديك صلاحية التعيين.")
        try:tg=int(text)
        except ValueError: raise ValueError("Telegram ID غير صحيح.")
        target=await session.scalar(select(AdminUser).where(AdminUser.telegram_id==tg,AdminUser.active.is_(True)))
        if not target: raise ValueError("الموظف الإداري غير موجود.")
        t=await session.get(SupportTicket,context.user_data["ticket_id"]); t.assigned_admin_id=target.id; await AuditService().log(session,a.telegram_id,"support_assignment","support_ticket",t.id,new={"assigned_admin_id":target.id}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التعيين.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_SETTINGS":
        from ..services.settings_service import DEFAULTS
        if text not in DEFAULTS: raise ValueError("اسم الإعداد غير صحيح.")
        set_state(context,"ADMIN_SETTING_VALUE",setting_key=text); await update.message.reply_text(f"القيمة الحالية: {await services['settings'].get(text)}\nأرسل القيمة الجديدة.",reply_markup=back_home()); return
    if state=="ADMIN_SETTING_VALUE":
        key=context.user_data["setting_key"]; value=await services["settings"].validate(key,text); set_state(context,"ADMIN_SETTING_CONFIRM",setting_new=value); await update.message.reply_text(f"معاينة: {key} = {value}\nأرسل نعم للحفظ أو إلغاء.",reply_markup=menu(("نعم","إلغاء"))); return
    if state=="ADMIN_SETTING_CONFIRM":
        if text=="إلغاء": set_state(context,"IDLE"); await update.message.reply_text("تم الإلغاء.",reply_markup=admin_home(PERMISSIONS[a.role])); return
        if text!="نعم": return
        if not allowed(a,"settings.write"): raise PermissionError("ليس لديك صلاحية تعديل الإعدادات.")
        key=context.user_data["setting_key"]; old=await services["settings"].get(key); await services["settings"].set(key,context.user_data["setting_new"]); await AuditService().log(session,a.telegram_id,"settings_change","system_setting",key,old=old,new=context.user_data["setting_new"]); set_state(context,"IDLE"); await update.message.reply_text("✅ تم الحفظ. لا تتأثر البيانات التاريخية.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_FAQ_MENU":
        if text=="إضافة":
            if not allowed(a,"faq.write"): raise PermissionError("ليس لديك صلاحية FAQ.")
            set_state(context,"ADMIN_FAQ_NEW_Q"); await update.message.reply_text("أرسل السؤال الجديد.",reply_markup=back_home()); return
        if text not in ("تعديل","حذف","تفعيل","تعطيل","ترتيب","عرض"): raise ValueError("اختر عملية صحيحة.")
        set_state(context,"ADMIN_FAQ_ACTION",faq_action=text); await update.message.reply_text("أرسل رقم السؤال.",reply_markup=back_home()); return
    if state=="ADMIN_FAQ_ACTION":
        try:fid=int(text)
        except ValueError: raise ValueError("رقم السؤال غير صحيح.")
        row=await session.get(FAQItem,fid)
        if not row: raise ValueError("السؤال غير موجود.")
        action=context.user_data["faq_action"]
        if action=="إضافة": set_state(context,"ADMIN_FAQ_NEW_Q"); await update.message.reply_text("أرسل السؤال الجديد.",reply_markup=back_home()); return
        if action=="عرض": await update.message.reply_text(f"#{row.id}\n❓ {row.question}\n{row.answer}\nنشط: {row.active}\nترتيب: {row.sort_order}",reply_markup=back_home()); return
        if action=="تعديل": set_state(context,"ADMIN_FAQ_EDIT",faq_id=fid); await update.message.reply_text("أرسل السؤال الجديد ثم | ثم الإجابة."); return
        if action in ("حذف","تفعيل","تعطيل","ترتيب"):
            if not allowed(a,"faq.write"): raise PermissionError("ليس لديك صلاحية تعديل FAQ.")
            if action=="حذف": await session.delete(row)
            elif action=="تفعيل": row.active=True
            elif action=="تعطيل": row.active=False
            else: set_state(context,"ADMIN_FAQ_ORDER",faq_id=fid); await update.message.reply_text("أرسل رقم الترتيب."); return
            await AuditService().log(session,a.telegram_id,"faq_change","faq_item",fid,new={"action":action}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التنفيذ.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_FAQ_NEW_Q": set_state(context,"ADMIN_FAQ_NEW_A",faq_question=text); await update.message.reply_text("أرسل الإجابة.",reply_markup=back_home()); return
    if state=="ADMIN_FAQ_NEW_A":
        if not allowed(a,"faq.write"): raise PermissionError("ليس لديك صلاحية FAQ.")
        row=FAQItem(question=context.user_data["faq_question"],answer=text,active=True,sort_order=0); session.add(row); await session.flush(); await AuditService().log(session,a.telegram_id,"faq_create","faq_item",row.id,new={"question":row.question}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم إنشاء السؤال.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_FAQ_EDIT":
        if not allowed(a,"faq.write"): raise PermissionError("ليس لديك صلاحية FAQ.")
        parts=text.split("|",1)
        if len(parts)!=2: raise ValueError("استخدم: السؤال | الإجابة")
        row=await session.get(FAQItem,context.user_data["faq_id"]); old={"question":row.question,"answer":row.answer}; row.question=parts[0].strip(); row.answer=parts[1].strip(); await AuditService().log(session,a.telegram_id,"faq_edit","faq_item",row.id,old=old,new={"question":row.question,"answer":row.answer}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم التعديل.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_FAQ_ORDER":
        if not allowed(a,"faq.write"): raise PermissionError("ليس لديك صلاحية FAQ.")
        try:n=int(text)
        except ValueError: raise ValueError("الترتيب يجب أن يكون رقمًا.")
        row=await session.get(FAQItem,context.user_data["faq_id"]); row.sort_order=n; await AuditService().log(session,a.telegram_id,"faq_reorder","faq_item",row.id,new={"sort_order":n}); set_state(context,"IDLE"); await update.message.reply_text("✅ تم الترتيب.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_REPORTS":
        if text=="اليوم": start=utcnow().replace(hour=0,minute=0,second=0,microsecond=0); end=start+timedelta(days=1)
        elif text=="الشهر": now=utcnow(); start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0); end=(start+timedelta(days=32)).replace(day=1)
        else:
            try: a1,a2=text.split(); from datetime import datetime,timezone; start=datetime.fromisoformat(a1).replace(tzinfo=timezone.utc); end=datetime.fromisoformat(a2).replace(tzinfo=timezone.utc)+timedelta(days=1)
            except Exception: raise ValueError("الصيغة: YYYY-MM-DD YYYY-MM-DD")
        v=await services["report"].period(session,start,end); await update.message.reply_text(f"📈 التقرير\nالعملاء الجدد: {v['customers']}\nطلبات الدفع: {v['payments']}\nالإيرادات المعتمدة: {v['revenue']}",reply_markup=back_home()); set_state(context,"IDLE"); return
    if state=="ADMIN_AUDIT":
        q=select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)
        if text!="الكل": q=q.where(AuditLog.action.ilike(f"%{text}%"))
        rows=list((await session.scalars(q)).all()); await update.message.reply_text("\n".join(f"{x.created_at:%Y-%m-%d %H:%M} | {x.action} | {x.entity_type}#{x.entity_id}" for x in rows) or "لا يوجد سجل.",reply_markup=back_home()); set_state(context,"IDLE"); return
    if state=="ADMIN_NOTIFICATION_LIST":
        if not allowed(a,"notifications.read"): raise PermissionError("ليس لديك صلاحية قراءة الإشعارات.")
        if text=="إرسال":
            if not allowed(a,"notifications.send"): raise PermissionError("ليس لديك صلاحية إرسال الإشعارات.")
            set_state(context,"ADMIN_NOTIFICATION_SEND"); await update.message.reply_text("أرسل نص الإعلان ليتم وضعه في طابور الإشعارات للعملاء النشطين.",reply_markup=back_home()); return
        rows=list((await session.scalars(select(Notification).order_by(Notification.id.desc()).limit(50))).all()); await update.message.reply_text("\n".join(f"#{x.id} | {x.kind} | attempts={x.attempts} | sent={bool(x.sent_at)}" for x in rows) or "لا توجد إشعارات.",reply_markup=back_home()); set_state(context,"IDLE"); return
    if state=="ADMIN_NOTIFICATION_SEND":
        if not allowed(a,"notifications.send"): raise PermissionError("ليس لديك صلاحية إرسال الإشعارات.")
        import hashlib
        body=text.strip()
        if not 2 <= len(body) <= 4000: raise ValueError("نص الإعلان غير صالح.")
        marker=hashlib.sha256((str(a.telegram_id)+body+utcnow().isoformat()).encode()).hexdigest()[:20]
        last_id=0; total=0
        while True:
            ids=list((await session.scalars(select(Customer.id).where(Customer.status==CustomerStatus.ACTIVE,Customer.id>last_id).order_by(Customer.id).limit(500))).all())
            if not ids: break
            for cid in ids: session.add(Notification(customer_id=cid,kind="ADMIN_ANNOUNCEMENT",body=body,dedupe_key=f"announcement:{marker}:{cid}"))
            total += len(ids); last_id=ids[-1]; await session.flush()
        await AuditService().log(session,a.telegram_id,"notification_announcement","notification",marker,new={"customers":total}); set_state(context,"IDLE"); await update.message.reply_text(f"✅ تم وضع الإعلان لـ {total} عميل نشط في الطابور.",reply_markup=admin_home(PERMISSIONS[a.role])); return
    if state=="ADMIN_FOLLOWUP_LIST":
        if not allowed(a,"followups.read"): raise PermissionError("ليس لديك صلاحية قراءة المتابعات.")
        q=select(Followup).order_by(Followup.cycle_end).limit(50)
        if text!="الكل":
            try:q=q.where(Followup.id==int(text))
            except ValueError:
                try:n=normalize_yemen_phone(text); ph=await services["phone_repo"].get_by_normalized(n); q=q.where(Followup.phone_number_id==ph.id if ph else False)
                except ValueError: raise ValueError("أدخل رقم المتابعة أو الهاتف أو الكل.")
        rows=list((await session.scalars(q)).all()); await update.message.reply_text("\n".join(f"#{x.id} | phone#{x.phone_number_id} | {x.cycle_start.date()} → {x.cycle_end.date()}" for x in rows) or "لا توجد نتائج.",reply_markup=back_home()); set_state(context,"IDLE"); return
    await update.message.reply_text("الحالة الحالية غير معروفة. أعد فتح القسم.",reply_markup=admin_home(PERMISSIONS[a.role])); set_state(context,"IDLE")
