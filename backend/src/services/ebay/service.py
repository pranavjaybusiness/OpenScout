import re

from src.pipeline_log import ebay_search_query, ebay_search_response
from src.services.ebay.affiliate import wrap_ebay_affiliate_url
from src.services.ebay.client import EbayBrowseClient
from src.services.marketplace.queries import build_search_query
from src.services.marketplace.verdict import listings_from_bucket_verdict

_browse_client: EbayBrowseClient | None = None
_NEW_CONDITION_IDS = {"1000"}
_EBAY_SEARCH_LIMIT = 50


def _get_browse_client() -> EbayBrowseClient:
    global _browse_client
    if _browse_client is None:
        _browse_client = EbayBrowseClient()
    return _browse_client


def _listing_price(listing: dict) -> float:
    cleaned = re.sub(r"[^0-9.]", "", str(listing.get("price") or ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _numeric_price(product_data: dict) -> float | None:
    raw = product_data.get("numeric_price")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0.0 else None


def _listing_bucket(item: dict) -> str:
    """Map API-filtered conditionId to new vs refurbished bucket for Gemini."""
    condition_id = (item.get("condition_id") or "").strip()
    if condition_id in _NEW_CONDITION_IDS:
        return "new"
    return "refurbished"


def _as_listing(item: dict, original_price: float, condition_bucket: str) -> dict:
    ebay_price = item["price"]
    savings = round(original_price - ebay_price, 2)
    label = "New" if condition_bucket == "new" else "Refurbished"
    return {
        "platform": "eBay",
        "condition_type": condition_bucket,
        "condition_label": label,
        "title": item.get("title") or "",
        "price": f"${ebay_price:.2f}",
        "url": wrap_ebay_affiliate_url(item.get("itemWebUrl") or ""),
        "image_url": item.get("image_url") or "",
        "raw_condition": item.get("condition") or "",
        "savings": f"${savings:.2f}",
    }


def collect_ebay_candidates(product_data: dict) -> dict:
    """Search eBay only (no Gemini). Returns {searched, candidates}."""
    original_price = _numeric_price(product_data)
    if original_price is None:
        return {"searched": False, "candidates": {"new": [], "refurbished": []}}

    client = _get_browse_client()
    if not client.is_configured():
        return {"searched": False, "candidates": {"new": [], "refurbished": []}}

    query = build_search_query(product_data)
    if not query:
        return {"searched": False, "candidates": {"new": [], "refurbished": []}}

    candidates: dict[str, list[dict]] = {"new": [], "refurbished": []}
    seen_urls: set[str] = set()

    ebay_search_query(query)
    try:
        items = client.search_items(
            query,
            limit=_EBAY_SEARCH_LIMIT,
            max_price=original_price,
        )
    except Exception:
        ebay_search_response(query, [])
        items = []

    ebay_search_response(query, items)

    for item in items:
        ebay_price = item.get("price")
        if not isinstance(ebay_price, (int, float)) or ebay_price <= 0:
            continue
        if ebay_price >= original_price:
            continue

        bucket = _listing_bucket(item)
        listing = _as_listing(item, original_price, bucket)
        url = listing.get("url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates[bucket].append(listing)

    for key in ("new", "refurbished"):
        candidates[key] = sorted(candidates[key], key=_listing_price, reverse=True)

    return {"searched": True, "candidates": candidates}


def finalize_ebay_comparison(collect_result: dict, ebay_verdict: dict) -> dict:
    """Apply combined Gemini eBay verdict to collected candidates."""
    if not collect_result.get("searched"):
        return {
            "searched": False,
            "found": False,
            "listing": None,
            "listings": [],
            "options": {"new": None, "refurbished": None},
            "match_summary": {"has_exact_match": False, "has_close_match": False},
            "verification": {"ebay": ebay_verdict},
        }

    candidates = collect_result.get("candidates") or {}
    new_verdict = (ebay_verdict or {}).get("new") or {}
    refurb_verdict = (ebay_verdict or {}).get("refurbished") or {}

    listings: list[dict] = []
    listings.extend(
        listings_from_bucket_verdict(
            candidates.get("new") or [], new_verdict, source="ebay", bucket="new"
        )
    )
    listings.extend(
        listings_from_bucket_verdict(
            candidates.get("refurbished") or [],
            refurb_verdict,
            source="ebay",
            bucket="refurbished",
        )
    )

    selected_new = next((x for x in listings if x.get("condition_bucket") == "new"), None)
    selected_refurbished = next(
        (x for x in listings if x.get("condition_bucket") == "refurbished"), None
    )
    options = {"new": selected_new, "refurbished": selected_refurbished}
    listing = (
        min(listings, key=_listing_price) if listings else _primary_listing(options)
    )

    has_exact = any(x.get("match_quality") == "exact" for x in listings)
    has_close = any(x.get("match_quality") == "close" for x in listings)
    match_summary = {"has_exact_match": has_exact, "has_close_match": has_close}

    if listings:
        return {
            "searched": True,
            "found": True,
            "listing": listing,
            "listings": listings,
            "options": options,
            "match_summary": match_summary,
            "verification": {"ebay": ebay_verdict},
        }

    return {
        "searched": True,
        "found": False,
        "listing": None,
        "listings": [],
        "options": {"new": None, "refurbished": None},
        "match_summary": match_summary,
        "verification": {"ebay": ebay_verdict},
    }


def _primary_listing(options: dict) -> dict | None:
    candidates = [x for x in (options.get("new"), options.get("refurbished")) if x]
    if not candidates:
        return None
    return min(candidates, key=lambda x: float(x["price"].replace("$", "")))


def get_ebay_comparison(product_data: dict) -> dict:
    """Legacy entry point; prefer comparison.get_marketplace_comparisons."""
    from src.services.comparison import get_marketplace_comparisons

    ebay, _shopping = get_marketplace_comparisons(product_data)
    return ebay
