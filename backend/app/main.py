import os
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Import all our Pydantic Models ---
from app.models.api_models import QueryRequest, ProcessResponse, ExtractedProduct, BulkAddRequest

# --- Import all our Service Functions ---
from app.services.llm_service import get_ai_plan, extract_product_info_from_query, extract_items_from_text
from app.services.product_service import search_products_hybrid
from app.services.cart_service import add_item_to_temp_cart, remove_item_from_temp_cart, get_temp_cart
from app.services.ocr_service import extract_text_from_pdf
from app.services.order_service import create_order_from_cart, get_last_order_for_user
from app.services.budget_service import curate_cart_with_llm

# --- Load Environment Variables ---
load_dotenv()

# --- Supabase Client Initialization ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Walmart Smart Cart API",
    description="Microservice with a Unified AI Planner for smart shopping.",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================================
# === Main AI Endpoint (/process_query) ===
# ===============================================
@app.post("/process_query", response_model=ProcessResponse)
async def process_user_query(request: QueryRequest):
    """
    Handles all primary user queries using a unified AI planner.
    """
    print(f"Received query: '{request.query}' from user: {request.user_id} with mode: {request.ai_mode}")

    # --- Handle all "AI" modes ('build_cart' and 'recommend') ---
    if request.ai_mode in ['build_cart', 'recommend']:
        
        plan = get_ai_plan(request.query)
        intent = plan.get("intent")

        # --- Sub-Logic: Reorder based on past purchases ---
        if intent == 'reorder':
            print("AI Plan: Reorder the last cart.")
            last_order_items = get_last_order_for_user(request.user_id)
            if not last_order_items:
                raise HTTPException(status_code=404, detail="You have no previous orders to rebuild from!")
            
            review_list = []
            for item in last_order_items:
                if item.get('products'):
                    original_product_data = item['products']
                    original_product_data['quantity'] = item['quantity']
                    original_product_data['source'] = 'Reorder'
                    review_list.append(original_product_data)
                    
                    similar_products = search_products_hybrid(query_text=original_product_data['name'], match_threshold=0.5, match_count=5)
                    for alt in similar_products:
                        if alt['id'] != item['product_id']:
                            alt['quantity'] = 1
                            alt['source'] = 'Recommendation'
                            review_list.append(alt)
                            break
            
            return ProcessResponse(message=plan.get("query_for_user", "Rebuilt from your last order."), review_items=review_list)

        # --- Sub-Logic: Create a new cart based on an event/theme ---
        elif intent == 'create_event':
            print(f"AI Plan: Create an event-based cart. Themes: {plan.get('themes')}")
            themes = plan.get("themes", [])
            if not themes:
                raise HTTPException(status_code=400, detail="The AI could not determine a theme from your request.")
            
            all_matched_products = {}
            for theme in themes:
                matched_products = search_products_hybrid(query_text=theme, match_threshold=0.35, match_count=5)
                for product in matched_products:
                    all_matched_products[product['id']] = product
            unique_product_list = list(all_matched_products.values())
            
            if not unique_product_list:
                raise HTTPException(status_code=404, detail="I couldn't find any items matching those themes.")
            
            final_review_list = curate_cart_with_llm(
                products=unique_product_list, 
                budget=plan.get("budget"),
                user_query=request.query
            )

            if not final_review_list:
                 raise HTTPException(status_code=404, detail="The AI curator could not create a cart for your request.")

            return ProcessResponse(message="Here are some AI-curated suggestions for your event!", review_items=final_review_list)
        
        else: # Handles AI planner failure
            raise HTTPException(status_code=400, detail="The AI could not understand your request. Please try rephrasing.")

    # --- Handle standard "Add to Cart" mode ---
    elif request.ai_mode == 'add_to_cart':
        print("Handling 'Add to Cart' request...")
        llm_result = extract_product_info_from_query(request.query)
        if llm_result.intent != "add_to_cart":
            raise HTTPException(status_code=400, detail="In this mode, I can only add items.")
        if not llm_result.products:
            raise HTTPException(status_code=400, detail="I couldn't find any products in your request.")

        newly_added_items = []
        for product_query in llm_result.products:
            search_query = f"{' '.join(product_query.preferences)} {product_query.name}".strip()
            matched_products = search_products_hybrid(query_text=search_query, match_threshold=0.4, match_count=1)
            if matched_products:
                top_product = matched_products[0]
                added_item = add_item_to_temp_cart(user_id=request.user_id, product=top_product, quantity=product_query.quantity)
                newly_added_items.append(added_item)
        
        if not newly_added_items:
            raise HTTPException(status_code=404, detail="Sorry, we couldn't find any of the products you asked for.")
        
        return ProcessResponse(message=f"Added {len(newly_added_items)} item(s) to your cart.", added_items=newly_added_items)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported AI mode: {request.ai_mode}")

# ===============================================
# === PDF and Bulk Add Endpoints ===
# ===============================================
@app.post("/extract_from_list", response_model=List[ExtractedProduct])
async def extract_from_list(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
    file_contents = await file.read()
    raw_text = extract_text_from_pdf(file_contents)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the PDF.")
    extracted_items_list = extract_items_from_text(raw_text)
    if not extracted_items_list:
        raise HTTPException(status_code=400, detail="The AI could not identify any shopping items in your list.")
    try:
        validated_products = [ExtractedProduct(**p) for p in extracted_items_list]
        return validated_products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"There was an error structuring the items from your list: {e}")

@app.post("/add_bulk_items", response_model=ProcessResponse)
async def add_bulk_items(request: BulkAddRequest):
    newly_added_items = []
    for product_query in request.products:
        top_product = None
        if product_query.id:
            product_details_response = supabase.table('products').select('*').eq('id', product_query.id).single().execute()
            if product_details_response.data:
                top_product = product_details_response.data
        else:
            search_query = f"{' '.join(product_query.preferences)} {product_query.name}".strip()
            matched_products = search_products_hybrid(query_text=search_query, match_threshold=0.4, match_count=1)
            if matched_products:
                top_product = matched_products[0]
        
        if top_product:
            added_item = add_item_to_temp_cart(user_id=request.user_id, product=top_product, quantity=product_query.quantity)
            newly_added_items.append(added_item)

    if not newly_added_items:
        raise HTTPException(status_code=404, detail="Sorry, we couldn't find any of the products from your list.")
    return ProcessResponse(message=f"Added {len(newly_added_items)} items from your list.", added_items=newly_added_items)


# ===============================================
# === Cart and Checkout Endpoints ===
# ===============================================
@app.get("/temp_cart/{user_id}", response_model=List[dict])
async def get_user_cart(user_id: str):
    return get_temp_cart(user_id)

@app.delete("/temp_cart_item/{user_id}/{item_id}")
async def reject_cart_item(user_id: str, item_id: str):
    return remove_item_from_temp_cart(user_id, item_id)

@app.post("/checkout/{user_id}")
async def checkout(user_id: str):
    try:
        result = create_order_from_cart(user_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal error occurred during checkout: {str(e)}")

# ===============================================
# === Root Health-Check Endpoint ===
# ===============================================
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to the Walmart Smart Cart API v5.0!"}