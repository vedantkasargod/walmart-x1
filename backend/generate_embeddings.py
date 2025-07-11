
print("--- Script execution started. ---")

import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# Configure basic logging to see detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Connects to Supabase and forces a regeneration of embeddings for ALL products
    using the latest, high-quality text generation strategy.
    """
    logging.info("--- Main function started (FORCED REFRESH MODE). ---")

    # --- 1. INITIALIZATION ---
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logging.error("FATAL: Supabase credentials not found in .env file. Exiting.")
        return
        
    logging.info("Connecting to Supabase...")
    supabase: Client = create_client(url, key)
    logging.info("Connection successful.")

    logging.info("Loading sentence-transformer model...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
        logging.info("Model loaded successfully on GPU.")
    except Exception as e:
        logging.warning(f"Could not load model on GPU: {e}. Falling back to CPU.")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logging.info("Model loaded successfully on CPU.")

    # --- 2. FETCH ALL PRODUCTS ---
    # We are now fetching ALL products from the table, regardless of whether
    # they already have an embedding. This ensures a complete refresh.
    logging.info("Fetching ALL products to regenerate embeddings...")
    response = supabase.table('products').select('*').execute()

    if not response.data:
        logging.error("No products found in the database. Exiting.")
        return
    
    products_to_embed = response.data
    logging.info(f"Found {len(products_to_embed)} products to process.")

    # --- 3. GENERATE EMBEDDINGS WITH ENHANCED TEXT STRATEGY ---
    logging.info("Generating rich text for embeddings...")
    texts_to_encode = []
    for product in products_to_embed:
        tags_str = ', '.join(product.get('tags', [])) if product.get('tags') else ''

        # "Golden Query" Strategy
        golden_query = f"a user is looking for {product.get('name', '')} in the {product.get('category','')} section"
        
        product_name_lower = product.get('name','').lower()
        if 'hydrating facial cleanser' in product_name_lower:
             golden_query = "a gentle cleanser for my face for dry skin"
        elif 'airpods' in product_name_lower:
             golden_query = "wireless apple headphones"
        elif 'laundry detergent pacs' in product_name_lower:
             golden_query = "laundry pods for my clothes"
        elif 'portable charger' in product_name_lower:
            golden_query = "a power bank for my phone"

        # Combine all text fields for a rich context
        combined_text = (
            f"Product Name: {product.get('name', '')}. "
            f"Description: {product.get('description', '')}. "
            f"Category: {product.get('category', '')}. "
            f"Tags: {tags_str}. "
            f"A user might ask for this by saying: '{golden_query}'"
        )
        texts_to_encode.append(combined_text)

    logging.info("Generating new embeddings from rich text...")
    embeddings = model.encode(texts_to_encode, show_progress_bar=True)
    logging.info("Embeddings generated successfully.")

    # --- 4. PREPARE AND UPLOAD DATA ---
    updates = []
    for i, product in enumerate(products_to_embed):
        updated_product = product.copy()
        updated_product['embedding'] = embeddings[i].tolist()
        updated_product.pop('created_at', None)
        updates.append(updated_product)

    logging.info(f"Preparing to upsert {len(updates)} products with new embeddings...")
    
    try:
        supabase.table('products').upsert(updates).execute()
        logging.info("SUCCESS: Database refreshed with new, higher-quality embeddings!")
    except Exception as e:
        logging.error(f"An error occurred during database update: {e}")

# --- SCRIPT ENTRY POINT ---
if __name__ == "__main__":
    logging.info("--- Checking script entry point. ---")
    main()
    logging.info("--- Script execution finished. ---")