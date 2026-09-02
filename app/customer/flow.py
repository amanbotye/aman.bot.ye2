from __future__ import annotations
from datetime import timezone, datetime
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.database import SessionLocal
from app.states import State
from app.keyboards import *
from app.models import Customer, TelecomCompany, PaymentMethod, FAQ, SupportStatus
from app.config import settings
from app.services.customer_service import get_or_create_customer, active_companies, register_phone, numbers, counts
from app.services.payment_service import active_methods, pending_for, create_payment
from app.services.settings_service import get, get_decimal
from app.services.session_service import load, save, clear
from app.services.subscription_service import active_subscription, classify_subscription, remaining
from app.services.support_service import create_ticket, add_message, customer_tickets
from app.utils import normalize_name, is_valid_full_name, normalize_phone, is_valid_yemeni_phone, display_phone

async def customer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message: return
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user)
        await clear(db, c.telegram_id)
    await update.message.reply_text(
        f"مرحباً بك {c.full_name or update.effective_user.first_name or 'بك'} 👋\n\n"
        "🛡️ أهلاً بك في أمان AMAN.\nخدمة حماية وإدارة أرقامك.\n\nاختر الخدمة التي تريدها:",
        reply_markup=customer_main_menu())

async def protect_start(update, context):
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user)
        companies = await active_companies(db)
        if not c.full_name:
            await save(db, c.telegram_id, State.NAME_INPUT, {'customer_id': c.id})
            msg, kb = "نحتاج اسمك الكامل مرة واحدة فقط لربط أرقامك بحسابك.\n\n✍️ اكتب اسمك الكامل:", back_menu()
        else:
            await save(db, c.telegram_id, State.COMPANY_SELECTION, {'customer_id': c.id})
            msg, kb = '📡 اختر شركة الاتصالات:', companies_keyboard(companies)
    await update.message.reply_text(msg, reply_markup=kb)

