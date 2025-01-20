# states.py

from enum import Enum, auto

class States(Enum):
    MAIN_MENU = auto()
    DOLLAR_MENU = auto()
    EXCHANGE_RATE_INPUT = auto()

    BARCODE_INPUT = auto()   # Barkod so'rash
    PRICE_INPUT = auto()     # Mahsulotga narx (USD) so'rash
    WEIGHT_INPUT = auto()    # Mahsulotga weight so'rash
    PRICE_DONE = auto()      # Narx kiritish tugagandan keyingi tugma bosish

    # Mahsulot qo'shish (all fields)
    ADD_PRODUCT_NAME = auto()
    ADD_PRODUCT_ARTIKUL = auto()
    ADD_PRODUCT_CATEGORY = auto()
    ADD_PRODUCT_POSTAVSHIK = auto()
    ADD_PRODUCT_STOCK = auto()
    ADD_PRODUCT_CENA_POSTAVKI = auto()
    ADD_PRODUCT_CENA_PRODAJI = auto()
    ADD_PRODUCT_SKIDKA = auto()
    ADD_PRODUCT_BREND = auto()
    ADD_PRODUCT_SROK = auto()
    ADD_PRODUCT_EDINITSA = auto()
    ADD_PRODUCT_BARCODE = auto()
    ADD_PRODUCT_DONE = auto()

    # VIEW PRODUCTS
    VIEW_PRODUCTS = auto()

    # REPORTS
    REPORTS = auto()

    # ADMIN MENU
    ADMIN_MENU = auto()
    UPDATE_PRODUCT = auto()
    UPDATE_PRODUCT_NAME = auto()
    UPDATE_PRODUCT_WEIGHT = auto()
    UPDATE_PRODUCT_PRICE = auto()
    DELETE_PRODUCT = auto()
    IMPORT_EXPORT = auto()

    # KORZINKA STATES
    KORZINKA_MENU = auto()
    KORZINKA_ADD = auto()
    KORZINKA_PRICE = auto()
    KORZINKA_INLINE = auto()
    KORZINKA_VIEW = auto()
