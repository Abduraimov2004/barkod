# handlers/admin_handlers.py

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from states import States
from keyboards import admin_menu_keyboard, import_export_keyboard, korzinka_menu_keyboard, main_menu_keyboard
from database import (
    get_product_by_barcode, delete_product, fetch_product_from_openfda, add_product, update_weight_price_finalprice,
    supabase, get_exchange_rate
)
from config import ADMIN_ID

logger = logging.getLogger(__name__)

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin menu: update, delete, XLSX import/export, Korzinka, Back
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "Siz admin emassiz!",
            reply_markup=main_menu_keyboard(is_admin=False)  # Changed to main menu
        )
        return States.MAIN_MENU

    text = update.message.text.strip()
    if text == "Mahsulotni yangilash":
        await update.message.reply_text("Yangilash uchun barkod kiriting:")
        return States.UPDATE_PRODUCT

    elif text == "Mahsulotni o'chirish":
        await update.message.reply_text("O'chirish uchun barkod kiriting:")
        return States.DELETE_PRODUCT

    elif text == "XLSX import/export":
        await update.message.reply_text(
            "XLSX import/export menyusi:",
            reply_markup=import_export_keyboard()
        )
        return States.IMPORT_EXPORT

    elif text == "Korzinka":
        await update.message.reply_text(
            "Korzinka menyusi:",
            reply_markup=korzinka_menu_keyboard()
        )
        return States.KORZINKA_MENU

    elif text == "Orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytdik.",
            reply_markup=main_menu_keyboard(is_admin=True)
        )
        return States.MAIN_MENU

    else:
        await update.message.reply_text(
            "Noma'lum buyruq.",
            reply_markup=admin_menu_keyboard()
        )
        return States.ADMIN_MENU

async def update_product_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1) Enter barcode -> if found, next step: update name
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Barkod faqat raqam bo'lishi kerak!")
        return States.UPDATE_PRODUCT

    barcode = int(text)
    product = get_product_by_barcode(barcode)
    if not product:
        # Product not found in local DB, search via OpenFDA
        await update.message.reply_text("Mahsulot lokal bazada topilmadi. OpenFDA orqali qidirilyapti...")
        product_data = fetch_product_from_openfda(barcode)
        if product_data:
            # Product found via OpenFDA, add to local DB
            add_product(
                name=product_data['name'],
                artikul=product_data['artikul'],
                barcode=product_data['barcode'],
                category=product_data['category'],
                postavshik=product_data['postavshik'],
                stock=product_data['stock'],
                cena_postavki=product_data['cena_postavki'],
                cena_prodaji=product_data['cena_prodaji'],
                skidka=product_data['skidka'],
                brend=product_data['brend'],
                srok=product_data['srok'],
                edinitsa_izmereniya=product_data['edinitsa_izmereniya']
            )
            product = get_product_by_barcode(barcode)
            await update.message.reply_text(
                f"OpenFDA orqali mahsulot topildi va lokal bazaga qo'shildi: {product['name']}\n"
                "Yangi nomni kiriting (bo'sh qoldirsangiz o'zgarmaydi):"
            )
        else:
            await update.message.reply_text("Mahsulot OpenFDA da topilmadi. /cancel yoki Orqaga.")
            return States.ADMIN_MENU

    if product:
        context.user_data['upd_product_id'] = product['id']
        context.user_data['upd_barcode'] = product['barcode']
        old_name = product['name']

        await update.message.reply_text(
            f"Mahsulot topildi: {old_name}\n"
            "Yangi nomni kiriting (bo'sh qoldirsangiz o'zgarmaydi):"
        )
        return States.UPDATE_PRODUCT_NAME
    else:
        await update.message.reply_text("Mahsulot topilmadi.")
        return States.ADMIN_MENU

async def update_product_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    2) After updating name (optional), ask for weight
    """
    text = update.message.text.strip()
    if text:
        context.user_data['upd_new_name'] = text
    else:
        context.user_data['upd_new_name'] = None

    await update.message.reply_text(
        "Yangi og'irlikni (float) kiriting (bo'sh bo'lsa o'zgarmaydi):"
    )
    return States.UPDATE_PRODUCT_WEIGHT

async def update_product_weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    3) After weight, ask for price (USD)
    """
    text = update.message.text.strip()
    new_weight = None
    if text:
        try:
            new_weight = float(text)
        except ValueError:
            await update.message.reply_text("Og'irlik faqat raqam bo'lishi kerak!")
            return States.UPDATE_PRODUCT_WEIGHT

    context.user_data['upd_new_weight'] = new_weight

    await update.message.reply_text(
        "Yangi narx (USD) kiriting (bo'sh bo'lsa o'zgarmaydi):"
    )
    return States.UPDATE_PRODUCT_PRICE

async def update_product_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    4) After price, calculate final_price and update the product
    """
    text = update.message.text.strip()
    new_price = None
    if text:
        try:
            new_price = float(text)
        except ValueError:
            await update.message.reply_text("Narx faqat raqam bo'lishi kerak!")
            return States.UPDATE_PRODUCT_PRICE

    context.user_data['upd_new_price'] = new_price

    await update.message.reply_text("Yangilash yakunlanmoqda...")

    # Get data from user_data
    pid = context.user_data.get('upd_product_id')
    new_name = context.user_data.get('upd_new_name')
    new_weight = context.user_data.get('upd_new_weight')
    new_price_val = context.user_data.get('upd_new_price')

    # Fetch the product again to get current data
    product = get_product_by_barcode(context.user_data.get('upd_barcode'))
    if not product:
        await update.message.reply_text("Xatolik: mahsulot topilmadi.")
        return States.ADMIN_MENU

    old_weight = product.get('weight') or 0
    old_price = product.get('price') or 0

    # 1) Update name if provided
    if new_name:
        update_product_field = {'name': new_name}
        try:
            supabase_response = supabase.table('products').update(update_product_field).eq('id', pid).execute()
            if supabase_response.status_code >= 300:
                await update.message.reply_text("Xatolik: nomni yangilashda muammo yuz berdi.")
                return States.ADMIN_MENU
        except Exception as e:
            logger.error(f"Error updating product name: {e}")
            await update.message.reply_text("Nomni yangilashda xatolik yuz berdi.")
            return States.ADMIN_MENU

    # 2) Calculate final_weight and final_price
    final_weight = new_weight if new_weight is not None else old_weight
    final_price_usd = new_price_val if new_price_val is not None else old_price

    # final_price = (price + 13.5 * weight) * exchange_rate
    rate = get_exchange_rate()
    calc_final = (final_price_usd + 13.5 * final_weight) * rate

    # Update the product
    update_weight_price_finalprice(
        barcode=product['barcode'],
        weight=final_weight,
        price=final_price_usd,
        final_price=calc_final
    )

    await update.message.reply_text("Mahsulot muvaffaqiyatli yangilandi.")
    return States.ADMIN_MENU

async def delete_product_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle product deletion by barcode
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Barkod faqat raqam bo'lishi kerak!")
        return States.DELETE_PRODUCT

    barcode = int(text)
    product = get_product_by_barcode(barcode)
    if not product:
        await update.message.reply_text("Mahsulot topilmadi.")
        return States.ADMIN_MENU

    delete_product(barcode)
    await update.message.reply_text("Mahsulot o'chirildi.")
    return States.ADMIN_MENU