async def handle_state(update, context, state, data):
    if not update.message or not update.effective_user: return
    text = (update.message.text or '').strip()
    uid = update.effective_user.id
    if text == '/start': return await customer_start(update, context)
    if text in ('🔙 رجوع', '🏠 الرئيسية'):
        async with SessionLocal() as db: await clear(db, uid)
        await update.message.reply_text('تم الرجوع إلى القائمة الرئيسية.', reply_markup=customer_main_menu()); return
    if state == State.NAME_INPUT:
        name = normalize_name(text)
        if not is_valid_full_name(name):
            await update.message.reply_text('⚠️ يرجى كتابة اسمك الكامل بشكل صحيح.', reply_markup=back_menu()); return
        async with SessionLocal() as db:
            c = await db.get(Customer, data['customer_id'])
            if not c: await update.message.reply_text('⚠️ تعذر العثور على حسابك. أرسل /start.'); return
            c.full_name = name; companies = await active_companies(db)
            await save(db, uid, State.COMPANY_SELECTION, data)
        await update.message.reply_text('✅ تم حفظ اسمك.\n\n📡 الآن اختر شركة الاتصالات:', reply_markup=companies_keyboard(companies)); return
    if state == State.COMPANY_SELECTION:
        async with SessionLocal() as db:
            co = (await db.execute(select(TelecomCompany).where(TelecomCompany.name == text, TelecomCompany.is_active.is_(True)))).scalar_one_or_none()
            if not co: await update.message.reply_text('⚠️ اختر شركة من الأزرار الموجودة أمامك.'); return
            data['company_id'] = co.id; await save(db, uid, State.PHONE_INPUT, data)
        await update.message.reply_text('✍️ اكتب رقم الهاتف الذي تريد حمايته.\n\nمثال: 771234567', reply_markup=back_menu()); return
    if state == State.PHONE_INPUT:
        p = normalize_phone(text)
        if not is_valid_yemeni_phone(p):
            await update.message.reply_text('❌ رقم الهاتف غير صحيح. أدخل رقمًا يمنيًا من 9 أرقام يبدأ بـ 7.', reply_markup=back_menu()); return
        data['pending_phone'] = p
        async with SessionLocal() as db: await save(db, uid, State.PHONE_CONFIRMATION, data)
        await update.message.reply_text(f'📱 الرقم الذي أدخلته:\n\n{display_phone(p)}\n\nهل الرقم صحيح؟', reply_markup=phone_confirmation_keyboard()); return
    if state == State.PHONE_CONFIRMATION:
        if text == '✏️ تعديل الرقم':
            async with SessionLocal() as db: await save(db, uid, State.PHONE_INPUT, data)
            await update.message.reply_text('✍️ اكتب الرقم الصحيح:', reply_markup=back_menu()); return
        if text != '✅ تأكيد الرقم': await update.message.reply_text('⚠️ اختر أحد الخيارات.', reply_markup=phone_confirmation_keyboard()); return
        async with SessionLocal() as db:
            p, result = await register_phone(db, data['customer_id'], data['company_id'], data['pending_phone'])
            await db.commit()
            if result == 'owned_by_other':
                msg, kb = '❌ لا يمكن تسجيل هذا الرقم.\n\nهذا الرقم مرتبط بحساب آخر.', customer_main_menu(); await clear(db, uid)
            elif result == 'owned':
                msg, kb = 'ℹ️ هذا الرقم مسجل لديك بالفعل.\n\nيمكنك إدارته من «📱 أرقامي».', customer_main_menu(); await clear(db, uid)
            else:
                await save(db, uid, State.IDLE, {'customer_id': data['customer_id'], 'phone_id': p.id})
                msg, kb = f'✅ تم تسجيل الرقم بنجاح.\n\n📱 الرقم: {display_phone(p.phone_number)}\n📡 الشركة: {p.telecom_company.name}\n\n🟡 الحماية غير مفعلة.', phone_registered_keyboard()
        await update.message.reply_text(msg, reply_markup=kb); return
    if state == State.PHONE_SELECT:
        async with SessionLocal() as db:
            ns = await numbers(db, data['customer_id'])
            p = next((x for x in ns if display_phone(x.phone_number) == text), None)
            if not p: await update.message.reply_text('⚠️ اختر رقمًا من القائمة.', reply_markup=phone_list_keyboard(data.get('phone_labels', []))); return
            pending = await pending_for(db, p.customer_id, p.id)
            if pending:
                await clear(db, uid); await update.message.reply_text(f'⏳ لديك طلب دفع قيد المراجعة بالفعل.\n\nالكود: {pending.payment_code}', reply_markup=customer_main_menu()); return
            methods = await active_methods(db); price = await get_decimal(db, 'service_price', 1000); currency = await get(db, 'currency', 'YER')
            data.update(phone_id=p.id, method_ids={m.name: m.id for m in methods})
            await save(db, uid, State.PAYMENT_METHOD, data)
        if not methods: await update.message.reply_text('⚠️ لا توجد طرق دفع متاحة حاليًا.', reply_markup=customer_main_menu()); return
        await update.message.reply_text(f'💳 قيمة الخدمة: {price} {currency}\n\nاختر طريقة الدفع:', reply_markup=payment_methods_keyboard(methods)); return
    if state == State.PAYMENT_METHOD:
        async with SessionLocal() as db:
            method = (await db.execute(select(PaymentMethod).where(PaymentMethod.name == text, PaymentMethod.is_active.is_(True)))).scalar_one_or_none()
            if not method: await update.message.reply_text('⚠️ اختر طريقة دفع من القائمة.'); return
            data['method_id'] = method.id; await save(db, uid, State.PAYMENT_REFERENCE, data)
        await update.message.reply_text(f'💳 طريقة الدفع: {method.name}\n\nالحساب: {method.account_name or "-"}\nرقم الحساب: {method.account_number or "-"}\n\n{method.instructions or ""}\n\n✍️ أرسل رقم العملية / مرجع التحويل:', reply_markup=back_menu()); return
    if state == State.PAYMENT_REFERENCE:
        if not text: await update.message.reply_text('⚠️ مرجع العملية لا يمكن أن يكون فارغًا.'); return
        async with SessionLocal() as db:
            m = await db.get(PaymentMethod, data['method_id']); data['reference'] = text
            next_state = State.PAYMENT_PROOF if m and m.proof_required else State.PAYMENT_SUBMITTED
            await save(db, uid, next_state, data)
        if next_state == State.PAYMENT_PROOF: await update.message.reply_text('📎 أرسل صورة أو ملف إثبات الدفع.', reply_markup=back_menu())
        else: await submit_payment(update, data, None, None)
        return
    if state == State.PAYMENT_PROOF:
        if update.message.photo: proof, ptype = update.message.photo[-1].file_id, 'photo'
        elif update.message.document: proof, ptype = update.message.document.file_id, 'document'
        else: await update.message.reply_text('📎 أرسل صورة أو ملف إثبات الدفع.', reply_markup=back_menu()); return
        await submit_payment(update, data, proof, ptype); return
    if state == State.SUPPORT_SUBJECT:
        async with SessionLocal() as db:
            t = await create_ticket(db, data['customer_id'], text); await add_message(db, t.id, uid, 'تم فتح التذكرة.', False); await db.commit(); await clear(db, uid)
        await update.message.reply_text(f'✅ تم فتح تذكرة الدعم.\n\nرقم التذكرة: {t.ticket_code}\n\nاستخدم «💬 الدعم» لإرسال الرسائل.', reply_markup=customer_main_menu()); return
    if state == State.SUPPORT_TICKET_SELECT:
        async with SessionLocal() as db:
            ts = await customer_tickets(db, data['customer_id']); t = next((x for x in ts if x.ticket_code == text), None)
            if not t: await update.message.reply_text('⚠️ اختر تذكرة صحيحة.', reply_markup=back_menu()); return
            if t.status == SupportStatus.closed: await update.message.reply_text('🔒 هذه التذكرة مغلقة. يمكنك فتح تذكرة جديدة.', reply_markup=customer_main_menu()); return
            data['ticket_id'] = t.id; await save(db, uid, State.SUPPORT_REPLY, data)
        await update.message.reply_text(f'💬 التذكرة {t.ticket_code}\n\nأرسل رسالتك:', reply_markup=back_menu()); return
    if state == State.SUPPORT_REPLY:
        async with SessionLocal() as db:
            r, result = await add_message(db, data['ticket_id'], uid, text, False); await db.commit()
        await update.message.reply_text('✅ تم إرسال رسالتك للدعم.', reply_markup=customer_main_menu()); return

