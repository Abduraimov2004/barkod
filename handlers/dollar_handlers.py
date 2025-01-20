from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from states import States
from keyboards import dollar_menu_keyboard, main_menu_keyboard
from database import (
    get_exchange_rate, set_exchange_rate
)
from config import ADMIN_ID

async def dollar_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    if text == "Kursni ko'rish":
        rate = get_exchange_rate()
        await update.message.reply_text(
            f"Joriy dollar kursi: {rate}",
            reply_markup=dollar_menu_keyboard()
        )
        return States.DOLLAR_MENU

    elif text == "Kursni o'zgartirish":
        if not is_admin:
            await update.message.reply_text(
                "Siz admin emassiz, kursni o'zgarta olmaysiz!",
                reply_markup=dollar_menu_keyboard()
            )
            return States.DOLLAR_MENU

        await update.message.reply_text(
            "Yangi dollar kursini kiriting (masalan, 11000 yoki 10995.5):",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.EXCHANGE_RATE_INPUT

    elif text == "Orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytildi.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    else:
        await update.message.reply_text(
            "Iltimos, menyudagi tugmalardan birini tanlang.",
            reply_markup=dollar_menu_keyboard()
        )
        return States.DOLLAR_MENU


async def exchange_rate_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    text = update.message.text
    if text == "Orqaga":
        await update.message.reply_text(
            "Dollar kursi menyusiga qaytildi.",
            reply_markup=dollar_menu_keyboard()
        )
        return States.DOLLAR_MENU

    try:
        new_rate = float(text)
    except ValueError:
        await update.message.reply_text(
            "Iltimos, to'g'ri kurs (raqam) kiriting yoki Orqaga bosing:",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.EXCHANGE_RATE_INPUT

    set_exchange_rate(new_rate)
    await update.message.reply_text(
        f"Dollar kursi muvaffaqiyatli yangilandi: {new_rate}",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )
    return States.MAIN_MENU
