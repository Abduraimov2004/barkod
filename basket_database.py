# basket_database.py

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_basket_items():
    """
    Retrieves all items in the basket.
    """
    try:
        response = supabase.table('basket').select('*').execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching basket items: {e}")
        return []

def add_or_update_item_in_basket(name, artikul, barcode, weight, price, price_postavki, shtuk):
    """
    Adds a new item to the basket or updates the `shtuk` if it already exists.
    """
    try:
        # Check if item exists
        response = supabase.table('basket').select('*').eq('barcode', barcode).execute()
        items = response.data
        if items:
            # Update existing item's shtuk
            existing_shtuk = items[0]['shtuk']
            new_shtuk = existing_shtuk + shtuk
            supabase.table('basket').update({'shtuk': new_shtuk}).eq('barcode', barcode).execute()
        else:
            # Insert new item
            data = {
                'name': name,
                'artikul': artikul,
                'barcode': barcode,
                'weight': weight,
                'price': price,
                'price_postavki': price_postavki,
                'shtuk': shtuk
            }
            supabase.table('basket').insert(data).execute()
    except Exception as e:
        logger.error(f"Error adding/updating basket item: {e}")

def update_shtuk(item_id, new_shtuk):
    """
    Updates the `shtuk` count for a specific basket item.
    """
    try:
        supabase.table('basket').update({'shtuk': new_shtuk}).eq('id', item_id).execute()
    except Exception as e:
        logger.error(f"Error updating shtuk for item {item_id}: {e}")

def remove_item(item_id):
    """
    Removes an item from the basket by its ID.
    """
    try:
        supabase.table('basket').delete().eq('id', item_id).execute()
    except Exception as e:
        logger.error(f"Error removing item {item_id} from basket: {e}")

def clear_basket():
    """
    Clears all items from the basket.
    """
    try:
        supabase.table('basket').delete().neq('id', 0).execute()  # Assuming id=0 does not exist
    except Exception as e:
        logger.error(f"Error clearing the basket: {e}")
