# main.py

import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from config import BOT_TOKEN, ADMIN_ID
from handlers.korzinka_handlers import (
    korzinka_menu_handler,
    korzinka_inline_callback,
    korzinka_add_handler,
    korzinka_price_handler,
    show_basket_items,
    export_basket,
    korzinka_view_handler,
    noop_callback
)
from pytz import timezone

from handlers.main_handlers import (
    start, main_menu_handler, send_products, view_products_handler)
from handlers.product_handlers import (
    barcode_input_handler, price_input_handler, weight_input_handler,
    price_done_callback_handler, add_product_name_handler,
    add_product_artikul_handler, add_product_category_handler,
    add_product_postavshik_handler, add_product_stock_handler,
    add_product_cena_postavki_handler, add_product_cena_prodaji_handler,
    add_product_skidka_handler, add_product_brend_handler,
    add_product_srok_handler, add_product_edinitsa_handler,
    add_product_barcode_handler, add_product_done_callback_handler
)
from handlers.dollar_handlers import dollar_menu_handler, exchange_rate_input_handler
from handlers.admin_handlers import (
    admin_menu_handler, update_product_state_handler,
    update_product_name_handler, update_product_weight_handler,
    delete_product_state_handler, update_product_price_handler
)
from handlers.excel_handlers import (
    import_export_menu_handler, excel_import_file_handler
)
from handlers.reports_handlers import reports_menu_handler
from states import States
from keyboards import main_menu_keyboard

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def cancel(update, context):
    user_id = update.message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    await update.message.reply_text(
        "Bekor qilindi.",
        reply_markup=main_menu_keyboard(is_admin=is_admin)
    )
    return States.MAIN_MENU

def main():

    # Установите таймзону (например, "Asia/Tashkent")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # MAIN MENU
            States.MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler),
            ],

            # DOLLAR
            States.DOLLAR_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, dollar_menu_handler),
            ],
            States.EXCHANGE_RATE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exchange_rate_input_handler),
            ],

            # BARKOD QIDIRISH VA PRICE/WEIGHT
            States.BARCODE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, barcode_input_handler),
            ],
            States.PRICE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, price_input_handler),
            ],
            States.WEIGHT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, weight_input_handler),
            ],
            States.PRICE_DONE: [
                CallbackQueryHandler(price_done_callback_handler, pattern='^(add_more|back)$')
            ],

            # ADD PRODUCT (all fields step-by-step)
            States.ADD_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name_handler),
            ],
            States.ADD_PRODUCT_ARTIKUL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_artikul_handler),
            ],
            States.ADD_PRODUCT_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_category_handler),
            ],
            States.ADD_PRODUCT_POSTAVSHIK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_postavshik_handler),
            ],
            States.ADD_PRODUCT_STOCK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_stock_handler),
            ],
            States.ADD_PRODUCT_CENA_POSTAVKI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_cena_postavki_handler),
            ],
            States.ADD_PRODUCT_CENA_PRODAJI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_cena_prodaji_handler),
            ],
            States.ADD_PRODUCT_SKIDKA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_skidka_handler),
            ],
            States.ADD_PRODUCT_BREND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_brend_handler),
            ],
            States.ADD_PRODUCT_SROK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_srok_handler),
            ],
            States.ADD_PRODUCT_EDINITSA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_edinitsa_handler),
            ],
            States.ADD_PRODUCT_BARCODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_barcode_handler),
            ],
            States.ADD_PRODUCT_DONE: [
                CallbackQueryHandler(add_product_done_callback_handler, pattern='^(add_product_again|back)$')
            ],

            # VIEW PRODUCTS
            States.VIEW_PRODUCTS: [
                CallbackQueryHandler(view_products_handler, pattern='^(page_\d+|back)$')
            ],

            # REPORTS
            States.REPORTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reports_menu_handler)
            ],

            # ADMIN MENU
            States.ADMIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_handler),
            ],

            # UPDATE PRODUCT
            States.UPDATE_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_product_state_handler),
            ],
            States.UPDATE_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_product_name_handler),
            ],
            States.UPDATE_PRODUCT_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_product_weight_handler),
            ],
            States.UPDATE_PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_product_price_handler),
            ],

            # KORZINKA STATES
            States.KORZINKA_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, korzinka_menu_handler),
            ],
            States.KORZINKA_ADD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, korzinka_add_handler),
            ],
            States.KORZINKA_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, korzinka_price_handler),
            ],
            States.KORZINKA_INLINE: [
                CallbackQueryHandler(
                    korzinka_inline_callback,
                    pattern=r'^(inc_\d+|dec_\d+|remove_\d+|plus|minus|next)$'
                ),
            ],

            States.KORZINKA_VIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, korzinka_view_handler),
            ],

            # DELETE PRODUCT
            States.DELETE_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_product_state_handler),
            ],

            # IMPORT/EXPORT (XLSX)
            States.IMPORT_EXPORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, import_export_menu_handler),
                MessageHandler(filters.Document.ALL, excel_import_file_handler),
            ],

        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    # Add handler for 'noop' callback
    app.add_handler(CallbackQueryHandler(noop_callback, pattern='^noop$'))
    app.run_polling()

if __name__ == '__main__':
    main()
