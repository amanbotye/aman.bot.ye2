from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from app.database import SessionLocal
from app.states import State
from app.keyboards import admin_menu, admin_back, phone_list_keyboard
from app.services.admin_service import is_admin, dashboard
from app.services.payment_service import approve_payment, reject_payment
from app.services.notification_service import queue_notification
from app.services.session_service import save, clear
from app.models import PaymentRequest, PaymentStatus, Customer, PhoneNumber, Subscription, SubscriptionStatus, Followup, FollowupStatus, SupportTicket, SupportStatus, SupportMessage, FAQ, SystemSetting, Notification, NotificationStatus, AuditLog, TelecomCompany, PaymentMethod

async def guard(update):
    async with SessionLocal() as db: return await is_admin(db, update.effective_user.id)

async def admin_entry(update, context):
    if not await guard(update): await update.message.reply_text('⛔ غير مصرح لك بالوصول.'); return
    async with SessionLocal() as db: await save(db, update.effective_user.id, State.ADMIN_MENU, {})
    await update.message.reply_text('🛡️ لوحة إدارة AMAN\n\nاختر القسم:', reply_markup=admin_menu())

async def dashboard_handler(update, context):
    if not await guard(update): return
    async with SessionLocal() as db: d = await dashboard(db)
    await update.message.reply_text(
        '📊 لوحة التحكم\n\n'
        f'👥 العملاء: {d["customers"]} (نشط: {d["active_customers"]})\n'
        f'📱 الأرقام: {d["phones"]} (محمية: {d["protected"]})\n'
        f'💳 المدفوعات المعلقة: {d["pending_payments"]}\n'
        f'🛡️ الاشتراكات النشطة: {d["active_subscriptions"]}\n'
        f'💬 التذاكر المفتوحة: {d["open_tickets"]}', reply_markup=admin_menu())

async def payments(update, context):
    if not await guard(update): return
    async with SessionLocal() as db:
        rows = (await db.execute(select(PaymentRequest, Customer, PhoneNumber).join(Customer, Customer.id == PaymentRequest.customer_id).join(PhoneNumber, PhoneNumber.id == PaymentRequest.phone_number_id).where(PaymentRequest.status == PaymentStatus.pending).order_by(PaymentRequest.created_at).limit(50))).all()
        labels = [p.payment_code for p, c, n in rows]
        await save(db, update.effective_user.id, State.ADMIN_PAYMENT_SELECT, {'codes': labels})
    if not rows: await update.message.reply_text('💳 لا توجد مدفوعات معلقة.', reply_markup=admin_menu()); return
    text = '💳 المدفوعات المعلقة:\n\n' + '\n'.join(f'{p.payment_code} — {c.full_name or "بدون اسم"} — {n.phone_number} — {p.amount} {p.currency}' for p,c,n in rows)
    await update.message.reply_text(text + '\n\nاختر الكود ثم أرسل: ✅ قبول AMAN-XXXXXX أو ❌ رفض AMAN-XXXXXX', reply_markup=phone_list_keyboard(labels))

