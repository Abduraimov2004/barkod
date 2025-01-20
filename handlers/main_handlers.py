# handlers/main_handlers.py

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID
from states import States
from keyboards import main_menu_keyboard, dollar_menu_keyboard, reports_menu_keyboard
from database import (
    get_total_products_count, get_all_products, get_exchange_rate, get_product_by_barcode,
    update_weight_price_finalprice, add_product
)

from keyboards import admin_menu_keyboard, price_done_inline_keyboard, add_product_done_keyboard, view_products_inline_keyboard

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    await update.message.reply_text(
        "Salom! Botga xush kelibsiz.\nQuyidagi menyudan tanlang:",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )
    return States.MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    if text == "Barkod bilan qidirish":
        await update.message.reply_text("Barkodni kiriting:",)
        return States.BARCODE_INPUT

    elif text == "Dollar kursi":
        await update.message.reply_text(
            "Dollar kursi menyusi:",
            reply_markup=dollar_menu_keyboard()
        )
        return States.DOLLAR_MENU

    elif text == "Maxsulot qo'shish":
        # Start asking for product details
        await update.message.reply_text("Mahsulot nomini kiriting (name):")
        return States.ADD_PRODUCT_NAME

    elif text == "Barcha mahsulotlar":
        total = get_total_products_count()
        if total == 0:
            await update.message.reply_text(
                "Hozircha hech qanday mahsulot mavjud emas!",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return States.MAIN_MENU

        total_pages = (total // 10) + (1 if total % 10 else 0)
        page = 1
        products = get_all_products(limit=10, offset=0)

        await send_products(update, context, products, page, total_pages)
        return States.VIEW_PRODUCTS

    elif text == "Hisobotlar":
        await update.message.reply_text(
            "Hisobot menyusi:",
            reply_markup=reports_menu_keyboard()
        )
        return States.REPORTS

    elif text == "Admin panel":
        if is_admin:
            await update.message.reply_text(
                "Admin panel:",
                reply_markup=admin_menu_keyboard()
            )
            return States.ADMIN_MENU
        else:
            await update.message.reply_text(
                "Siz admin emassiz!",
                reply_markup=main_menu_keyboard(is_admin=False)
            )
            return States.MAIN_MENU

    else:
        if text == "Orqaga":
            # Return to main menu
            await update.message.reply_text(
                "Asosiy menyu:",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return States.MAIN_MENU

        # Unknown input
        await update.message.reply_text(
            "Iltimos, menyudan tanlang.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

async def send_products(update: Update, context: ContextTypes.DEFAULT_TYPE, products, page, total_pages):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    msg = f"Barcha mahsulotlar (sahifa {page}/{total_pages}):\n\n"
    start_index = (page - 1) * 10
    for idx, p in enumerate(products, start=start_index + 1):
        pid = p.get('id')
        name = p.get('name')
        artikul = p.get('artikul')
        barcode = p.get('barcode')
        category = p.get('category')
        postavshik = p.get('postavshik')
        stock = p.get('stock')
        c_post = p.get('cena_postavki')
        c_prod = p.get('cena_prodaji')
        skidka = p.get('skidka')
        brend = p.get('brend')
        srok = p.get('srok')
        edi = p.get('edinitsa_izmereniya')
        weight = p.get('weight')
        price = p.get('price')
        final_p = p.get('final_price')

        msg += (
            f"{idx}. {name}\n"
            f"   Artikul: {artikul}\n"
            f"   Barkod: {barcode}\n"
            f"   Category: {category}\n"
            f"   Postavshik: {postavshik}\n"
            f"   Stock: {stock}\n"
            f"   Cena_postavki: {c_post}\n"
            f"   Cena_prodaji: {c_prod}\n"
            f"   Skidka: {skidka}\n"
            f"   Brend: {brend}\n"
            f"   Srok: {srok}\n"
            f"   Edinitsa: {edi}\n"
            f"   Weight: {weight}\n"
            f"   Price(USD): {price}\n"
            f"   Final(so'm): {final_p}\n\n"
        )

    reply_markup = view_products_inline_keyboard(page, total_pages)
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def view_products_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    await query.answer()

    if data.startswith("page_"):
        from database import get_all_products, get_total_products_count
        try:
            page = int(data.split("_")[1])
        except ValueError:
            logger.error(f"Invalid page number in callback data: {data}")
            await query.answer("Invalid page number.", show_alert=True)
            return States.VIEW_PRODUCTS

        total = get_total_products_count()
        total_pages = (total // 10) + (1 if total % 10 else 0)
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * 10
        products = get_all_products(limit=10, offset=offset)
        await send_products_inline(query, context, products, page, total_pages)
        return States.VIEW_PRODUCTS

    elif data == "back":
        await query.edit_message_text("Asosiy menyuga qaytildi.")
        await query.message.reply_text(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    else:
        await query.edit_message_text("Noma'lum tugma bosildi.")
        await query.message.reply_text(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

async def send_products_inline(query, context, products, page, total_pages):
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    msg = f"Barcha mahsulotlar (sahifa {page}/{total_pages}):\n\n"
    start_index = (page - 1) * 10
    for idx, p in enumerate(products, start=start_index + 1):
        pid = p.get('id')
        name = p.get('name')
        barcode = p.get('barcode')
        price = p.get('price')
        final_p = p.get('final_price')

        msg += (
            f"{idx}. {name}\n"
            f"   Barkod: {barcode}\n"
            f"   Price(USD): {price}\n"
            f"   Final(so'm): {final_p}\n\n"
        )

    reply_markup = view_products_inline_keyboard(page, total_pages)
    await query.edit_message_text(msg, reply_markup=reply_markup)
