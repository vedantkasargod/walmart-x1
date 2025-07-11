# file: backend/app/services/budget_service.py
import os
import json
import logging
from typing import List, Dict, Optional
import requests
from .llm_service import load_prompt, OPENROUTER_API_KEY, OPENROUTER_API_URL

# --- Setup ---
PROMPT_DIR = "D:\\walmart_4\\backend\\app\\prompts" # Your corrected path
BUDGET_CURATOR_PROMPT = load_prompt(os.path.join(PROMPT_DIR, 'budget_curator_prompt.md'))

def curate_cart_with_llm(
    products: List[Dict], 
    budget: Optional[float], 
    user_query: str
) -> List[Dict]:
    """
    Uses an LLM to intelligently select products to fit a budget, then enriches
    the LLM's decision with full product details to ensure a consistent API response.
    """
    if not products:
        return []

    # --- Path A: No Budget (The working path) ---
    if budget is None:
        logging.info("No budget specified. Using simple top 7 fallback.")
        top_products = sorted(products, key=lambda p: p.get('similarity', 0), reverse=True)[:7]
        # Ensure a default quantity is always present
        for p in top_products:
            p['quantity'] = 1
        return top_products

    # --- Path B: With Budget (The new, corrected path) ---
    
    # 1. Create a lookup map of our full product data for easy access later.
    product_lookup = {p["id"]: p for p in products}

    # 2. Prepare the simplified list of products for the LLM prompt.
    products_for_llm = json.dumps([
        {"id": p.get("id"), "name": p.get("name"), "price": p.get("price")} for p in products
    ], indent=2)
    
    prompt_context = f"USER'S GOAL: \"{user_query}\"\nBUDGET: {budget}\nAVAILABLE PRODUCTS:\n{products_for_llm}"
    
    try:
        logging.info("Initiating LLM call for budget curation...")
        # (Standard LLM call boilerplate)
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [{"role": "system", "content": BUDGET_CURATOR_PROMPT}, {"role": "user", "content": prompt_context}],
        }
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        llm_output = response.json()['choices'][0]['message']['content']
        
        start_index = llm_output.find('[')
        end_index = llm_output.rfind(']') + 1
        json_str = llm_output[start_index:end_index]
        # 3. Get the LLM's simple decision list, e.g., [{id: 1, quantity: 2}, ...]
        llm_decisions = json.loads(json_str)

    except Exception as e:
        logging.error(f"LLM curator failed: {e}")
        return []

    # 4. --- The "Enrichment" Step ---
    # We now build the final list by combining the LLM's decisions with our full product data.
    final_curated_cart = []
    for decision in llm_decisions:
        product_id = decision.get("id")
        if product_id in product_lookup:
            # Get the original, complete product details
            full_product_details = product_lookup[product_id].copy()
            # Add the quantity decided by the LLM
            full_product_details["quantity"] = decision.get("quantity", 1)
            final_curated_cart.append(full_product_details)
            
    logging.info(f"LLM curator successfully created a cart with {len(final_curated_cart)} items.")
    return final_curated_cart