async def admin_state(update, context, state, data):
    if not await guard(update): return
    text = (update.message.text or '').strip()
    uid = update.effective_user.id
    if state == State.ADMIN_PAYMENT_SELECT:
        async with SessionLocal() as db:
            p = (await db.execute(select(PaymentRequest).where(PaymentRequest.payment_code == text))).scalar_one_or_none()
            if not p: await update.message.reply_text('⚠️ اختر طلبًا صحيحًا.'); return
            c = await db.get(Customer, p.customer_id); n = await db.get(PhoneNumber, p.phone_number_id)
            await save(db, uid, State.ADMIN_MENU, {})
        await update.message.reply_text(
            f'💳 طلب دفع\n\nالكود: {p.payment_code}\nالعميل: {c.full_name or "-"}\nTelegram ID: {c.telegram_id}\nالرقم: {n.phone_number}\nالمبلغ: {p.amount} {p.currency}\nمرجع العملية: {p.transaction_reference}\nالإثبات: {"موجود" if p.proof_file_url else "غير موجود"}\n\nاستخدم:\n✅ قبول {p.payment_code}\n❌ رفض {p.payment_code}', reply_markup=admin_menu()); return
    if text.startswith('✅ قبول '):
        code = text[len('✅ قبول '):].strip()
        async with SessionLocal() as db:
            p = (await db.execute(select(PaymentRequest).where(PaymentRequest.payment_code == code))).scalar_one_or_none()
            if not p: await update.message.reply_text('⚠️ الطلب غير موجود.'); return
            result, status = await approve_payment(db, p.id, uid)
            if status == 'already_processed': await db.rollback(); await update.message.reply_text('⚠️ تم التعامل مع هذا الطلب مسبقًا.', reply_markup=admin_menu()); return
            if not result: await db.rollback(); await update.message.reply_text('❌ تعذر إكمال العملية.', reply_markup=admin_menu()); return
            c = await db.get(Customer, result.customer_id)
            await queue_notification(db, c.telegram_id, 'payment_approved', f'✅ تم قبول دفعتك {result.payment_code} وتفعيل الحماية لرقمك.', f'payment-approved:{result.id}')
            await db.commit()
        await update.message.reply_text('✅ تم قبول الدفع وتفعيل الاشتراك والرقم وإنشاء المتابعة.', reply_markup=admin_menu()); return
    if text.startswith('❌ رفض '):
        code = text[len('❌ رفض '):].strip()
        async with SessionLocal() as db:
            p = (await db.execute(select(PaymentRequest).where(PaymentRequest.payment_code == code))).scalar_one_or_none()
            if not p: await update.message.reply_text('⚠️ الطلب غير موجود.'); return
            await save(db, uid, State.ADMIN_REJECT_REASON, {'payment_id': p.id, 'code': code})
        await update.message.reply_text('✍️ اكتب سبب رفض طلب الدفع:', reply_markup=admin_back()); return
    if state == State.ADMIN_REJECT_REASON:
        async with SessionLocal() as db:
            p, status = await reject_payment(db, data['payment_id'], uid, text)
            if status == 'already_processed': await db.rollback(); await update.message.reply_text('⚠️ تم التعامل مع هذا الطلب مسبقًا.', reply_markup=admin_menu()); return
            c = await db.get(Customer, p.customer_id)
            await queue_notification(db, c.telegram_id, 'payment_rejected', f'❌ تم رفض طلب الدفع {p.payment_code}.\nالسبب: {p.rejection_reason}', f'payment-rejected:{p.id}')
            await db.commit(); await clear(db, uid)
        await update.message.reply_text('❌ تم رفض الدفع وإشعار العميل.', reply_markup=admin_menu()); return


