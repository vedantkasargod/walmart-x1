import os
import requests
import json
from dotenv import load_dotenv
from fastapi import HTTPException
from app.models.api_models import LLMResponse

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Enhanced System Prompt ---
# This version is more explicit about the required JSON structure, especially the 'products' array.
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

User Query: "get me a bottle of coke"
Your JSON Response:
{ "products": [ { "name": "coke", "quantity": 1, "preferences": ["bottle"] } ], "intent": "add_to_cart" }

User Query: "what's a good face wash for oily skin?"
Your JSON Response:
{ "products": [], "intent": "recommend" }
"""

def extract_product_info_from_query(query: str) -> LLMResponse:
    """
    Calls the OpenRouter API, extracts structured product information, and validates it.
    This function includes logic to clean up and fix common LLM formatting errors.
    """
    print("\n✅✅✅ --- HITTING THE REAL OPENROUTER LLM SERVICE! --- ✅✅✅\n")

    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Data payload for the API request
    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "response_format": {"type": "json_object"}, # Asks the model to return JSON
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    }

    try:
        # --- 1. API Call ---
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=20)
        response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
        llm_output = response.json()['choices'][0]['message']['content']

        print(f"--- RAW LLM OUTPUT ---\n{llm_output}\n--- END RAW LLM OUTPUT ---")

        # --- 2. Clean and Parse JSON ---
        # This block finds the JSON object within the potentially messy LLM response string.
        start_index = llm_output.find('{')
        end_index = llm_output.rfind('}') + 1

        if start_index == -1 or end_index == 0:
            print(f"Error: Could not find a JSON object in the response: {llm_output}")
            raise json.JSONDecodeError("Could not find a JSON object in the LLM response.", llm_output, 0)

        json_str = llm_output[start_index:end_index]
        parsed_json = json.loads(json_str)
        
        print(f"--- PARSED JSON ---\n{parsed_json}\n--- END PARSED JSON ---")

        # --- 3. Fix Common Structural Errors ---
        # This block handles cases where the LLM forgets to put the product object inside a list.
        if "products" in parsed_json and isinstance(parsed_json.get("products"), dict):
            print("--- FIXING LLM MISTAKE: Converting 'products' object to a list. ---")
            parsed_json["products"] = [parsed_json["products"]]

        # --- 4. Validate with Pydantic ---
        # This is the final step where Pydantic checks if all keys and value types are correct.
        # If this fails, it means the structure is still wrong (e.g., missing keys, wrong data types).
        validated_response = LLMResponse(**parsed_json)
        
        return validated_response

    # --- 5. Comprehensive Error Handling ---
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error calling OpenRouter: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=503, detail=f"Error from LLM service: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        raise HTTPException(status_code=503, detail=f"Error communicating with the LLM service: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM JSON response: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse response from the LLM service.")
    except Exception as e:
        # This is a catch-all for other errors, most likely the Pydantic validation error.
        print(f"An unexpected error occurred, likely during data validation: {e}")
        # We explicitly name the likely cause in the error detail for clearer debugging.
        raise HTTPException(status_code=500, detail="LLM response did not match the required data structure.")