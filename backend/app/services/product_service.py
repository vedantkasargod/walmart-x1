import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in the environment variables.")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Loading sentence transformer model for Product Service...")

model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
print("Model loaded.")


def search_products_hybrid(query_text: str, match_threshold: float, match_count: int):
    """
    Performs HYBRID search (keyword + semantic) using the new RPC function in Supabase.
    """
    # Generate the embedding for the semantic part of the search
    query_embedding = model.encode(query_text).tolist()

    try:
        # Call the new 'hybrid_search_products' function we created in the Supabase SQL editor
        response = supabase.rpc('hybrid_search_products', {
            'keyword_query': query_text,      # Pass the raw text for keyword search
            'query_embedding': query_embedding, # Pass the vector for semantic search
            'match_threshold': match_threshold,
            'match_count': match_count
        }).execute()

        if response.data:
            logging.info(f"Hybrid search found {len(response.data)} products for query: '{query_text}'")
            return response.data
        else:
            logging.info(f"Hybrid search found no products for query: '{query_text}'")
            return []

    except Exception as e:
        logging.error(f"An error occurred during hybrid product search: {e}")
        return []