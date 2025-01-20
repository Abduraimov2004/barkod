# handlers/reports_handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from states import States
from keyboards import reports_menu_keyboard, main_menu_keyboard
from config import ADMIN_ID
from database import get_products_statistics

import logging

logger = logging.getLogger(__name__)

async def reports_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    text = update.message.text.strip()
    if text == "Hisobotni ko'rish":
        stats = get_products_statistics()
        msg = "Hisobot:\n"
        msg += f"Eng qimmat final_price: {stats['max_price'] or 'N/A'} so'm\n"
        msg += f"Eng arzon final_price: {stats['min_price'] or 'N/A'} so'm\n"
        msg += f"Umumiy stock: {stats['total_stock'] or 0}\n"
        msg += f"O'rtacha final_price: {stats['avg_price'] or 'N/A'} so'm\n"

        await update.message.reply_text(
            msg,
            reply_markup=reports_menu_keyboard()
        )
        return States.REPORTS

    elif text == "Orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytdik.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU
    else:
        await update.message.reply_text("Noma'lum buyruq.")
        return States.REPORTS
