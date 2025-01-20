# database.py

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, OPENFDA_API_KEY, OPENFDA_BASE_URL
import requests
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Exchange Rate Functions ---
def get_exchange_rate():
    response = supabase.table('exchange_rate').select('rate').eq('id', 1).execute()
    data = response.data
    if data:
        return data[0]['rate']
    else:
        logger.warning("Exchange rate not found, defaulting to 1.0")
        return 1.0

# database.py

# database.py

def set_exchange_rate(rate):
    # Обновляем обменный курс
    response = supabase.table('exchange_rate').update({'rate': rate}).eq('id', 1).execute()

    # Проверка статуса ответа (успешный - 2xx)
    if response.status_code >= 400:  # Если ошибка HTTP
        error_details = response.get("data", "Unknown error")  # Получаем данные об ошибке
        logger.error(f"Failed to set exchange rate: {error_details}")
        raise Exception(f"Database update error: {error_details}")

    # Если всё успешно, возвращаем данные
    logger.info(f"Exchange rate updated: {rate}")
    return response.data


# --- Products Functions ---
def get_product_by_barcode(barcode):
    """
    Retrieves a product by its barcode.
    Returns a dictionary if found, else None.
    """
    try:
        response = supabase.table('products').select('*').eq('barcode', barcode).limit(1).execute()
        if response.data:
            return response.data[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching product by barcode {barcode}: {e}")
        return None

def add_product(name, artikul, barcode, category, postavshik,
               stock, cena_postavki, cena_prodaji, skidka,
               brend, srok, edinitsa_izmereniya):
    """
    Adds a new product to the database.
    """
    data = {
        'name': name,
        'artikul': artikul,
        'barcode': barcode,
        'category': category,
        'postavshik': postavshik,
        'stock': stock,
        'cena_postavki': cena_postavki,
        'cena_prodaji': cena_prodaji,
        'skidka': skidka,
        'brend': brend,
        'srok': srok,
        'edinitsa_izmereniya': edinitsa_izmereniya
    }
    try:
        response = supabase.table('products').insert(data).execute()
        if response.status_code >= 300:
            logger.error(f"Error adding product: {response.data}")
            return None
        return response.data
    except Exception as e:
        logger.error(f"Exception adding product: {e}")
        return None

def delete_product(barcode):
    """
    Deletes a product by its barcode.
    """
    try:
        response = supabase.table('products').delete().eq('barcode', barcode).execute()
        if response.status_code >= 300:
            logger.error(f"Error deleting product with barcode {barcode}: {response.data}")
        return response.data
    except Exception as e:
        logger.error(f"Exception deleting product with barcode {barcode}: {e}")
        return None

def update_weight_price_finalprice(barcode, weight=None, price=None, final_price=None):
    """
    Updates weight, price, and final_price of a product identified by its barcode.
    """
    updates = {}
    if weight is not None:
        updates['weight'] = weight
    if price is not None:
        updates['price'] = price
    if final_price is not None:
        updates['final_price'] = final_price
    try:
        response = supabase.table('products').update(updates).eq('barcode', barcode).execute()
        if response.status_code >= 300:
            logger.error(f"Error updating product with barcode {barcode}: {response.data}")
        return response.data
    except Exception as e:
        logger.error(f"Exception updating product with barcode {barcode}: {e}")
        return None

def get_all_products(limit=10, offset=0):
    """
    Retrieves all products with pagination.
    """
    try:
        response = supabase.table('products').select('*').order('id').range(offset, offset + limit -1).execute()
        if response.status_code < 300:
            return response.data
        else:
            logger.error(f"Error fetching all products: {response.data}")
            return []
    except Exception as e:
        logger.error(f"Exception fetching all products: {e}")
        return []

def get_total_products_count():
    """
    Retrieves the total number of products.
    """
    try:
        response = supabase.table('products').select('id', count='exact').execute()
        if response.data:
            return response.count or 0
        else:
            logger.error("Error fetching total products count")
            return 0
    except Exception as e:
        logger.error(f"Exception fetching total products count: {e}")
        return 0

def get_products_statistics():
    """
    Calculates statistics: max_price, min_price, total_stock, avg_price.
    """
    try:
        response = supabase.table('products').select('*').execute()
        products = response.data
        if not products:
            return {
                "max_price": 'N/A',
                "min_price": 'N/A',
                "total_stock": 0,
                "avg_price": 'N/A'
            }
        # Filter out products with None final_price
        final_prices = [p['final_price'] for p in products if p['final_price'] is not None]
        stocks = [p['stock'] for p in products if p['stock'] is not None]
        if final_prices:
            max_price = max(final_prices)
            min_price = min(final_prices)
            avg_price = round(sum(final_prices) / len(final_prices), 2)
        else:
            max_price = 'N/A'
            min_price = 'N/A'
            avg_price = 'N/A'
        total_stock = sum(stocks) if stocks else 0
        return {
            "max_price": max_price,
            "min_price": min_price,
            "total_stock": total_stock,
            "avg_price": avg_price
        }
    except Exception as e:
        logger.error(f"Error calculating product statistics: {e}")
        return {
            "max_price": 'N/A',
            "min_price": 'N/A',
            "total_stock": 0,
            "avg_price": 'N/A'
        }

# --- OpenFDA Functions ---
def fetch_product_from_openfda(barcode):
    """
    Fetches product information from the OpenFDA API using a barcode.
    """
    params = {
        'search': f'upc:{barcode}',
        'limit': 1,
        'api_key': OPENFDA_API_KEY
    }
    try:
        response = requests.get(OPENFDA_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            openfda = result.get('openfda', {})
            name = openfda.get('brand_name', ['Nom mavjud emas'])[0]
            artikul = openfda.get('generic_name', ['Artikul mavjud emas'])[0]
            category = ', '.join(result.get('substance_name', ['Kategoriya mavjud emas']))
            postavshik = 'OpenFDA'  # Can be customized
            stock = 0.0
            cena_postavki = 0
            cena_prodaji = 0
            skidka = 0.0
            brend = ', '.join(openfda.get('manufacturer_name', ['Brend mavjud emas']))
            srok = 'N/A'
            edinitsa_izmereniya = 'N/A'
            weight = 0.0
            price = 0.0
            final_price = 0.0

            product_data = {
                'name': name,
                'artikul': artikul,
                'barcode': barcode,
                'category': category,
                'postavshik': postavshik,
                'stock': stock,
                'cena_postavki': cena_postavki,
                'cena_prodaji': cena_prodaji,
                'skidka': skidka,
                'brend': brend,
                'srok': srok,
                'edinitsa_izmereniya': edinitsa_izmereniya,
                'weight': weight,
                'price': price,
                'final_price': final_price
            }
            return product_data
        else:
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenFDA API error: {e}")
        return None
