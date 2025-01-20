# handlers/korzinka_handlers.py

import logging
import os

from telegram import Update, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from states import States
from keyboards import (
    korzinka_menu_keyboard,
    korzinka_inline_buttons,
    korzinka_item_inline,
    admin_menu_keyboard
)
from config import ADMIN_ID
from database import get_product_by_barcode, get_exchange_rate, fetch_product_from_openfda, add_product
from basket_database import (
    add_or_update_item_in_basket,
    get_basket_items,
    update_shtuk,
    clear_basket,
    remove_item
)

logger = logging.getLogger(__name__)

async def korzinka_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Korzinka menu: "Add product", "View basket items", "Export", "Back"
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    if text == "Maxsulot qo'shish":
        await update.message.reply_text("Barkod kiriting:")
        return States.KORZINKA_ADD

    elif text == "Korzinkadagi Maxsulotlar":
        await show_basket_items(update, context)
        return States.KORZINKA_VIEW

    elif text == "Export":
        await export_basket(update, context)
        return States.KORZINKA_MENU

    elif text == "Orqaga":
        # Return to admin menu
        await update.message.reply_text(
            "Admin menyusiga qaytish.",
            reply_markup=admin_menu_keyboard()
        )
        return States.ADMIN_MENU
    else:
        # Handle unexpected input
        await update.message.reply_text(
            "Noma'lum buyruq.",
            reply_markup=korzinka_menu_keyboard()
        )
        return States.KORZINKA_MENU

async def korzinka_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Enter barcode -> find in DB -> if found, ask for USD price
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Barkod faqat raqam bo'lishi kerak yoki /cancel:")
        return States.KORZINKA_ADD

    barcode = int(text)
    product = get_product_by_barcode(barcode)
    if not product:
        # Product not found in local DB, search via OpenFDA
        await update.message.reply_text("Mahsulot lokal bazada topilmadi. OpenFDA orqali qidirilyapti...")
        product_data = fetch_product_from_openfda(barcode)
        if product_data:
            # Product found via OpenFDA, add to local DB
            add_product(
                name=product_data["name"],
                artikul=product_data["artikul"],
                barcode=product_data["barcode"],
                category=product_data["category"],
                postavshik=product_data["postavshik"],
                stock=product_data["stock"],
                cena_postavki=product_data["cena_postavki"],
                cena_prodaji=product_data["cena_prodaji"],
                skidka=product_data["skidka"],
                brend=product_data["brend"],
                srok=product_data["srok"],
                edinitsa_izmereniya=product_data["edinitsa_izmereniya"],
            )
            product = get_product_by_barcode(barcode)
            if not product:
                await update.message.reply_text("Mahsulot OpenFDA orqali qo'shilmadi.")
                return States.KORZINKA_ADD

    if product:
        # Check if 'weight' is present and >0
        weight = product.get('weight')
        if weight is None or weight <= 0:
            await update.message.reply_text("Bu mahsulotda og'irlik ko'rsatilmagan. Qoshish mumkin emas.")
            return States.KORZINKA_ADD

        # Check if the product already exists in the basket
        existing_items = get_basket_items()
        if any(item['barcode'] == barcode for item in existing_items):
            await update.message.reply_text("Bu mahsulot allaqachon korzinkada bor.")
            await update.message.reply_text(
                "Korzinka menyusiga qaytamiz.",
                reply_markup=korzinka_menu_keyboard()
            )
            return States.KORZINKA_MENU  # Return to Korzinka menu without asking for USD price

        # Continue with the flow to ask for USD price since the product is not in the basket
        name = product.get('name')
        artikul = product.get('artikul')
        context.user_data["basket_name"] = name
        context.user_data["basket_artikul"] = artikul
        context.user_data["basket_barcode"] = barcode
        context.user_data["basket_weight"] = weight

        await update.message.reply_text(
            f"Mahsulot topildi:\n"
            f"  Nomi: {name}\n"
            f"  Artikul: {artikul}\n"
            f"  Weight: {weight}\n\n"
            "Narx (USD) kiriting:"
        )
        return States.KORZINKA_PRICE
    else:
        await update.message.reply_text("Mahsulot topilmadi.")
        return States.KORZINKA_ADD

