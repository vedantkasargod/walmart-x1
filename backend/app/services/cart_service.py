# file: backend/app/services/cart_service.py

import redis
import json
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Connect to your local Redis instance running in Docker
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    # Ping the server to check the connection
    redis_client.ping()
    logging.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis: {e}")
    # In a real app, you might want to exit or handle this more gracefully
    redis_client = None


TEMP_CART_EXPIRATION_SECONDS = 3600 # 1 hour

def add_item_to_temp_cart(user_id: str, product: dict, quantity: int):
    """Adds an item to the user's temporary cart in Redis."""
    if not redis_client:
        raise ConnectionError("Redis client is not available.")

    cart_key = f"temp_cart:{user_id}"
    
    # Use a unique ID for each cart entry. This is crucial for the "Undo" feature
    # and allows adding the same product multiple times as separate entries.
    item_id = str(uuid.uuid4())
    
    cart_item_data = {
        "item_id": item_id,
        "product_id": product.get('id'),
        "name": product.get('name'),
        "price": product.get('price'),
        "image_url": product.get('image_url'),
        "quantity": quantity,
    }
    
    # We use a Redis Hash to store the cart. The cart_key is the name of the hash,
    # and each item_id is a field within that hash.
    redis_client.hset(cart_key, item_id, json.dumps(cart_item_data))
    
    # Reset the expiration time every time the cart is modified.
    redis_client.expire(cart_key, TEMP_CART_EXPIRATION_SECONDS)
    
    logging.info(f"Added item {item_id} to cart for user {user_id}")
    return cart_item_data # Return the full item data with its new unique ID

def remove_item_from_temp_cart(user_id: str, item_id: str):
    """Removes a specific item from the user's temporary cart using its unique item_id."""
    if not redis_client:
        raise ConnectionError("Redis client is not available.")

    cart_key = f"temp_cart:{user_id}"
    result = redis_client.hdel(cart_key, item_id)
    
    if result == 1:
        logging.info(f"Removed item {item_id} from cart for user {user_id}")
    else:
        logging.warning(f"Attempted to remove non-existent item {item_id} for user {user_id}")
        
    return {"status": "ok", "removed": result}

def get_temp_cart(user_id: str) -> list:
    """Retrieves all items from the user's temporary cart."""
    if not redis_client:
        raise ConnectionError("Redis client is not available.")
        
    cart_key = f"temp_cart:{user_id}"
    cart_items = redis_client.hgetall(cart_key)
    
    # The values are stored as JSON strings, so we need to parse them back into dicts
    return [json.loads(item) for item in cart_items.values()]