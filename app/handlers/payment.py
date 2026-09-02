from telegram import ReplyKeyboardMarkup
from sqlalchemy import select
from ..models import PaymentMethod, PhoneNumber
from ..states import States
from ..keyboards import back_home,customer_home

async def begin_payment(update,context,session,services,phone_id):
    phone=await session.get(PhoneNumber,phone_id)
    if not phone or phone.customer_id!=context.user_data.get("customer_id"): raise ValueError("الرقم غير متاح.")
    methods=list((await session.scalars(select(PaymentMethod).where(PaymentMethod.active.is_(True)).order_by(PaymentMethod.sort_order,PaymentMethod.id))).all())
    if not methods: raise ValueError("لا توجد طرق دفع متاحة حاليًا.")
    context.user_data.update(payment_phone_id=phone_id,payment_methods={m.name:m.id for m in methods},state=States.PAYMENT_METHOD)
    price=await services["settings"].get("service_price"); currency=await services["settings"].get("currency")
    await update.message.reply_text(f"💳 قيمة الحماية: {price} {currency}\nاختر طريقة الدفع:",reply_markup=ReplyKeyboardMarkup([[m.name] for m in methods]+[["🔙 رجوع","🏠 الرئيسية"]],resize_keyboard=True))

def _proof_from_update(update, max_mb=10):
    msg=update.message
    if msg.photo:
        photo=msg.photo[-1]
        if getattr(photo,"file_size",None) and photo.file_size > max_mb*1024*1024:
            raise ValueError(f"حجم الإثبات يتجاوز {max_mb}MB.")
        return photo.file_id
    if msg.document:
        if msg.document.file_size and msg.document.file_size > max_mb*1024*1024: raise ValueError(f"حجم الإثبات يتجاوز {max_mb}MB.")
        if msg.document.mime_type and not (msg.document.mime_type.startswith("image/") or msg.document.mime_type=="application/pdf"): raise ValueError("صيغة الإثبات يجب أن تكون صورة أو PDF.")
        return msg.document.file_id
    return None

async def _create(update,context,services,proof):
    c=await services["customer"].get_or_create(update.effective_user.id); context.user_data["customer_id"]=c.id
    req=await services["payment"].create_request(c.id,context.user_data["payment_phone_id"],context.user_data["payment_method_id"],context.user_data["payment_reference"],proof)
    context.user_data["state"]="IDLE"; context.user_data["admin_payment_created"]=req.id
    await update.message.reply_text(f"✅ تم إرسال طلب الدفع رقم #{req.id}.\nالحالة: قيد المراجعة.",reply_markup=customer_home())
    return req

async def payment_router(update,context,session,services):
    text=(update.message.text or "").strip(); state=context.user_data.get("state")
    if text in ("🔙 رجوع","🏠 الرئيسية"):
        context.user_data["state"]="IDLE"; await update.message.reply_text("تم الرجوع.",reply_markup=customer_home()); return None
    if state==States.PAYMENT_METHOD:
        mid=context.user_data.get("payment_methods",{}).get(text)
        if not mid: await update.message.reply_text("اختر طريقة دفع من القائمة."); return None
        method=await session.get(PaymentMethod,mid)
        context.user_data.update(payment_method_id=mid,payment_requires_proof=method.requires_proof,state=States.PAYMENT_REFERENCE)
        await update.message.reply_text(f"{method.name}\nاسم الحساب: {method.account_name}\nرقم الحساب: {method.account_number}\n\n{method.instructions}\n\nأرسل رقم/مرجع العملية:",reply_markup=back_home()); return None
    if state==States.PAYMENT_REFERENCE:
        if len(text)<2 or len(text)>255: await update.message.reply_text("أرسل مرجع العملية بشكل صحيح."); return None
        context.user_data.update(payment_reference=text,state=States.PAYMENT_PROOF)
        await update.message.reply_text("أرسل صورة أو PDF لإثبات الدفع." if context.user_data.get("payment_requires_proof") else "يمكنك إرسال صورة/PDF للإثبات، أو اكتب: تخطي",reply_markup=back_home()); return None
    if state==States.PAYMENT_PROOF:
        if text.lower()=="تخطي" and not context.user_data.get("payment_requires_proof"):
            return await _create(update,context,services,None)
        if context.user_data.get("payment_requires_proof"):
            await update.message.reply_text("إثبات الدفع مطلوب لهذه الطريقة. أرسل صورة أو PDF."); return None
        await update.message.reply_text("أرسل صورة/PDF أو اكتب: تخطي."); return None
    return None

async def proof_router(update,context,session,services):
    if context.user_data.get("state")!=States.PAYMENT_PROOF:return False
    max_mb=await services["settings"].get_int("proof_max_size_mb")
    proof=_proof_from_update(update,max_mb)
    if not proof:return False
    await _create(update,context,services,proof); return True
