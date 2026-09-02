from telegram import ReplyKeyboardMarkup
from sqlalchemy import select
from ..models import TelecomCompany, Subscription, PhoneStatus, CustomerStatus, FAQItem
from ..states import States
from ..keyboards import customer_home,back_home,confirm,phone_actions
from ..utils import normalize_yemen_phone

async def start_customer(update,context,session,services):
 c=await services["customer"].get_or_create(update.effective_user.id,update.effective_user.username,update.effective_user.first_name,update.effective_user.last_name)
 if c.status!=CustomerStatus.ACTIVE: raise ValueError("حسابك غير متاح حاليًا. تواصل مع الدعم.")
 context.user_data["mode"]="customer"
 await update.message.reply_text("مرحبًا بك في أمان 🛡️\nحماية ومتابعة أرقامك اليمنية.",reply_markup=customer_home())

def set_state(context,state,**data):
 context.user_data["state"]=state; context.user_data.update(data)

async def protect(update,context,session,services):
 c=await services["customer"].get_or_create(update.effective_user.id)
 context.user_data["customer_id"]=c.id
 if not c.full_name:
  set_state(context,States.CUSTOMER_NAME); await update.message.reply_text("نحتاج اسمك الكامل مرة واحدة فقط لربط أرقامك بحسابك.",reply_markup=back_home()); return
 companies=list((await session.scalars(select(TelecomCompany).where(TelecomCompany.active.is_(True)).order_by(TelecomCompany.sort_order,TelecomCompany.id))).all())
 if not companies: raise ValueError("لا توجد شركات اتصالات متاحة حاليًا.")
 set_state(context,States.CHOOSE_COMPANY,companies={x.name:x.id for x in companies})
 await update.message.reply_text("اختر شركة الاتصالات:",reply_markup=ReplyKeyboardMarkup([[x.name] for x in companies]+[["🔙 رجوع","🏠 الرئيسية"]],resize_keyboard=True))

async def my_phones(update,context,session,services):
 c=await services["customer"].get_or_create(update.effective_user.id); phones=await services["phone_repo"].list_customer(c.id,20,0)
 if not phones: await update.message.reply_text("لا توجد أرقام مسجلة لديك.",reply_markup=customer_home()); return
 ids=[p.id for p in phones]
 subs=list((await session.scalars(select(Subscription).where(Subscription.phone_number_id.in_(ids)).order_by(Subscription.end_at.desc()))).all())
 latest={}
 for sub in subs: latest.setdefault(sub.phone_number_id,sub)
 lines=["📱 أرقامك:"]
 for p in phones:
  sub=latest.get(p.id); end=sub.end_at.date().isoformat() if sub else "—"
  lines.append(f"\n📱 {p.normalized_phone}\n📡 {p.telecom_company.name if p.telecom_company else '—'}\n🛡️ {p.status.value}\n📅 الانتهاء: {end}")
 await update.message.reply_text("".join(lines),reply_markup=customer_home())

async def account(update,context,session,services):
 c=await services["customer"].get_or_create(update.effective_user.id); await update.message.reply_text(f"👤 حسابي\n\nالاسم: {c.full_name or 'غير محفوظ'}\nالمستخدم: @{c.username or '—'}\nمعرّف Telegram: {c.telegram_id}",reply_markup=customer_home())

async def faq(update,context,session,services):
 rows=list((await session.scalars(select(FAQItem).where(FAQItem.active.is_(True)).order_by(FAQItem.sort_order,FAQItem.id))).all())
 if not rows: await update.message.reply_text("لا توجد أسئلة شائعة حاليًا.",reply_markup=customer_home()); return
 text="\n\n".join(f"❓ {x.question}\n{x.answer}" for x in rows); await update.message.reply_text(text,reply_markup=customer_home())

async def text_router(update,context,session,services):
 text=(update.message.text or "").strip(); state=context.user_data.get("state",States.IDLE)
 if text in ("🔙 رجوع","🏠 الرئيسية"):
  set_state(context,States.IDLE); await update.message.reply_text("تم الرجوع.",reply_markup=customer_home()); return
 if state==States.CUSTOMER_NAME:
  c=await services["customer"].get_or_create(update.effective_user.id); await services["customer"].set_name(c,text)
  companies=list((await session.scalars(select(TelecomCompany).where(TelecomCompany.active.is_(True)).order_by(TelecomCompany.sort_order,TelecomCompany.id))).all())
  if not companies: raise ValueError("لا توجد شركات اتصالات متاحة حاليًا.")
  set_state(context,States.CHOOSE_COMPANY,companies={x.name:x.id for x in companies})
  await update.message.reply_text("✅ تم حفظ اسمك. اختر شركة الاتصالات:",reply_markup=ReplyKeyboardMarkup([[x.name] for x in companies]+[["🔙 رجوع","🏠 الرئيسية"]],resize_keyboard=True)); return
 if state==States.CHOOSE_COMPANY:
  cid=context.user_data.get("companies",{}).get(text)
  if not cid: await update.message.reply_text("اختر شركة من القائمة."); return
  set_state(context,States.PHONE_INPUT,company_id=cid); await update.message.reply_text("أرسل رقم الهاتف الذي تريد حمايته.",reply_markup=back_home()); return
 if state==States.PHONE_INPUT:
  n=normalize_yemen_phone(text); company=await session.get(TelecomCompany,context.user_data.get("company_id"))
  if not company or not company.active: raise ValueError("شركة الاتصالات غير متاحة.")
  set_state(context,States.PHONE_CONFIRM,phone=n,company_name=company.name); await update.message.reply_text(f"📱 الرقم: {n}\n📡 الشركة: {company.name}\nهل تريد تأكيد الرقم؟",reply_markup=confirm()); return
 if state==States.PHONE_CONFIRM:
  if text=="✏️ تعديل الرقم": set_state(context,States.PHONE_INPUT); await update.message.reply_text("أرسل الرقم من جديد.",reply_markup=back_home()); return
  if text!="✅ تأكيد الرقم": await update.message.reply_text("اختر تأكيد الرقم أو تعديل الرقم.",reply_markup=confirm()); return
  company=await session.get(TelecomCompany,context.user_data["company_id"])
  if not company or not company.active: raise ValueError("شركة الاتصالات غير متاحة.")
  c=await services["customer"].get_or_create(update.effective_user.id); p=await services["phone"].register(c.id,company.id,context.user_data["phone"]); set_state(context,States.PHONE_ACTION,phone_id=p.id)
  await update.message.reply_text(f"✅ تم تسجيل الرقم بنجاح.\n📱 الرقم: {p.normalized_phone}\n🟡 الحماية غير مفعلة.",reply_markup=phone_actions()); return
 if state==States.PHONE_ACTION: return
 await update.message.reply_text("استخدم القائمة الرئيسية لاختيار الخدمة.",reply_markup=customer_home())
