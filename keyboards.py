# keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def main_menu_keyboard(is_admin=False):
    """
    Main menu keyboard:
    1) Barkod bilan qidirish
    2) Dollar kursi
    3) Mahsulot qo'shish
    4) Barcha mahsulotlar
    5) Hisobotlar
    6) Admin panel (only for admins)
    """
    keyboard = [
        ["Barkod bilan qidirish"],
        ["Dollar kursi", "Maxsulot qo'shish"],
        ["Barcha mahsulotlar", "Hisobotlar"],
    ]
    if is_admin:
        keyboard.append(["Admin panel"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def dollar_menu_keyboard():
    keyboard = [
        ["Kursni ko'rish", "Kursni o'zgartirish"],
        ["Orqaga"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def price_done_inline_keyboard():
    """
    Callback buttons after price input:
    'add_more': add another product
    'back': return to main menu
    """
    kb = [
        [InlineKeyboardButton("Yana barkod kiriting", callback_data='add_more')],
        [InlineKeyboardButton("Orqaga", callback_data='back')]
    ]
    return InlineKeyboardMarkup(kb)

def add_product_done_keyboard():
    """
    Callback buttons after adding a product:
    'add_product_again': add another product
    'back': return to main menu
    """
    kb = [
        [InlineKeyboardButton("Yana mahsulot qo'shish", callback_data='add_product_again')],
        [InlineKeyboardButton("Orqaga", callback_data='back')]
    ]
    return InlineKeyboardMarkup(kb)

def view_products_inline_keyboard(page, total_pages):
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f'page_{page - 1}'))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("➡️ Keyingi", callback_data=f'page_{page + 1}'))
    buttons.append(InlineKeyboardButton("Orqaga", callback_data='back'))

    return InlineKeyboardMarkup([buttons])

def admin_menu_keyboard():
    keyboard = [
        ["Mahsulotni yangilash", "Mahsulotni o'chirish"],
        ["XLSX import/export", "Korzinka"],   # "Korzinka" button
        ["Orqaga"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def import_export_keyboard():
    kb = [
        ["XLSX import", "XLSX export"],
        ["Orqaga"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def reports_menu_keyboard():
    kb = [
        ["Hisobotni ko'rish", "Orqaga"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def korzinka_menu_keyboard():
    """
    Korzinka menu: "Add product", "View basket items", "Export", "Back"
    """
    kb = [
        ["Maxsulot qo'shish", "Korzinkadagi Maxsulotlar"],
        ["Export"],
        ["Orqaga"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def korzinka_inline_buttons(shtuk=1):
    """
    Inline buttons: "+" , "-", "Keyingi"
    If shtuk=1, hide the "-" button
    """
    buttons = []
    if shtuk > 1:
        minus_btn = InlineKeyboardButton("➖", callback_data="minus")
        buttons.append(minus_btn)
    plus_btn = InlineKeyboardButton("➕", callback_data="plus")
    next_btn = InlineKeyboardButton("Keyingi", callback_data="next")
    buttons.extend([plus_btn, next_btn])
    return InlineKeyboardMarkup([buttons])

def korzinka_item_inline(item_id, current_shtuk):
    """
    Inline buttons for each basket item:
    [➖] [➕]
    """
    inc_callback = f"inc_{item_id}"
    dec_callback = f"dec_{item_id}"

    quantity_buttons = []
    if current_shtuk > 1:
        dec_btn = InlineKeyboardButton("➖", callback_data=dec_callback)
        quantity_buttons.append(dec_btn)
    plus_btn = InlineKeyboardButton("➕", callback_data=inc_callback)
    quantity_buttons.append(plus_btn)

    return InlineKeyboardMarkup([quantity_buttons])
