from telegram import Update
from telegram.ext import ContextTypes
from ..keyboards import customer_home,admin_home
async def home(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا بك في أمان 🛡️",reply_markup=customer_home())
