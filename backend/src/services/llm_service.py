from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.constants import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

class IdentificationNumber(BaseModel):
    name: str = Field(description="The name of the identifier (e.g., ASIN, SKU, UPC)")
    value: str = Field(description="The actual identification number")

class ProductSpecification(BaseModel):
    category: str = Field(description="The type of spec (e.g., 'CPU', 'Material', 'Capacity')")
    value: str = Field(description="The concise, exact value (e.g., 'Ryzen 7', 'Leather', '28 cu ft').")
    is_search_critical: bool = Field(description="Set to true ONLY if this specification is a major defining feature of the product that a user would type into a search bar to find it (e.g., 'Ryzen 7' for a PC, 'Leather' for a couch, 'French Door' for a fridge). Set to false for minor details like dimensions, weight, or voltage.")

class ProductExtraction(BaseModel):
    name: str | None = Field(description="The full product name as it appears on the page.")
    price: str | None = Field(description="The formatted price for display, including currency symbol, e.g., '$649.99'")
    search_optimized_name: str | None = Field(description="A clean, concise version of the name optimized for search engines. Remove promotional words and limit to 7 core descriptive words.")
    numeric_price: float | None = Field(description="The exact numeric price as a pure float for mathematical comparison. e.g., 649.99. No currency symbols or commas.")
    brand: str | None
    image_url: str | None
    identification_numbers: list[IdentificationNumber] | None
    core_specifications: list[ProductSpecification] | None = Field(description="Extract ONLY critical, factual specifications. Strictly exclude features, marketing fluff, and promotional text.")

def parse_product_text(text: str, model: str = "gemini-2.5-flash") -> str:
    response = client.models.generate_content(
        model=model,
        contents=text[:50000], 
        config=types.GenerateContentConfig(
            system_instruction="You are a strict data extraction tool. Extract the product details from the provided text and JSON-LD data. Return the data exactly matching the provided JSON schema. If a field is missing, return null.",
            response_mime_type="application/json",
            response_schema=ProductExtraction,
            temperature=0.0, 
        ),
    )
    return response.text