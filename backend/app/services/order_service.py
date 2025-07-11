import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from app.services.cart_service import get_temp_cart, redis_client
from typing import List, Dict, Optional
# Load environment variables for Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in the environment variables.")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_order_from_cart(user_id: str) -> dict:
    """
    Creates a permanent order in PostgreSQL from the user's temporary Redis cart.
    This function performs a transaction-like operation.
    """
    # 1. Retrieve the user's temporary cart from Redis
    cart_items = get_temp_cart(user_id)
    if not cart_items:
        raise ValueError("Cannot create an order from an empty cart.")

    # 2. Calculate the total amount of the order
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    try:
        # --- Start of "Transaction" ---
        
        # 3. Create a single record in the 'orders' table
        logging.info(f"Creating order for user {user_id} with total {total_amount}")
        order_response = supabase.table('orders').insert({
            'user_id': user_id,
            'total_amount': total_amount
        }).execute()
        
        if not order_response.data:
            raise Exception("Failed to create order record.")
            
        # Get the ID of the new order we just created
        new_order_id = order_response.data[0]['id']
        logging.info(f"Successfully created order with ID: {new_order_id}")

        # 4. Prepare the list of items for the 'order_items' table
        order_items_to_insert = [
            {
                'order_id': new_order_id,
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'price_at_purchase': item['price']
            }
            for item in cart_items
        ]
        
        # 5. Insert all cart items into the 'order_items' table in a single batch
        logging.info(f"Inserting {len(order_items_to_insert)} items into order_items table.")
        items_response = supabase.table('order_items').insert(order_items_to_insert).execute()
        
        if not items_response.data:
            # If this step fails, we should ideally "roll back" the order creation.
            # For simplicity, we'll just raise an error for now.
            # In a real production system, you'd delete the order record created above.
            raise Exception("Failed to insert order items.")

        # --- End of "Transaction" ---

        # 6. If everything was successful, clear the temporary Redis cart
        cart_key = f"temp_cart:{user_id}"
        redis_client.delete(cart_key)
        logging.info(f"Successfully cleared Redis cart for user {user_id}")
        
        return {"status": "success", "order_id": new_order_id, "total_amount": total_amount}

    except Exception as e:
        logging.error(f"An error occurred during order creation for user {user_id}: {e}")
        # Return a meaningful error to the endpoint
        raise e
    

# in backend/app/services/order_service.py

# ... (keep your existing imports and create_order_from_cart function)

def get_last_order_for_user(user_id: str) -> Optional[List[Dict]]:
    """
    Retrieves the items from the most recent order for a given user.
    """
    try:
        logging.info(f"Fetching last order for user_id: {user_id}")
        
        # Step 1: Find the most recent order for this user
        latest_order_response = supabase.table('orders').select('id') \
            .eq('user_id', user_id) \
            .order('order_date', desc=True) \
            .limit(1) \
            .execute()
            
        if not latest_order_response.data:
            logging.info(f"No previous orders found for user {user_id}.")
            return None # Return None if the user has no order history

        latest_order_id = latest_order_response.data[0]['id']
        logging.info(f"Found latest order_id: {latest_order_id}")

        # Step 2: Get all items associated with that order
        # We also "join" to get the product name and image from the products table.
        order_items_response = supabase.table('order_items') \
            .select('*, products(name, image_url)') \
            .eq('order_id', latest_order_id) \
            .execute()

        if not order_items_response.data:
            logging.warning(f"Order {latest_order_id} found, but it has no items.")
            return []

        logging.info(f"Retrieved {len(order_items_response.data)} items from the last order.")
        return order_items_response.data

    except Exception as e:
        logging.error(f"Error fetching last order for user {user_id}: {e}")
        return None