from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- LLM and Query Models ---
# These are fine, but let's ensure min_length is good for simple queries.
class ExtractedProduct(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="The name of the product, e.g., 'lays' or 'milk'.")
    quantity: int = Field(default=1, description="The number of units the user wants.")
    preferences: List[str] = Field(default=[], description="User preferences like color, flavor, brand e.g., ['blue', 'magic masala'].")

class LLMResponse(BaseModel):
    products: List[ExtractedProduct]
    intent: Literal["add_to_cart", "search", "recommend", "greeting", "farewell", "chitchat", "unknown"] = Field(..., description="The user's perceived intent.")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's natural language query.")
    user_id: str = Field(..., description="A unique identifier for the user.")
    session_id: str = Field(..., description="A unique identifier for the current chat session.")
    ai_mode: Optional[str] = None


# --- API Response Models ---

class ProductSuggestion(BaseModel):
    """
    This model is still useful for other potential features, so we keep it.
    """
    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    confidence_score: float = Field(..., ge=0, le=1, description="How confident we are that this is the right product.")

# --- THIS IS THE CORRECTED MODEL ---
class ProcessResponse(BaseModel):
    """
    A flexible response model that can handle items added directly to the cart
    OR items that need to be reviewed by the user first.
    Both list fields are optional to prevent validation errors.
    """
    status: str = "success"
    message: str
    added_items: Optional[List[dict]] = None  # <-- MAKE THIS OPTIONAL
    review_items: Optional[List[dict]] = None # <-- ENSURE THIS IS OPTIONAL

class BulkAddRequest(BaseModel):
    """
    Defines the request body for adding a user-confirmed list of items to the cart.
    """
    user_id: str
    products: List[ExtractedProduct]