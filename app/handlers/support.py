from ..states import States
from ..keyboards import back_home,customer_home,kb
async def start_support(update,context):
    context.user_data["state"]=States.SUPPORT_MENU
    await update.message.reply_text("💬 الدعم\nاختر: فتح تذكرة جديدة أو متابعة تذكرة سابقة.",reply_markup=kb([["تذكرة جديدة","تذاكري"],["🔙 رجوع","🏠 الرئيسية"]]))
async def support_router(update,context,session,services):
    text=(update.message.text or "").strip(); state=context.user_data.get("state")
    if text in ("🔙 رجوع","🏠 الرئيسية"):
        context.user_data["state"]="IDLE"; await update.message.reply_text("تم الرجوع.",reply_markup=customer_home()); return
    c=await services["customer"].get_or_create(update.effective_user.id)
    if state==States.SUPPORT_MENU:
        if text=="تذكرة جديدة": context.user_data["state"]=States.SUPPORT_SUBJECT; await update.message.reply_text("اكتب عنوان المشكلة.",reply_markup=back_home()); return
        if text=="تذاكري":
            rows=await services["support_repo"].list_customer(c.id,20,0); context.user_data["state"]=States.SUPPORT_TICKET; await update.message.reply_text("\n".join(f"#{t.id} | {t.status.value} | {t.subject}" for t in rows) or "لا توجد تذاكر.",reply_markup=back_home()); return
    if state==States.SUPPORT_SUBJECT:
        context.user_data.update(support_subject=text,state=States.SUPPORT_MESSAGE); await update.message.reply_text("اكتب رسالتك.",reply_markup=back_home()); return
    if state==States.SUPPORT_MESSAGE:
        t=await services["support"].create(c.id,context.user_data.get("support_subject","دعم")); await services["support"].message(t.id,update.effective_user.id,text); context.user_data["state"]="IDLE"; await update.message.reply_text(f"✅ تم إنشاء التذكرة #{t.id}.",reply_markup=customer_home()); return
    if state==States.SUPPORT_TICKET:
        try: tid=int(text)
        except ValueError: await update.message.reply_text("أرسل رقم التذكرة."); return
        t=await services["support_repo"].get(tid)
        if not t or t.customer_id!=c.id: raise ValueError("التذكرة غير موجودة في حسابك.")
        msgs=await services["support_repo"].messages(tid,50); context.user_data["support_ticket_id"]=tid; context.user_data["state"]=States.SUPPORT_TICKET_MESSAGE
        await update.message.reply_text(f"#{tid} | {t.status.value}\n{t.subject}\n\n"+"\n".join(f"{m.sender_telegram_id}: {m.message_text}" for m in msgs)+"\n\nأرسل ردك.",reply_markup=back_home()); return
    if state==States.SUPPORT_TICKET_MESSAGE:
        tid=context.user_data["support_ticket_id"]; await services["support"].message(tid,update.effective_user.id,text); context.user_data["state"]="IDLE"; await update.message.reply_text("✅ تم إرسال رسالتك.",reply_markup=customer_home()); return