async def korzinka_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receive USD price, calculate prices, add to basket, and ask to adjust 'shtuk'
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    try:
        price_usd = float(text)
    except ValueError:
        await update.message.reply_text("Narx (USD)ni to'g'ri kiriting:")
        return States.KORZINKA_PRICE

    name = context.user_data.get('basket_name')
    artikul = context.user_data.get('basket_artikul')
    barcode = context.user_data.get('basket_barcode')
    weight = context.user_data.get('basket_weight', 0.0)

    rate = get_exchange_rate()
    # price in som
    price_som = price_usd * rate
    # price_postavki = (price_usd + 13.5 * weight) * exchange_rate
    price_postavki = (price_usd + 13.5 * weight) * rate

    # Shtuk = 1 (default)
    context.user_data['basket_shtuk'] = 1
    context.user_data['basket_price'] = price_som
    context.user_data['basket_price_postavki'] = price_postavki

    # Add to basket
    add_or_update_item_in_basket(
        name=name,
        artikul=artikul,
        barcode=barcode,
        weight=weight,
        price=price_som,
        price_postavki=price_postavki,
        shtuk=1
    )

    # Prepare message
    msg = (
        f"Mahsulot qo'shildi:\n"
        f"  Nomi: {name}\n"
        f"  Artikul: {artikul}\n"
        f"  Barkod: {barcode}\n"
        f"  Weight: {weight}\n"
        f"  Price(so'm): {price_som:.2f}\n"
        f"  Price_postavki(so'm): {price_postavki:.2f}\n"
        f"  Shtuk: 1\n"
    )
    await update.message.reply_text(
        msg,
        reply_markup=korzinka_inline_buttons(shtuk=1)  # inline "+" "-" "Next"
    )
    return States.KORZINKA_INLINE

