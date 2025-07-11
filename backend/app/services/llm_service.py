import os
import requests
import json
import logging
from dotenv import load_dotenv
from fastapi import HTTPException
from app.models.api_models import LLMResponse
from typing import List
from app.models.api_models import LLMResponse
from typing import Dict
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"



def load_prompt(file_path: str) -> str:
    """A simple utility function to load a prompt text from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"FATAL: Prompt file not found at path: {file_path}")
        return "" 

PROMPT_DIR = "D:\\walmart_4\\backend\\app\\prompts" # Use double backslashes for Windows paths
EXTRACT_PRODUCTS_PROMPT = load_prompt(os.path.join(PROMPT_DIR, 'extract_products_prompt.md'))
EXTRACT_LIST_ITEMS_PROMPT = load_prompt(os.path.join(PROMPT_DIR, 'extract_list_items_prompt.md'))
LIST_MODIFICATION_PROMPT = load_prompt(os.path.join(PROMPT_DIR, 'list_modification_prompt.md'))
# in llm_service.py
# First, load the new prompt at the top
UNIFIED_PLANNER_PROMPT = load_prompt(os.path.join(PROMPT_DIR, 'unified_planner_prompt.md'))

def get_ai_plan(query: str) -> dict:
    """
    This is our new 'smart butler'. It determines the user's true intent
    by classifying the query as either 'reorder' or 'create_event'.
    """
    logging.info(f"Initiating AI Planner call for query: '{query}'")
    
    if not UNIFIED_PLANNER_PROMPT:
        logging.error("Unified planner prompt is not loaded. Cannot proceed.")
        return {"intent": "error", "message": "Planner prompt not configured."}

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": UNIFIED_PLANNER_PROMPT}, {"role": "user", "content": query}],
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        llm_output = response.json()['choices'][0]['message']['content']
        logging.debug(f"Raw AI Planner Output: {llm_output}")
        
        # Use our robust JSON parsing to handle extra text
        start_index = llm_output.find('{')
        end_index = llm_output.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            raise json.JSONDecodeError("Could not find a valid JSON object in the planner response.", llm_output, 0)

        json_str = llm_output[start_index:end_index]
        parsed_json = json.loads(json_str)
        logging.info(f"AI Planner Response: {parsed_json}")
        return parsed_json

    except Exception as e:
        logging.error(f"Failed during AI plan extraction: {e}")
        return {"intent": "error", "message": str(e)}

def extract_items_from_text(text: str) -> List[dict]:
    """
    Calls the LLM with a simple prompt to get a list of products.
    It does not care about intent. It just returns a list of dictionaries.
    """
    logging.info("Initiating LLM call for simple list item extraction.")
    
    # Robust JSON parsing logic from our other function
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [{"role": "system", "content": EXTRACT_LIST_ITEMS_PROMPT}, {"role": "user", "content": text}],
        }
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        llm_output = response.json()['choices'][0]['message']['content']
        
        start_index = llm_output.find('[')
        end_index = llm_output.rfind(']') + 1
        if start_index == -1 or end_index == 0:
            raise json.JSONDecodeError("Could not find a JSON array in the LLM response.", llm_output, 0)

        json_str = llm_output[start_index:end_index]
        parsed_list = json.loads(json_str)
        return parsed_list
    except Exception as e:
        logging.error(f"Failed during simple list extraction: {e}")
        return [] # Return an empty list on failure

SYSTEM_PROMPT = """
You are an expert Walmart shopping assistant. Your task is to receive a natural language query from a user and extract key product information.
You MUST respond in a valid JSON format. Do not add any text or explanations outside of the JSON structure.

The JSON output MUST follow this precise format. The "products" key MUST be a JSON array (wrapped in []), even if there is only one or zero products.
{
    "products": [
        {
            "name": "The core name of the product",
            "quantity": The number of items, as an integer (default to 1 if not specified),
            "preferences": ["A list of adjectives or specific details like color, flavor, brand, size, etc."]
        }
    ],
    "intent": "This can be 'add_to_cart', 'recommend', 'search', or 'unknown'."
}
--- EXAMPLES ---
User Query: "I need 2 big packets of blue lays please"
Your JSON Response:
{ "products": [ { "name": "lays", "quantity": 2, "preferences": ["big", "blue"] } ], "intent": "add_to_cart" }

