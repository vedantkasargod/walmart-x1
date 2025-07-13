import os
import logging
from typing import List, Optional
import json


from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client
from fastapi import WebSocket, WebSocketDisconnect
from app.services.voice_service import speech_to_text_http

# --- Import all our Pydantic Models ---
from app.models.api_models import QueryRequest, ProcessResponse, ExtractedProduct, BulkAddRequest, ModifyReviewRequest

# --- Import all our Service Functions ---
from app.services.llm_service import get_ai_plan, extract_product_info_from_query, extract_items_from_text
from app.services.product_service import search_products_hybrid
from app.services.cart_service import add_item_to_temp_cart, remove_item_from_temp_cart, get_temp_cart
from app.services.ocr_service import extract_text_from_pdf
from app.services.order_service import create_order_from_cart, get_last_order_for_user
from app.services.budget_service import curate_cart_with_llm
from app.services.review_service import create_review_session, get_review_session, clear_review_session
from app.services.llm_service import get_list_modification_action
from app.services.voice_service import text_to_speech_stream
from fastapi.responses import StreamingResponse

# --- Load Environment Variables ---
load_dotenv()

# --- Supabase Client Initialization ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



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
        review_list = []

        if intent == 'reorder':
            print("AI Plan: Reorder the last cart.")
            last_order_items = get_last_order_for_user(request.user_id)
            if not last_order_items:
                raise HTTPException(status_code=404, detail="You have no previous orders to rebuild from!")
            
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
        
        elif intent == 'create_event':
            print(f"AI Plan: Create an event-based cart. Themes: {plan.get('themes')}")
            themes = plan.get("themes", [])
            if not themes:
                raise HTTPException(status_code=400, detail="The AI could not determine a theme.")
            
            all_matched_products = {}
            for theme in themes:
                matched_products = search_products_hybrid(query_text=theme, match_threshold=0.35, match_count=5)
                for product in matched_products:
                    all_matched_products[product['id']] = product
            unique_product_list = list(all_matched_products.values())
            
            if not unique_product_list:
                raise HTTPException(status_code=404, detail="Could not find items matching themes.")
            
            review_list = curate_cart_with_llm(
                products=unique_product_list, 
                budget=plan.get("budget"),
                user_query=request.query
            )
        
        else:
            raise HTTPException(status_code=400, detail="The AI could not understand your request.")

        # --- New Behavior: Save the generated list to a review session ---
        if review_list:
            create_review_session(request.user_id, review_list)
            return ProcessResponse(
                message=plan.get("query_for_user", "A new list is ready for your review!"),
            )
        else:
            raise HTTPException(status_code=404, detail="The AI could not generate a list for that request.")
        
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
    
@app.get("/speak")
async def speak_text(text: str):
    """
    Receives text, generates speech using ElevenLabs, and streams the
    audio back to the client by handling the generator directly.
    """
    try:
        audio_generator = text_to_speech_stream(text)
        
        # --- THE FIX ---
        # Create a generator function to yield the audio chunks for StreamingResponse
        async def stream_audio():
            for chunk in audio_generator:
                yield chunk
        # --- END OF FIX ---

        return StreamingResponse(stream_audio(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")

@app.post("/transcribe_audio")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Receives an audio file from the frontend and returns the transcription.
    """
    audio_bytes = await audio.read()
    transcript = speech_to_text_http(audio_bytes)
    return {"transcript": transcript}

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

@app.get("/review_session/{user_id}", response_model=List[dict])
async def get_user_review_session(user_id: str):
    """Retrieves the review session list for a user from Redis."""
    session_items = get_review_session(user_id)
    if session_items is None:
        return []
    return session_items

@app.post("/modify_review_list/{user_id}")
async def modify_review_list(user_id: str, request: ModifyReviewRequest):
    """
    Takes a user's voice command, gets the AI action, modifies the review
    session in Redis, and returns a confirmation message.
    """
    # 1. Get the current state of the review list from Redis
    current_list = get_review_session(user_id)
    if current_list is None:
        raise HTTPException(status_code=404, detail="No active review session found to modify.")

    # 2. Get the structured action from our "Action Taker" LLM
    action_data = get_list_modification_action(request.command, current_list)
    action_type = action_data.get("action")
    
    message = "I'm not sure how to do that. Please try again." # Default message

    # 3. Execute the action
    if action_type == "remove":
        item_id_to_remove = action_data.get("item_id")
        # Create a new list excluding the item to be removed
        updated_list = [item for item in current_list if item.get("id") != item_id_to_remove]
        create_review_session(user_id, updated_list) # Save the new list back to Redis
        message = "Okay, I've removed that item."

    elif action_type == "update_quantity":
        item_id_to_update = action_data.get("item_id")
        new_quantity = action_data.get("quantity")
        
        for item in current_list:
            if item.get("id") == item_id_to_update:
                item["quantity"] = new_quantity
                break
        create_review_session(user_id, current_list) # Save the modified list
        message = "Got it. I've updated the quantity."

    elif action_type == "confirm_add":
        # This action tells the frontend to proceed with adding the items to the cart.
        # We don't modify the list, just send a specific message.
        message = "CONFIRM_ADD" # A special keyword the frontend will look for

    elif action_type == "unknown":
        message = "I didn't understand that command. Can you rephrase?"

    # 4. Return a simple message for the AI to speak
    # The frontend will then re-fetch the review session to update the UI.
    return {"message": message}


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