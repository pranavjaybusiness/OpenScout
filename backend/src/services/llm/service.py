import json
from urllib.parse import urlparse

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
    name: str = Field(
        description=(
            "Identifier type label. Use retailer-specific names when applicable "
            "(e.g. ASIN on Amazon, store SKU). Use universal names for global codes "
            "(UPC, GTIN, EAN, ISBN, MPN)."
        )
    )
    value: str = Field(description="The actual identification number")

class ProductSpecification(BaseModel):
    category: str = Field(description="The type of spec (e.g., 'CPU', 'Material', 'Capacity')")
    value: str = Field(description="The concise, exact value (e.g., 'Ryzen 7', 'Leather', '28 cu ft').")
    is_search_critical: bool = Field(description="Set to true ONLY if this specification is a major defining feature of the product that a user would type into a search bar to find it (e.g., 'Ryzen 7' for a PC, 'Leather' for a couch, 'French Door' for a fridge). Set to false for minor details like dimensions, weight, or voltage.")

class ProductExtraction(BaseModel):
    name: str | None = Field(description="The full product name as it appears on the page.")
    price: str | None = Field(description="The formatted price for display, including currency symbol, e.g., '$649.99'")
    search_optimized_name: str | None = Field(
        description=(
            "Clean, concise name optimized for searching this product on eBay and other "
            "marketplaces. Remove promotional words; limit to ~7 core descriptive words. "
            "Apply site_context rules from the system prompt: prefix with the store brand only "
            "when the site is the product's own brand store and the page title lacks it; never "
            "prefix multi-brand retailers (Amazon, Walmart, Target, etc.)."
        )
    )
    numeric_price: float | None = Field(description="The exact numeric price as a pure float for mathematical comparison. e.g., 649.99. No currency symbols or commas.")
    brand: str | None
    image_url: str | None
    identification_numbers: list[IdentificationNumber] | None
    core_specifications: list[ProductSpecification] | None = Field(description="Extract ONLY critical, factual specifications. Strictly exclude features, marketing fluff, and promotional text.")


class CloseMatchEntry(BaseModel):
    index: int = Field(description="Candidate index for a close (not exact) match.")
    difference: str = Field(
        description="Short user-facing note (e.g. 'Color: listing is Black, your page is White')."
    )


class EbayBucketVerification(BaseModel):
    exact_indices: list[int] = Field(
        default_factory=list,
        description=(
            "Every EXACT match index in this bucket. Include ALL qualifying exact matches, "
            "not only the cheapest. Empty when none qualify."
        ),
    )
    close_matches: list[CloseMatchEntry] = Field(
        default_factory=list,
        description=(
            "Close matches ONLY when exact_indices is empty. Include ALL qualifying close "
            "matches with per-listing difference notes."
        ),
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Explanation for this bucket: why these listings match, or why all were rejected."
        ),
    )


class EbayVerificationResult(BaseModel):
    new: EbayBucketVerification
    refurbished: EbayBucketVerification


class MarketplaceVerificationResult(BaseModel):
    ebay: EbayVerificationResult
    shopping: EbayBucketVerification = Field(
        description=(
            "All qualifying matches among shopping.candidates (Google Shopping retailers, "
            "new only). Same exact_indices / close_matches rules as eBay new bucket."
        )
    )


