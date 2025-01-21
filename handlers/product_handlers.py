import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from states import States
from keyboards import (
    main_menu_keyboard, price_done_inline_keyboard,
    add_product_done_keyboard, view_products_inline_keyboard
)
from config import ADMIN_ID
from database import (
    get_product_by_barcode, update_weight_price_finalprice,
    add_product, get_all_products, get_exchange_rate,
    get_total_products_count
)

logger = logging.getLogger(__name__)

# ---------- BARKOD QIDIRISH -> PRICE -> WEIGHT -> FINAL_PRICE ----------
async def barcode_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    text = update.message.text.strip()

    if text.lower() == "orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytildi.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    if not text.isdigit():
        await update.message.reply_text(
            "Barkod faqat raqam bo'lishi kerak yoki Orqaga bosing:",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.BARCODE_INPUT

    barcode = int(text)
    product = get_product_by_barcode(barcode)
    if product:
        context.user_data['barcode'] = barcode
        context.user_data['product_name'] = product['name']

        if product.get('weight') is None:
            # Weight is null, prompt for weight first
            await update.message.reply_text(
                f"Mahsulot topildi: {product['name']}\n"
                "Og'irlikni (weight) kiriting (masalan, 1.0 yoki 0.5):",
                reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
            )
            return States.WEIGHT_INPUT
        else:
            # Weight exists, prompt directly for price
            await update.message.reply_text(
                f"Mahsulot topildi: {product['name']}\n"
                "Narxni (USD) kiriting yoki Orqaga bosing:",
                reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
            )
            return States.PRICE_INPUT
    else:
        await update.message.reply_text(
            "Bunday barkod topilmadi. Qayta kiritish yoki Orqaga bosing.",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.BARCODE_INPUT

async def weight_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    if text.lower() == "orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytildi.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    try:
        weight_val = float(text)
        if weight_val <= 0:
            raise ValueError("Weight must be positive.")
    except ValueError:
        await update.message.reply_text(
            "Iltimos, to'g'ri og'irlik kiriting yoki Orqaga bosing:",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.WEIGHT_INPUT

    context.user_data['usd_price'] = None  # Reset in case of re-entry
    context.user_data['weight_val'] = weight_val

    # Prompt for price next
    await update.message.reply_text(
        "Narxni (USD) kiriting yoki Orqaga bosing:",
        reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
    )
    return States.PRICE_INPUT





async def price_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    if text.lower() == "orqaga":
        await update.message.reply_text(
            "Asosiy menyuga qaytildi.",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    try:
        usd_price = float(text)
        if usd_price < 0:
            raise ValueError("Price cannot be negative.")
    except ValueError:
        await update.message.reply_text(
            "Iltimos, to'g'ri narx kiriting yoki Orqaga bosing:",
            reply_markup=ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)
        )
        return States.PRICE_INPUT

    context.user_data['usd_price'] = usd_price

    # If weight was not previously set (i.e., user didn't input weight), keep it as is
    weight_val = context.user_data.get('weight_val')

    # Fetch barcode from context.user_data
    barcode = context.user_data.get('barcode')
    if weight_val is None:
        if barcode is None:
            await update.message.reply_text(
                "Xatolik: mahsulot barkodi topilmadi. Iltimos, yangi mahsulotni qo'shishni boshlang.",
                reply_markup=main_menu_keyboard(is_admin=is_admin),
            )
            return States.MAIN_MENU

        # Fetch existing weight from the database
        product = get_product_by_barcode(barcode)
        weight_val = product.get('weight') if product else 0.0

    # Calculate final_price
    exchange_rate = get_exchange_rate()
    final_price = round((usd_price + 13.5 * weight_val) * exchange_rate, 0)

    # Update the product in the database
    if barcode:  # Ensure barcode is valid before updating the database
        update_weight_price_finalprice(
            barcode=barcode,
            weight=weight_val,
            price=usd_price,
            final_price=final_price
        )

    final_price_rounded = round(final_price, 2)
    await update.message.reply_text(
        f"Nomi: {context.user_data.get('product_name')}\n"
        f"Barkod: {barcode}\n"
        f"Price (USD): {usd_price}\n"
        f"Weight: {weight_val}\n"
        f"Final(so'm): {final_price_rounded}\n",
    )
    await update.message.reply_text(
        "Davom etish yoki orqaga qaytish?",
        reply_markup=price_done_inline_keyboard()
    )
    return States.PRICE_DONE



async def price_done_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    await query.answer()

    if data == 'add_more':
        await query.edit_message_text("Yana barkod kiriting:")
        return States.BARCODE_INPUT
    elif data == 'back':
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


# ---------- MAHSULOT QO'SHISH (barcha maydonlarni birma-bir so'rash) ----------
async def add_product_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_name'] = text
    await update.message.reply_text("Artikul kiriting (masalan, A-100 yoki 12345):")
    return States.ADD_PRODUCT_ARTIKUL

async def add_product_artikul_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_artikul'] = text
    await update.message.reply_text("Kategoriya kiriting (category):")
    return States.ADD_PRODUCT_CATEGORY

async def add_product_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_category'] = text
    await update.message.reply_text("Postavshik kiriting (masalan, 'Samsung' yoki 'Local'):")
    return States.ADD_PRODUCT_POSTAVSHIK

async def add_product_postavshik_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_postavshik'] = text
    await update.message.reply_text("Stock (float) kiriting (masalan, 10 yoki 2.5):")
    return States.ADD_PRODUCT_STOCK

async def add_product_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        stock_val = float(text)
    except ValueError:
        stock_val = 0.0
    context.user_data['new_stock'] = stock_val

    await update.message.reply_text("Cena postavki (raqam) kiriting:")
    return States.ADD_PRODUCT_CENA_POSTAVKI

async def add_product_cena_postavki_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        c_post = int(text)
    except ValueError:
        c_post = 0
    context.user_data['new_cena_postavki'] = c_post

    await update.message.reply_text("Cena prodaji (raqam) kiriting:")
    return States.ADD_PRODUCT_CENA_PRODAJI

async def add_product_cena_prodaji_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        c_prod = int(text)
    except ValueError:
        c_prod = 0
    context.user_data['new_cena_prodaji'] = c_prod

    await update.message.reply_text("Skidka (float) kiriting (masalan, 5 yoki 10.5):")
    return States.ADD_PRODUCT_SKIDKA

async def add_product_skidka_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        skidka_val = float(text)
    except ValueError:
        skidka_val = 0.0
    context.user_data['new_skidka'] = skidka_val

    await update.message.reply_text("Brend nomi kiriting (masalan, 'Apple'):")
    return States.ADD_PRODUCT_BREND

async def add_product_brend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_brend'] = text

    await update.message.reply_text("Srok (yaroqlilik muddati) kiriting (masalan, '12 oy'):")
    return States.ADD_PRODUCT_SROK

async def add_product_srok_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_srok'] = text

    await update.message.reply_text("Edinitsa_izmereniya kiriting (masalan, 'dona'):")
    return States.ADD_PRODUCT_EDINITSA

async def add_product_edinitsa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['new_edi'] = text

    await update.message.reply_text("Barkodni kiriting (faqat raqam):")
    return States.ADD_PRODUCT_BARCODE

async def add_product_barcode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        barcode_val = int(text)
    except:
        barcode_val = 0

    # DB ga qo'shamiz
    name = context.user_data.get('new_name')
    artikul = context.user_data.get('new_artikul')
    category = context.user_data.get('new_category')
    postavshik = context.user_data.get('new_postavshik')
    stock = context.user_data.get('new_stock', 0)
    cena_postavki = context.user_data.get('new_cena_postavki', 0)
    cena_prodaji = context.user_data.get('new_cena_prodaji', 0)
    skidka = context.user_data.get('new_skidka', 0.0)
    brend = context.user_data.get('new_brend', "")
    srok = context.user_data.get('new_srok', "")
    edi = context.user_data.get('new_edi', "")

    add_product(
        name=name,
        artikul=artikul,
        barcode=barcode_val,
        category=category,
        postavshik=postavshik,
        stock=stock,
        cena_postavki=cena_postavki,
        cena_prodaji=cena_prodaji,
        skidka=skidka,
        brend=brend,
        srok=srok,
        edinitsa_izmereniya=edi
    )

    await update.message.reply_text(
        f"Yangi mahsulot qo'shildi:\n\n"
        f"Nomi: {name}\n"
        f"Artikul: {artikul}\n"
        f"Barkod: {barcode_val}\n"
        f"Kategoriya: {category}\n"
        f"Postavshik: {postavshik}\n"
        f"Stock: {stock}\n"
        f"Cena postavki: {cena_postavki}\n"
        f"Cena prodaji: {cena_prodaji}\n"
        f"Skidka: {skidka}\n"
        f"Brend: {brend}\n"
        f"Srok: {srok}\n"
        f"Edinitsa: {edi}\n\n"
        "Yana mahsulot qo'shasizmi yoki Orqaga?",
        reply_markup=add_product_done_keyboard()
    )
    return States.ADD_PRODUCT_DONE

async def add_product_done_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    await query.answer()

    if data == 'add_product_again':
        await query.edit_message_text("Mahsulot nomini kiriting (name):")
        return States.ADD_PRODUCT_NAME
    elif data == 'back':
        await query.edit_message_text("Asosiy menyuga qaytildi.")
        await query.message.reply_text(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU
    else:
        await query.edit_message_text("Noma'lum tugma bosildi.")
        return States.MAIN_MENU

# ---------- BARCHA MAHSULOTLAR (pagination) ----------
async def send_products(update: Update, context: ContextTypes.DEFAULT_TYPE, products, page, total_pages):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)

    msg = f"Barcha mahsulotlar (sahifa {page}/{total_pages}):\n\n"
    start_index = (page - 1) * 10
    for idx, p in enumerate(products, start=start_index + 1):
        pid, name, artikul, barcode, category, postavshik, stock, c_post, c_prod, skidka, brend, srok, edi, weight, price, final_p = p
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
        page = int(data.split("_")[1])
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
        from keyboards import main_menu_keyboard
        await query.message.reply_text(
            "Asosiy menyu:",
            reply_markup=main_menu_keyboard(is_admin=is_admin)
        )
        return States.MAIN_MENU

    else:
        await query.edit_message_text("Noma'lum tugma bosildi.")
        return States.MAIN_MENU


async def send_products_inline(query, context, products, page, total_pages):
    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    msg = f"Barcha mahsulotlar (sahifa {page}/{total_pages}):\n\n"
    start_index = (page - 1) * 10
    for idx, p in enumerate(products, start=start_index + 1):
        pid, name, artikul, barcode, category, postavshik, stock, c_post, c_prod, skidka, brend, srok, edi, weight, price, final_p = p
        msg += (
            f"{idx}. {name}\n"
            f"   Barkod: {barcode}\n"
            f"   Price(USD): {price}\n"
            f"   Final(so'm): {final_p}\n\n"
        )

    from keyboards import view_products_inline_keyboard
    reply_markup = view_products_inline_keyboard(page, total_pages)
    await query.edit_message_text(msg, reply_markup=reply_markup)