async def section(update, context, name):
    if not await guard(update): return
    uid=update.effective_user.id
    async with SessionLocal() as db:
        if name=='customers':
            rows=(await db.execute(select(Customer).order_by(Customer.created_at.desc()).limit(20))).scalars().all()
            text='👥 العملاء\n\n'+('\n'.join(f'{c.id}. {c.full_name or "-"} — {c.telegram_id} — {c.status.value}' for c in rows) if rows else 'لا يوجد عملاء.')
        elif name=='numbers':
            rows=(await db.execute(select(PhoneNumber).order_by(PhoneNumber.created_at.desc()).limit(30))).scalars().all()
            text='📱 الأرقام\n\n'+('\n'.join(f'{x.id}. {x.phone_number} — {x.status.value} — عميل #{x.customer_id}' for x in rows) if rows else 'لا توجد أرقام.')
        elif name=='subscriptions':
            rows=(await db.execute(select(Subscription).order_by(Subscription.ends_at.desc()).limit(30))).scalars().all()
            text='🛡️ الاشتراكات\n\n'+('\n'.join(f'#{x.id} — رقم #{x.phone_number_id} — {x.status.value} — {x.starts_at:%Y-%m-%d} → {x.ends_at:%Y-%m-%d}' for x in rows if x.starts_at and x.ends_at) if rows else 'لا توجد اشتراكات.')
        elif name=='followups':
            rows=(await db.execute(select(Followup).order_by(Followup.due_at).limit(30))).scalars().all()
            text='🔄 المتابعة\n\n'+('\n'.join(f'#{x.id} — رقم #{x.phone_number_id} — {x.status.value} — {x.due_at:%Y-%m-%d}' for x in rows) if rows else 'لا توجد متابعات.')
        elif name=='support':
            rows=(await db.execute(select(SupportTicket).where(SupportTicket.status.in_([SupportStatus.new,SupportStatus.open])).order_by(SupportTicket.updated_at.desc()).limit(30))).scalars().all()
            text='💬 الدعم\n\n'+('\n'.join(f'{x.ticket_code} — عميل #{x.customer_id} — {x.subject} — {x.status.value}' for x in rows) if rows else 'لا توجد تذاكر مفتوحة.')
            await save(db,uid,State.ADMIN_TICKET_SELECT,{'codes':[x.ticket_code for x in rows]})
        elif name=='notifications':
            total=(await db.execute(select(func.count(Notification.id)))).scalar_one(); pending=(await db.execute(select(func.count(Notification.id)).where(Notification.status==NotificationStatus.pending))).scalar_one(); failed=(await db.execute(select(func.count(Notification.id)).where(Notification.status==NotificationStatus.failed))) .scalar_one()
            text=f'🔔 الإشعارات\n\nالإجمالي: {total}\nالمعلقة: {pending}\nالفاشلة: {failed}'
        elif name=='reports':
            d=await dashboard(db)
            approved=(await db.execute(select(func.count(PaymentRequest.id)).where(PaymentRequest.status==PaymentStatus.approved))).scalar_one()
            revenue=(await db.execute(select(func.coalesce(func.sum(PaymentRequest.amount),0)).where(PaymentRequest.status==PaymentStatus.approved))).scalar_one()
            text=f'📊 التقارير\n\nالعملاء: {d["customers"]}\nالأرقام: {d["phones"]}\nالاشتراكات النشطة: {d["active_subscriptions"]}\nالمدفوعات المقبولة: {approved}\nالإيرادات المسجلة: {revenue}\nالتذاكر المفتوحة: {d["open_tickets"]}'
        elif name=='settings':
            rows=(await db.execute(select(SystemSetting).order_by(SystemSetting.key))).scalars().all()
            text='⚙️ الإعدادات\n\n'+'\n'.join(f'{x.key} = {x.value}' for x in rows)+'\n\nلتعديل إعداد: اكتب key=value ثم أرسلها.'
            await save(db,uid,State.ADMIN_SETTINGS_VALUE,{})
        elif name=='faq':
            rows=(await db.execute(select(FAQ).order_by(FAQ.sort_order,FAQ.id))).scalars().all()
            text='❓ الأسئلة الشائعة\n\n'+('\n'.join(f'#{x.id} {"🟢" if x.is_active else "⚫"} {x.question}' for x in rows) if rows else 'لا توجد أسئلة.')+'\n\nلإضافة سؤال: اكتب FAQ: السؤال | الجواب'
        elif name=='audit':
            rows=(await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(30))).scalars().all()
            text='🧾 سجل العمليات\n\n'+('\n'.join(f'#{x.id} — {x.action} — {x.entity_type or "-"}#{x.entity_id or "-"} — {x.created_at:%Y-%m-%d %H:%M}' for x in rows) if rows else 'لا توجد سجلات.')
        elif name=='payments':
            return await payments(update,context)
        elif name=='dashboard':
            return await dashboard_handler(update,context)
        else:
            text='هذا القسم متاح، لكن اختر إجراءً من القائمة.'
    await update.message.reply_text(text,reply_markup=admin_menu())

