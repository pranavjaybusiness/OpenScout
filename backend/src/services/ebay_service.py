from src.pipeline_log import ebay_search_query, ebay_search_response

from src.services.ebay_affiliate import wrap_ebay_affiliate_url

from src.services.ebay_client import EbayBrowseClient

from src.services.llm_service import verify_ebay_candidates



_browse_client: EbayBrowseClient | None = None

_NEW_CONDITION_IDS = {"1000"}

# eBay Browse API allows up to 50 per request; all filtered candidates go to Gemini.
_EBAY_SEARCH_LIMIT = 50


def _get_browse_client() -> EbayBrowseClient:

    global _browse_client

    if _browse_client is None:

        _browse_client = EbayBrowseClient()

    return _browse_client





def build_ebay_queries(product_data: dict) -> list:

    """Generates prioritized search queries using the waterfall strategy."""

    queries = []

    ids_list = product_data.get("identification_numbers") or []

    ids: dict[str, str] = {}

    for item in ids_list:

        if not isinstance(item, dict):

            continue

        name = (item.get("name") or "").strip().upper()

        value = item.get("value")

        if name and value:

            ids[name] = str(value).strip()



    brand = product_data.get("brand") or ""

    gtin = ids.get("GTIN13") or ids.get("UPC") or ids.get("GTIN")

    if gtin:

        queries.append(gtin)



    model = ids.get("MODEL") or ids.get("MODEL NUMBER")

    if brand and model:

        queries.append(f"{brand} {model}".strip())



    cleaned_name = product_data.get("search_optimized_name")

    if cleaned_name:

        queries.append(cleaned_name)



    high_value_specs = []

    for spec in product_data.get("core_specifications", []):

        if spec.get("is_search_critical") is True:

            high_value_specs.append(spec.get("value"))

    if brand and high_value_specs:

        queries.append(f"{brand} {' '.join(high_value_specs)}".strip())



    seen = set()

    unique_queries = []

    for q in queries:

        if q and q not in seen:

            seen.add(q)

            unique_queries.append(q)

    return unique_queries





def _listing_price(listing: dict) -> float:
    return float(str(listing.get("price") or "$0").replace("$", ""))


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





def _listing_from_bucket_verdict(
    bucket_candidates: list[dict], bucket_verdict: dict
) -> dict | None:
    exact_index = bucket_verdict.get("exact_index")
    close_index = bucket_verdict.get("close_index")
    close_difference = (bucket_verdict.get("close_difference") or "").strip()

    reason = (bucket_verdict.get("reason") or "").strip()[:2000]

    if isinstance(exact_index, int) and 0 <= exact_index < len(bucket_candidates):
        listing = dict(bucket_candidates[exact_index])
        listing["match_quality"] = "exact"
        if reason:
            listing["gemini_match_reason"] = reason
        return listing

    if isinstance(close_index, int) and 0 <= close_index < len(bucket_candidates):
        listing = dict(bucket_candidates[close_index])
        listing["match_quality"] = "close"
        listing["close_match_note"] = (
            close_difference
            or "Minor difference from what you're viewing (e.g. color or capacity)."
        )
        if reason:
            listing["gemini_match_reason"] = reason
        return listing

    return None


def find_cheaper_alternatives(product_data: dict) -> dict:

    original_price = _numeric_price(product_data)

    if original_price is None:

        return {"new": None, "refurbished": None}



    client = _get_browse_client()

    if not client.is_configured():

        return {"new": None, "refurbished": None}



    queries = build_ebay_queries(product_data)

    candidates: dict[str, list[dict]] = {"new": [], "refurbished": []}

    seen_urls: set[str] = set()

    for query in queries:

        ebay_search_query(query)

        try:

            items = client.search_items(
                query,
                limit=_EBAY_SEARCH_LIMIT,
                max_price=original_price,
            )

        except Exception:

            ebay_search_response(query, [])

            continue

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
        candidates[key] = sorted(
            candidates[key],
            key=_listing_price,
            reverse=True,
        )



    if not candidates["new"] and not candidates["refurbished"]:

        return {"new": None, "refurbished": None}



    try:

        verdict = verify_ebay_candidates(product_data, candidates)

    except Exception:

        verdict = {
            "new": {
                "exact_index": None,
                "close_index": None,
                "close_difference": None,
                "reason": None,
            },
            "refurbished": {
                "exact_index": None,
                "close_index": None,
                "close_difference": None,
                "reason": None,
            },
        }

    selected_new = _listing_from_bucket_verdict(candidates["new"], verdict.get("new") or {})
    selected_refurbished = _listing_from_bucket_verdict(
        candidates["refurbished"], verdict.get("refurbished") or {}
    )

    return {
        "new": selected_new,
        "refurbished": selected_refurbished,
        "verification": verdict,
    }





def _primary_listing(options: dict) -> dict | None:

    candidates = [x for x in (options.get("new"), options.get("refurbished")) if x]

    if not candidates:

        return None

    return min(candidates, key=lambda x: float(x["price"].replace("$", "")))





def get_ebay_comparison(product_data: dict) -> dict:

    if _numeric_price(product_data) is None:

        return {

            "searched": False,

            "found": False,

            "listing": None,

            "options": {"new": None, "refurbished": None},

        }



    raw_options = find_cheaper_alternatives(product_data)
    verification = raw_options.pop("verification", {})
    options = raw_options

    listing = _primary_listing(options)

    has_exact = any(
        opt and opt.get("match_quality") == "exact" for opt in options.values()
    )

    has_close = any(
        opt and opt.get("match_quality") == "close" for opt in options.values()
    )

    match_summary = {
        "has_exact_match": has_exact,
        "has_close_match": has_close,
    }

    if listing:

        return {
            "searched": True,
            "found": True,
            "listing": listing,
            "options": options,
            "match_summary": match_summary,
            "verification": verification,
        }

    return {
        "searched": True,
        "found": False,
        "listing": None,
        "options": {"new": None, "refurbished": None},
        "match_summary": match_summary,
        "verification": verification,
    }