async def korzinka_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle increment, decrement, removal of basket items and 'next' button.
    """
    query = update.callback_query
    data = query.data  # Expected patterns: 'inc_<id>', 'dec_<id>', 'remove_<id>', 'next', 'plus', 'minus'

    logger.info(f"Received callback data: {data}")

    # Only allow admin users to modify the basket
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.answer("Siz admin emassiz!", show_alert=True)
        return States.KORZINKA_MENU

    if data == 'next':
        # Handle the "Keyingi" button
        await query.answer()  # Acknowledge the callback
        await query.edit_message_text(
            "Mahsulot qo'shildi."
            # 'edit_message_text' does not send a ReplyKeyboardMarkup
        )
        # Send a new message with main Korzinka menu
        await query.message.reply_text(
            "Yana mahsulot qo'shish uchun 'Maxsulot qo'shish' tugmasini bosing.",
            reply_markup=korzinka_menu_keyboard()
        )
        return States.KORZINKA_MENU

    elif data in ['plus', 'minus']:
        # Handle shtuk modification before adding to basket
        shtuk = context.user_data.get('basket_shtuk', 1)
        if data == 'plus':
            shtuk += 1
            context.user_data['basket_shtuk'] = shtuk
        elif data == 'minus' and shtuk > 1:
            shtuk -= 1
            context.user_data['basket_shtuk'] = shtuk

        # Update the basket in the database
        barcode = context.user_data.get('basket_barcode')
        if barcode:
            # Find the item in the basket by barcode
            items = get_basket_items()
            item = next((it for it in items if it['barcode'] == barcode), None)
            if item:
                item_id = item['id']  # Assuming 'id' is the unique identifier
                update_shtuk(item_id, shtuk)
                logger.info(f"Shtuk for item_id {item_id} updated to {shtuk}.")
            else:
                logger.error(f"Item with barcode {barcode} not found in the basket.")
                await query.answer("Mahsulot topilmadi.", show_alert=True)
                return States.KORZINKA_MENU
        else:
            logger.error("Barcode not found in user_data.")
            await query.answer("Mahsulot topilmadi.", show_alert=True)
            return States.KORZINKA_MENU

        # Update the message with new shtuk
        name = context.user_data.get('basket_name')
        artikul = context.user_data.get('basket_artikul')
        barcode = context.user_data.get('basket_barcode')
        weight = context.user_data.get('basket_weight', 0.0)
        price_som = context.user_data.get('basket_price', 0.0)
        price_postavki = context.user_data.get('basket_price_postavki', 0.0)

        msg = (
            f"Mahsulot qo'shildi:\n"
            f"  Nomi: {name}\n"
            f"  Artikul: {artikul}\n"
            f"  Barkod: {barcode}\n"
            f"  Weight: {weight}\n"
            f"  Price(so'm): {price_som:.2f}\n"
            f"  Price_postavki(so'm): {price_postavki:.2f}\n"
            f"  Shtuk: {shtuk}\n"
        )
        await query.edit_message_text(
            msg,
            reply_markup=korzinka_inline_buttons(shtuk=shtuk)
        )
        await query.answer("Shtuk yangilandi.", show_alert=False)
        return States.KORZINKA_INLINE

    elif data.startswith("inc_") or data.startswith("dec_") or data.startswith("remove_"):
        try:
            action, item_id_str = data.split("_", 1)
            item_id = int(item_id_str)
            logger.info(f"Action: {action}, Item ID: {item_id}")
        except ValueError:
            logger.error(f"Invalid callback data format: {data}")
            await query.answer("Noma'lum buyruq!", show_alert=True)
            return States.KORZINKA_MENU

        # Retrieve the item from the basket
        items = get_basket_items()
        the_item = next((it for it in items if it['id'] == item_id), None)
        if not the_item:
            logger.warning(f"Item with ID {item_id} not found in the basket.")
            await query.answer("Item topilmadi.", show_alert=True)
            return States.KORZINKA_MENU

        if action == "inc":
            new_shtuk = the_item['shtuk'] + 1
            update_shtuk(item_id, new_shtuk)
            action_performed = "Korzinkadagi mahsulot soni oshirildi."
            logger.info(f"Updated 'shtuk' for item {item_id} to {new_shtuk}.")
        elif action == "dec":
            if the_item['shtuk'] > 1:
                new_shtuk = the_item['shtuk'] - 1
                update_shtuk(item_id, new_shtuk)
                action_performed = "Korzinkadagi mahsulot soni kamaytirildi."
                logger.info(f"Updated 'shtuk' for item {item_id} to {new_shtuk}.")
            else:
                logger.info(f"Attempted to decrement 'shtuk' below 1 for item {item_id}.")
                await query.answer("Shtuk kam bo'lmaydi.", show_alert=True)
                return States.KORZINKA_MENU
        elif action == "remove":
            remove_item(item_id)
            await query.edit_message_text("Mahsulot korzinkadan o'chirildi.")
            logger.info(f"Removed item {item_id} from the basket.")
            return States.KORZINKA_MENU

        if action in ["inc", "dec"]:
            # Fetch the updated item
            updated_item = next((it for it in get_basket_items() if it['id'] == item_id), None)
            if not updated_item:
                logger.warning(f"Updated item with ID {item_id} not found in the basket.")
                await query.edit_message_text("Item topilmadi.")
                return States.KORZINKA_MENU

            # Prepare the updated message
            msg = (
                f"#{updated_item['id']}: {updated_item['name']}\n"
                f"   Artikul: {updated_item['artikul']}\n"
                f"   Barkod: {updated_item['barcode']}\n"
                f"   Weight: {updated_item['weight']}\n"
                f"   Price: {updated_item['price']:.2f}\n"
                f"   Postavki: {updated_item['price_postavki']:.2f}\n"
                f"   Shtuk: {updated_item['shtuk']}\n"
            )

            reply_markup = korzinka_item_inline(updated_item['id'], updated_item['shtuk'])
            if not isinstance(reply_markup, InlineKeyboardMarkup):
                logger.error("`korzinka_item_inline` did not return an InlineKeyboardMarkup object.")
                await query.answer("Ichki xato yuz berdi!", show_alert=True)
                return States.KORZINKA_MENU

            # Edit the message with updated quantity
            await query.edit_message_text(
                msg,
                reply_markup=reply_markup  # Quantity buttons
            )
            await query.answer(action_performed, show_alert=False)
            return States.KORZINKA_MENU

async def show_basket_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display all items in the basket without options to modify quantity.
    """
    items = get_basket_items()
    if not items:
        await update.message.reply_text(
            "Korzinka bo'sh.",
            reply_markup=korzinka_menu_keyboard()
        )
        return

    for item in items:
        msg = (
            f"#{item['id']}: {item['name']}\n"
            f"   Artikul: {item['artikul']}\n"
            f"   Barkod: {item['barcode']}\n"
            f"   Weight: {item['weight']}\n"
            f"   Price: {item['price']:.2f}\n"
            f"   Postavki: {item['price_postavki']:.2f}\n"
            f"   Shtuk: {item['shtuk']}\n\n"
        )
        await update.message.reply_text(msg)

    # Add buttons to export and back
    kb = [
        ["Export Korzinka"],
        ["Orqaga"]
    ]
    await update.message.reply_text(
        "Boshqa amallar:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def export_basket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Export the basket to an XLSX file and clear the basket.
    """
    from openpyxl import Workbook

    items = get_basket_items()
    if not items:
        await update.message.reply_text("Korzinka bo'sh, hech narsa yo'q.")
        return States.KORZINKA_MENU

    wb = Workbook()
    ws = wb.active
    ws.title = "Korzinka"

    # Headers
    headers = ["id", "name", "artikul", "barcode", "weight", "price", "price_postavki", "shtuk"]
    ws.append(headers)

    for item in items:
        ws.append([
            item.get('id'),
            item.get('name'),
            item.get('artikul'),
            item.get('barcode'),
            item.get('weight'),
            item.get('price'),
            item.get('price_postavki'),
            item.get('shtuk')
        ])

    filename = "korzinka_export.xlsx"
    wb.save(filename)

    if os.path.exists(filename):
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f, filename=filename)
        os.remove(filename)  # Remove the file after sending

    # Clear the basket after exporting
    clear_basket()

    await update.message.reply_text("Korzinka tozalandi va eksport qilindi.")

async def korzinka_view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle actions in the basket view such as exporting or going back.
    """
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return States.MAIN_MENU

    text = update.message.text.strip()
    if text == "Export Korzinka":
        await export_basket(update, context)
        return States.KORZINKA_MENU
    elif text == "Orqaga":
        await update.message.reply_text(
            "Korzinka menyusiga qaytdik.",
            reply_markup=korzinka_menu_keyboard()
        )
        return States.KORZINKA_MENU
    else:
        await update.message.reply_text(
            "Noma'lum buyruq.",
            reply_markup=korzinka_menu_keyboard()
        )
        return States.KORZINKA_MENU

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    No-operation callback to handle quantity display button.
    """
    query = update.callback_query
    await query.answer()
    # Do nothing