_VERIFICATION_SYSTEM_INSTRUCTION = """You are a practical product-equivalence verifier comparing a retailer product page to marketplace listing titles (eBay and other stores via Google Shopping).

You will receive one source product and candidates grouped by marketplace. Evaluate each marketplace independently.

## eBay (candidates.ebay)
For each condition bucket (new, refurbished), return:
- exact_indices: ALL EXACT match indices (every qualifying listing), or empty []
- close_matches: ONLY when exact_indices is empty—every CLOSE match as {index, difference}, or empty []
- reason: always required—a concise explanation for this bucket

The shopper sees every approved listing sorted by price so they can choose their preferred store. Return every qualifying match, not just the cheapest.

## Exact match
- Same brand and same model/product line/generation as the source.
- Same variant when the source specifies one (e.g. color): missing color on eBay counts as exact; listing must NOT clearly name a different color/variant than the source.
- Candidate indices are ordered from highest price to lowest (index 0 = most expensive still under the page price).
- Include every candidate index that is an exact match. Never include a non-exact listing when exact matches exist in that bucket.

## Close match (strict—only when no exact match exists)
- Use close_matches ONLY when exact_indices is empty for that bucket.
- Allowed: same brand AND same model/generation with ONE minor explicit mismatch stated in the title (most often color, or storage/capacity when both sides name different sizes).
- NOT allowed for close match: different brand, different model/generation (QC45 vs QuietComfort, XM4 vs XM5), accessories when source is main product, bundles, or vague "might be similar" guesses.
- Include every qualifying close match with its own difference note.

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

Return exact_indices and close_matches empty only when every candidate is clearly the wrong product—not merely because the title is vague.

## Shopping (candidates.shopping)
Google Shopping candidates are new retail from various sellers (Walmart, Target, SHEIN, Amazon, brand sites, etc.)—not eBay (eBay is separate). Return under "shopping" using the same exact_indices / close_matches / reason fields as one eBay bucket:
- exact_indices: ALL exact matches, or []
- close_matches: only when exact_indices is empty
- reason: always required
- Indices refer to shopping.candidates order (index 0 = most expensive still under the page price).
- Each candidate includes a platform field (seller name)—use title + brand/model rules, not the seller name alone.
- Include every qualifying match from different sellers (e.g. Walmart AND Amazon AND SHEIN) when each is a valid exact match."""


def _candidate_rows(candidates: list[dict]) -> list[dict]:
    return [
        {
            "index": i,
            "title": c.get("title"),
            "price": c.get("price"),
            "condition": c.get("condition_label"),
            "platform": c.get("platform"),
        }
        for i, c in enumerate(candidates)
    ]


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


def _marketplace_verification_payload(
    product_data: dict,
    ebay_candidates: dict[str, list[dict]],
    shopping_candidates: list[dict],
) -> dict:
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
            "ebay": {
                "new": [
                    {
                        "index": i,
                        "title": c.get("title"),
                        "price": c.get("price"),
                        "condition": c.get("condition_label"),
                        "raw_condition": c.get("raw_condition"),
                    }
                    for i, c in enumerate(ebay_candidates.get("new") or [])
                ],
                "refurbished": [
                    {
                        "index": i,
                        "title": c.get("title"),
                        "price": c.get("price"),
                        "condition": c.get("condition_label"),
                        "raw_condition": c.get("raw_condition"),
                    }
                    for i, c in enumerate(ebay_candidates.get("refurbished") or [])
                ],
            },
            "shopping": _candidate_rows(shopping_candidates),
        },
    }


def _empty_bucket_verdict() -> dict:
    return {"exact_indices": [], "close_matches": [], "reason": None}


def _empty_marketplace_verdict() -> dict:
    empty = _empty_bucket_verdict()
    return {
        "ebay": {"new": dict(empty), "refurbished": dict(empty)},
        "shopping": dict(empty),
    }


_PRODUCT_EXTRACTION_SYSTEM_INSTRUCTION = """You are a strict data extraction tool. Extract product details from the provided scraped page data and JSON-LD.

## Source site context
The payload includes site_context (URL and hostname of the page). Use this when building search_optimized_name:

- INCLUDE the site/retailer brand in search_optimized_name when the hostname is the product's own brand store (e.g. calvinklein.us, nike.com, apple.com, lululemon.com) AND the page title is generic or does not already contain that brand (e.g. "Blue Shorts" on calvinklein.us → "Calvin Klein blue shorts").
- Do NOT include the marketplace or retailer name when the site is a multi-brand retailer or marketplace (e.g. amazon.com, walmart.com, target.com, bestbuy.com, macys.com, nordstrom.com). Shoppers search by product brand, not where they found it (e.g. Sony headphones on amazon.com → "Sony headphones", not "Amazon Sony headphones").
- Do NOT include the site name if the product name already contains the correct brand or a specific model name.
- When unsure, prefer omitting the retailer/site name—wrong retailer prefixes hurt search more than missing them.

For all other fields: extract from page content only. The brand field is the product manufacturer/brand from the listing, not the store name (unless they are the same company).

## identification_numbers
- Always extract retailer-specific IDs when present (e.g. ASIN on amazon.com) using the correct label—they are used for match verification, not marketplace search.
- Also extract universal product codes when present (UPC, GTIN, EAN, ISBN, MPN).

Return data exactly matching the provided JSON schema. If a field is missing, return null."""


