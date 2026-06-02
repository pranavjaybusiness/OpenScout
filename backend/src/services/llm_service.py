import json

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.constants import GEMINI_API_KEY
from src.pipeline_log import (
    gemini_product_extraction,
    gemini_verification_prompt,
    gemini_verification_response,
)

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


class EbayBucketVerification(BaseModel):
    exact_index: int | None = Field(
        description="Best exact-equivalent listing index, or null if none."
    )
    close_index: int | None = Field(
        description=(
            "Index of a close (not exact) match ONLY when exact_index is null—"
            "same brand and model/generation with one minor explicit difference "
            "(e.g. color). Never a different model or brand."
        )
    )
    close_difference: str | None = Field(
        description="Short user-facing note for close_index (e.g. 'Color: listing is Black, your page is White')."
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Explanation of your decision for this bucket: why the chosen index is an "
            "exact or close match, or why every candidate was rejected."
        ),
    )


class EbayVerificationResult(BaseModel):
    new: EbayBucketVerification
    refurbished: EbayBucketVerification


_VERIFICATION_SYSTEM_INSTRUCTION = """You are a practical product-equivalence verifier comparing a retailer product page to eBay listing titles.

For each condition bucket (new, refurbished), return:
- exact_index: the best EXACT match (same sellable item the shopper is viewing), or null
- close_index: ONLY if exact_index is null—a CLOSE match (see below), or null
- close_difference: required when close_index is set (plain English, e.g. "Color: eBay listing is Black, your page is White")
- reason: always required for each bucket—a concise explanation of why you picked that index, or why all candidates were rejected

## Exact match
- Same brand and same model/product line/generation as the source.
- Same variant when the source specifies one (e.g. color): missing color on eBay counts as exact; listing must NOT clearly name a different color/variant than the source.
- Candidate indices are ordered from highest price to lowest (index 0 = most expensive still under the page price).
- If multiple exact matches exist, pick the cheapest among them (highest index / lowest price). Never pick a non-exact listing when an exact match exists, even if it is cheaper.

## Close match (strict—only when no exact match exists)
- Use close_index ONLY when there is no exact_index for that bucket.
- Allowed: same brand AND same model/generation with ONE minor explicit mismatch stated in the eBay title (most often color, or storage/capacity when both sides name different sizes).
- NOT allowed for close match: different brand, different model/generation (QC45 vs QuietComfort, XM4 vs XM5), accessories when source is main product, bundles, or vague "might be similar" guesses.
- If multiple close matches qualify, pick the cheapest among them (highest index / lowest price).

## How to read eBay titles
- Titles are often incomplete. Do NOT require year in the title when the product line name otherwise matches.
- Missing color on eBay → treat as exact, not close.
- Explicit different color in title vs source → exact_index null; may be close_index if same model.
- Reject different generation when the title explicitly names it (QC45, WH-1000XM4, etc.).

## Accessories vs main products (important)
- First infer whether the SOURCE product is a main product or an accessory/consumable/part (case, charger, cable, ear pads, filter, lid, band, remote, replacement part, etc.) from its name and specifications.
- If the source IS an accessory or part: select eBay listings that are the same accessory/part for the same compatible product. Do NOT reject them for being "only an accessory."
- If the source is a main product: reject listings that are accessories, replacement parts, bundles of unrelated items, or compatible-only add-ons—not the core device itself.

## Condition buckets
- Candidates are pre-filtered: "new" bucket = eBay conditionId 1000 only; "refurbished" = 2000/2500 only.
- Used, open box, for-parts, and all other conditions are already excluded—do not recommend them.
- "new": brand-new retail equivalents of the same item (not refurbished).
- "refurbished": manufacturer- or seller-refurbished equivalents of the same item only.

Return both indices null only when every candidate is clearly the wrong product—not merely because the title is vague."""


def _verification_payload(product_data: dict, candidates: dict[str, list[dict]]) -> dict:
    return {
        "source_product": {
            "name": product_data.get("name"),
            "search_optimized_name": product_data.get("search_optimized_name"),
            "brand": product_data.get("brand"),
            "price": product_data.get("price"),
            "numeric_price": product_data.get("numeric_price"),
            "identification_numbers": product_data.get("identification_numbers"),
            "core_specifications": product_data.get("core_specifications"),
        },
        "candidates": {
            "new": [
                {
                    "index": i,
                    "title": c.get("title"),
                    "price": c.get("price"),
                    "condition": c.get("condition_label"),
                    "raw_condition": c.get("raw_condition"),
                }
                for i, c in enumerate(candidates.get("new") or [])
            ],
            "refurbished": [
                {
                    "index": i,
                    "title": c.get("title"),
                    "price": c.get("price"),
                    "condition": c.get("condition_label"),
                    "raw_condition": c.get("raw_condition"),
                }
                for i, c in enumerate(candidates.get("refurbished") or [])
            ],
        },
    }


def parse_product_text(text: str, model: str = "gemini-2.5-flash") -> str:
    response = client.models.generate_content(
        model=model,
        contents=text[:50000], 
        config=types.GenerateContentConfig(
            system_instruction="You are a strict data extraction tool. Extract the product details from the provided text and JSON-LD data. Return data exactly matching the provided JSON schema. If a field is missing, return null.",
            response_mime_type="application/json",
            response_schema=ProductExtraction,
            temperature=0.0, 
        ),
    )
    text = response.text or ""
    gemini_product_extraction(text)
    return text


def _parse_bucket_verdict(raw: dict, candidate_count: int) -> dict:
    exact_index = raw.get("exact_index")
    close_index = raw.get("close_index")
    close_difference = (raw.get("close_difference") or "").strip() or None

    if not isinstance(exact_index, int) or not (0 <= exact_index < candidate_count):
        exact_index = None
    if not isinstance(close_index, int) or not (0 <= close_index < candidate_count):
        close_index = None

    if exact_index is not None:
        close_index = None
        close_difference = None

    reason = (raw.get("reason") or "").strip()[:2000] or None

    return {
        "exact_index": exact_index,
        "close_index": close_index,
        "close_difference": close_difference,
        "reason": reason,
    }


def verify_ebay_candidates(
    product_data: dict,
    candidates: dict[str, list[dict]],
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Verify listings per bucket. Returns exact/close indices for new and refurbished.
    """
    payload = _verification_payload(product_data, candidates)
    prompt = json.dumps(payload)
    gemini_verification_prompt(prompt)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_VERIFICATION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=EbayVerificationResult,
            temperature=0.0,
        ),
    )

    text = response.text or ""
    gemini_verification_response(text)
    data = json.loads(text or "{}")

    new_candidates = candidates.get("new") or []
    refurbished_candidates = candidates.get("refurbished") or []

    return {
        "new": _parse_bucket_verdict(data.get("new") or {}, len(new_candidates)),
        "refurbished": _parse_bucket_verdict(
            data.get("refurbished") or {}, len(refurbished_candidates)
        ),
    }