async def admin_extended_state(update, context, state, data):
    if not await guard(update): return
    text=(update.message.text or '').strip();uid=update.effective_user.id
    if state==State.ADMIN_SETTINGS_VALUE and '=' in text:
        key,value=[x.strip() for x in text.split('=',1)]
        async with SessionLocal() as db:
            x=(await db.execute(select(SystemSetting).where(SystemSetting.key==key))).scalar_one_or_none()
            if not x: await update.message.reply_text('⚠️ الإعداد غير موجود.'); return
            await save(db,uid,State.ADMIN_SETTINGS_CONFIRM,{'key':key,'old':x.value,'new':value})
        await update.message.reply_text(f'⚙️ تأكيد التعديل\n\n{key}\nالقيمة الحالية: {data.get("old", "غير معروفة")}\nالقيمة الجديدة: {value}\n\nأرسل «✅ تأكيد التعديل» أو «🔙 رجوع».',reply_markup=admin_back());return
    if state==State.ADMIN_SETTINGS_CONFIRM:
        if text!='✅ تأكيد التعديل': await update.message.reply_text('⚠️ أرسل «✅ تأكيد التعديل» للتأكيد أو «🔙 رجوع».',reply_markup=admin_back());return
        async with SessionLocal() as db:
            x=(await db.execute(select(SystemSetting).where(SystemSetting.key==data['key']))).scalar_one_or_none()
            if not x: await update.message.reply_text('⚠️ الإعداد غير موجود.');return
            old=x.value;x.value=data['new'];await __import__('app.services.audit_service',fromlist=['audit']).audit(db,uid,'setting_update','system_setting',x.id,{'key':x.key,'value':old},{'key':x.key,'value':x.value});await db.commit();await clear(db,uid)
        await update.message.reply_text('✅ تم حفظ الإعداد وتسجيل العملية.',reply_markup=admin_menu());return
    if state==State.ADMIN_TICKET_SELECT:
        async with SessionLocal() as db:
            t=(await db.execute(select(SupportTicket).where(SupportTicket.ticket_code==text))).scalar_one_or_none()
            if not t:await update.message.reply_text('⚠️ التذكرة غير موجودة.');return
            msgs=(await db.execute(select(SupportMessage).where(SupportMessage.ticket_id==t.id).order_by(SupportMessage.created_at))).scalars().all();await save(db,uid,State.ADMIN_TICKET_REPLY,{'ticket_id':t.id})
        transcript='\n'.join(f'{"👨‍💼" if m.sender_is_admin else "👤"}: {m.text or "[مرفق]"}' for m in msgs[-15:])
        await update.message.reply_text(f'💬 {t.ticket_code}\nالموضوع: {t.subject}\n\n{transcript}\n\n✉️ اكتب ردك:',reply_markup=admin_back());return
    if state==State.ADMIN_TICKET_REPLY:
        async with SessionLocal() as db:
            t=(await db.execute(select(SupportTicket).where(SupportTicket.id==data['ticket_id']).with_for_update())).scalar_one_or_none()
            if not t:return
            if t.status==SupportStatus.closed:await update.message.reply_text('🔒 التذكرة مغلقة.');return
            db.add(SupportMessage(ticket_id=t.id,sender_telegram_id=uid,sender_is_admin=True,text=text));t.status=SupportStatus.open
            c=await db.get(Customer,t.customer_id);await queue_notification(db,c.telegram_id,'support_reply',f'💬 رد جديد على تذكرتك {t.ticket_code}:\n{text}',f'support-reply:{t.id}:{int(__import__("time").time())}')
            await db.commit();await clear(db,uid)
        await update.message.reply_text('✅ تم إرسال الرد للعميل.',reply_markup=admin_menu());return
    if text.startswith('FAQ:'):
        body=text[4:].strip()
        if '|' not in body:await update.message.reply_text('الصيغة: FAQ: السؤال | الجواب');return
        q,a=[x.strip() for x in body.split('|',1)]
        async with SessionLocal() as db:db.add(FAQ(question=q,answer=a,is_active=True));await db.commit()
        await update.message.reply_text('✅ تمت إضافة السؤال.',reply_markup=admin_menu());return