def _hostname_from_url(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def _build_extraction_payload(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text[:50000]

    identifiers = data.get("identifiers") or {}
    url = (identifiers.get("url") or "").strip()
    hostname = (identifiers.get("hostname") or "").strip().lower()
    if not hostname and url:
        hostname = _hostname_from_url(url)

    payload = {
        "site_context": {
            "url": url or None,
            "hostname": hostname or None,
        },
        "scraped_data": data,
    }
    return json.dumps(payload)[:50000]


def parse_product_text(text: str, model: str = "gemini-2.5-flash") -> str:
    response = client.models.generate_content(
        model=model,
        contents=_build_extraction_payload(text),
        config=types.GenerateContentConfig(
            system_instruction=_PRODUCT_EXTRACTION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ProductExtraction,
            temperature=0.0,
        ),
    )
    text = response.text or ""
    gemini_product_extraction(text)
    return text


def _parse_bucket_verdict(raw: dict, candidate_count: int) -> dict:
    exact_indices: list[int] = []
    seen: set[int] = set()
    for item in raw.get("exact_indices") or []:
        if isinstance(item, int) and 0 <= item < candidate_count and item not in seen:
            seen.add(item)
            exact_indices.append(item)

    if not exact_indices:
        legacy = raw.get("exact_index")
        if isinstance(legacy, int) and 0 <= legacy < candidate_count:
            exact_indices = [legacy]

    close_matches: list[dict] = []
    if not exact_indices:
        for entry in raw.get("close_matches") or []:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or not (0 <= index < candidate_count):
                continue
            if any(m["index"] == index for m in close_matches):
                continue
            difference = (entry.get("difference") or "").strip()
            close_matches.append({"index": index, "difference": difference})

        if not close_matches:
            close_index = raw.get("close_index")
            close_difference = (raw.get("close_difference") or "").strip()
            if isinstance(close_index, int) and 0 <= close_index < candidate_count:
                close_matches = [{"index": close_index, "difference": close_difference}]

    reason = (raw.get("reason") or "").strip()[:2000] or None

    return {
        "exact_indices": exact_indices,
        "close_matches": close_matches,
        "reason": reason,
    }


def verify_marketplace_candidates(
    product_data: dict,
    ebay_candidates: dict[str, list[dict]],
    shopping_candidates: list[dict],
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    One Gemini call to verify eBay (new + refurbished) and Google Shopping candidates together.
    """
    ebay_new = ebay_candidates.get("new") or []
    ebay_refurbished = ebay_candidates.get("refurbished") or []
    shopping_list = shopping_candidates or []

    if not ebay_new and not ebay_refurbished and not shopping_list:
        return _empty_marketplace_verdict()

    payload = _marketplace_verification_payload(
        product_data, ebay_candidates, shopping_list
    )
    prompt = json.dumps(payload)
    gemini_verification_prompt(prompt)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_VERIFICATION_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=MarketplaceVerificationResult,
                temperature=0.0,
            ),
        )
        text = response.text or ""
        gemini_verification_response(text)
        data = json.loads(text or "{}")
    except Exception:
        return _empty_marketplace_verdict()

    ebay_data = data.get("ebay") or {}
    shopping_raw = data.get("shopping") or {}

    return {
        "ebay": {
            "new": _parse_bucket_verdict(ebay_data.get("new") or {}, len(ebay_new)),
            "refurbished": _parse_bucket_verdict(
                ebay_data.get("refurbished") or {}, len(ebay_refurbished)
            ),
        },
        "shopping": _parse_bucket_verdict(shopping_raw, len(shopping_list)),
    }