async def submit_payment(update, data, proof, ptype):
    async with SessionLocal() as db:
        m = await db.get(PaymentMethod, data['method_id']); p, created = await create_payment(db, data['customer_id'], data['phone_id'], m, data['reference'], proof, ptype)
        for admin_id in settings.admin_ids:
            from app.services.notification_service import queue_notification
            await queue_notification(db, admin_id, 'payment_new', f'💳 طلب دفع جديد {p.payment_code}.', f'payment-new:{p.id}')
        await db.commit(); await clear(db, update.effective_user.id)
    msg = f'✅ تم إرسال طلب الدفع للمراجعة.\n\nرقم الطلب: {p.payment_code}\nسيتم إشعارك بعد مراجعة الدفع.' if created else f'⏳ لديك طلب دفع قيد المراجعة بالفعل.\n\nرقم الطلب: {p.payment_code}'
    await update.message.reply_text(msg, reply_markup=customer_main_menu())

async def my_numbers(update, context):
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user); ns = await numbers(db, c.id)
        if not ns: await update.message.reply_text('📱 لا توجد أرقام مسجلة. اضغط «🛡️ حماية رقم».', reply_markup=customer_main_menu()); return
        lines, labels = ['📱 أرقامك:\n'], []
        for n in ns:
            s = await active_subscription(db, n.id); status = classify_subscription(s) if s else ('🟡 الحماية غير مفعلة' if n.status.value == 'inactive' else '🟠 موقوفة')
            lines += [f'📱 {display_phone(n.phone_number)}', f'📡 {n.telecom_company.name}', status]
            if s and s.ends_at: lines += [f'بداية الحماية: {s.starts_at:%Y-%m-%d}', f'نهاية الحماية: {s.ends_at:%Y-%m-%d}', f'الأيام المتبقية: {remaining(s)}']
            lines.append(''); labels.append(display_phone(n.phone_number))
    await update.message.reply_text('\n'.join(lines), reply_markup=phone_list_keyboard(labels))

async def activate_start(update, context):
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user); ns = await numbers(db, c.id); eligible = ns
        if not eligible: await update.message.reply_text('ℹ️ لا توجد أرقام مسجلة حاليًا.', reply_markup=customer_main_menu()); return
        labels = [display_phone(n.phone_number) for n in eligible]; await save(db, c.telegram_id, State.PHONE_SELECT, {'customer_id': c.id, 'phone_labels': labels})
    await update.message.reply_text('📱 اختر الرقم الذي تريد حمايته:', reply_markup=phone_list_keyboard(labels))

async def account(update, context):
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user); total, protected = await counts(db, c.id)
    await update.message.reply_text(f'👤 حسابي\n\nالاسم: {c.full_name or "غير مسجل"}\nالمستخدم: @{c.telegram_username or "غير متوفر"}\n\n📱 عدد الأرقام: {total}\n🛡️ الأرقام المحمية: {protected}', reply_markup=customer_main_menu())

async def support(update, context):
    async with SessionLocal() as db:
        c = await get_or_create_customer(db, update.effective_user); ts = await customer_tickets(db, c.id)
        open_ts = [t for t in ts if t.status != SupportStatus.closed]
        if open_ts:
            await save(db, c.telegram_id, State.SUPPORT_TICKET_SELECT, {'customer_id': c.id}); msg, kb = '💬 اختر تذكرة مفتوحة:', phone_list_keyboard([t.ticket_code for t in open_ts])
        else:
            await save(db, c.telegram_id, State.SUPPORT_SUBJECT, {'customer_id': c.id}); msg, kb = '💬 فتح تذكرة دعم\n\n✍️ اكتب موضوع المشكلة:', back_menu()
    await update.message.reply_text(msg, reply_markup=kb)

async def help_customer(update, context):
    async with SessionLocal() as db: fs = (await db.execute(select(FAQ).where(FAQ.is_active.is_(True)).order_by(FAQ.sort_order, FAQ.id))).scalars().all()
    txt = '❓ المساعدة\n\n' + ('\n\n'.join(f'س: {x.question}\nج: {x.answer}' for x in fs) if fs else 'استخدم «🛡️ حماية رقم» لإضافة رقم وطلب الحماية، و«💬 الدعم» للتواصل معنا.')
    await update.message.reply_text(txt, reply_markup=customer_main_menu())