User Query: "what's a good face wash for oily skin?"
Your JSON Response:
{ "products": [], "intent": "recommend" }
"""

def extract_product_info_from_query(query: str) -> LLMResponse:
    """
    Calls the OpenRouter API, extracts structured product information, and validates it.
    This function includes logic to clean up and fix common LLM formatting errors.
    """
    logging.info("Initiating LLM service call to OpenRouter.")

    if not OPENROUTER_API_KEY:
        logging.error("OpenRouter API key not configured.")
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured.")

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": query}],
    }

    parsed_json = {}  
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        llm_output = response.json()['choices'][0]['message']['content']
        logging.debug(f"Raw LLM Output: {llm_output}")

        start_index = llm_output.find('{')
        end_index = llm_output.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            raise json.JSONDecodeError("Could not find a JSON object in the LLM response.", llm_output, 0)

        json_str = llm_output[start_index:end_index]
        parsed_json = json.loads(json_str)
        logging.info(f"Successfully parsed JSON from LLM: {parsed_json}")

        # Case 1: LLM returned just the product object directly.
        if "products" not in parsed_json and "name" in parsed_json:
            logging.warning("Fixing LLM structural error: LLM returned a product object directly. Wrapping it in standard response structure.")
            parsed_json = {
                "products": [parsed_json],
                "intent": "add_to_cart" # Assume default intent
            }
        # Case 2: 'products' is a dict, not a list.
        elif "products" in parsed_json and isinstance(parsed_json.get("products"), dict):
            logging.warning("Fixing LLM structural error: 'products' was a dict, converting to list.")
            parsed_json["products"] = [parsed_json["products"]]

        validated_response = LLMResponse(**parsed_json)
        logging.info("LLM response validated successfully.")
        return validated_response

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error calling OpenRouter: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=503, detail=f"Error from LLM service: {e.response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling OpenRouter API: {e}")
        raise HTTPException(status_code=503, detail=f"Error communicating with the LLM service: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM JSON response. Error: {e}. Original text was: {llm_output}")
        raise HTTPException(status_code=500, detail="Failed to parse response from the LLM service.")
    except Exception as e:
        logging.error(f"Validation error for LLM response. Error: {e}. Parsed JSON: {parsed_json}")
        raise HTTPException(status_code=500, detail="LLM response did not match the required data structure.")
    

# in backend/app/services/llm_service.py

def get_list_modification_action(user_command: str, current_list: List[Dict]) -> Dict:
    """
    Takes a user's voice command and the current review list, and determines
    the specific action to perform on that list.
    """
    logging.info("Initiating LLM call for list modification action.")
    
    if not LIST_MODIFICATION_PROMPT:
        return {"action": "error", "detail": "List modification prompt not loaded."}

    # Format the context for the LLM
    list_for_prompt = json.dumps(
        [{"id": item.get("id"), "name": item.get("name"), "quantity": item.get("quantity")} for item in current_list],
        indent=2
    )
    
    prompt_context = (
        f"CURRENT LIST:\n{list_for_prompt}\n\n"
        f"USER COMMAND: \"{user_command}\"\n"
    )
    
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": LIST_MODIFICATION_PROMPT}, {"role": "user", "content": prompt_context}],
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        llm_output = response.json()['choices'][0]['message']['content']
        
        # Robust JSON parsing
        start_index = llm_output.find('{')
        end_index = llm_output.rfind('}') + 1
        json_str = llm_output[start_index:end_index]
        parsed_action = json.loads(json_str)
        
        logging.info(f"LLM returned action: {parsed_action}")
        return parsed_action
    except Exception as e:
        logging.error(f"Failed during list modification action extraction: {e}")
        return {"action": "error", "detail": str(e)}
