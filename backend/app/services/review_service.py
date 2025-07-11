# file: backend/app/services/review_service.py

import logging
import json
from typing import List, Dict, Optional
from .cart_service import redis_client # We can reuse our existing Redis client

# The Redis key will follow this pattern
REVIEW_SESSION_KEY_PREFIX = "review_session:"
# The review session will expire after 30 minutes of inactivity
REVIEW_SESSION_EXPIRATION_SECONDS = 1800 

def create_review_session(user_id: str, items: List[Dict]) -> bool:
    """
    Creates or overwrites a review session for a user in Redis.
    The list of items is stored as a single JSON string.
    """
    if not redis_client:
        logging.error("Redis client is not available. Cannot create review session.")
        return False
    
    try:
        session_key = f"{REVIEW_SESSION_KEY_PREFIX}{user_id}"
        # Convert the list of items into a JSON string for storage
        items_json = json.dumps(items)
        
        # Store the JSON string in Redis and set its expiration time
        redis_client.setex(session_key, REVIEW_SESSION_EXPIRATION_SECONDS, items_json)
        
        logging.info(f"Successfully created/updated review session for user {user_id} with {len(items)} items.")
        return True
    except Exception as e:
        logging.error(f"Error creating review session for user {user_id}: {e}")
        return False

def get_review_session(user_id: str) -> Optional[List[Dict]]:
    """Retrieves and decodes the review session list for a user from Redis."""
    if not redis_client:
        return None
        
    try:
        session_key = f"{REVIEW_SESSION_KEY_PREFIX}{user_id}"
        items_json = redis_client.get(session_key)
        
        if items_json:
            # If found, decode the JSON string back into a Python list
            return json.loads(items_json)
        else:
            # Return None if no session exists for this user
            return None
    except Exception as e:
        logging.error(f"Error retrieving review session for user {user_id}: {e}")
        return None

def clear_review_session(user_id: str):
    """Deletes a user's review session from Redis, typically after completion."""
    if not redis_client:
        return

    session_key = f"{REVIEW_SESSION_KEY_PREFIX}{user_id}"
    redis_client.delete(session_key)
    logging.info(f"Cleared review session for user {user_id}.")