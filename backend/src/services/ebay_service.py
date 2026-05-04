import logging



from src.services.ebay_client import EbayBrowseClient



logger = logging.getLogger(__name__)



_browse_client: EbayBrowseClient | None = None





def _get_browse_client() -> EbayBrowseClient:

    global _browse_client

    if _browse_client is None:

        _browse_client = EbayBrowseClient()

    return _browse_client





def build_ebay_queries(product_data: dict) -> list:

    """

    Generates a prioritized list of search queries using the Waterfall Strategy.

    """

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



    high_value_specs = []

    for spec in product_data.get("core_specifications", []):

        if spec.get("is_search_critical") is True:

            high_value_specs.append(spec.get("value"))



    if brand and high_value_specs:

        spec_string = " ".join(high_value_specs)

        queries.append(f"{brand} {spec_string}".strip())



    cleaned_name = product_data.get("search_optimized_name")

    if cleaned_name:

        queries.append(cleaned_name)



    seen = set()

    unique_queries = []

    for q in queries:

        if q and q not in seen:

            seen.add(q)

            unique_queries.append(q)



    return unique_queries





def _search_cheaper_listing(query: str, original_price: float) -> dict | None:

    """

    Call Browse search and return the first fixed-price item strictly cheaper than original_price.

    Results are sorted by ascending price from eBay.

    """

    client = _get_browse_client()

    if not client.is_configured():

        return None



    try:

        items = client.search_items(query, limit=25)

    except Exception as exc:

        logger.warning("eBay search raised for query %r: %s", query[:80], exc)

        return None



    for item in items:

        ebay_price = item["price"]

        if ebay_price <= 0 or ebay_price >= original_price:

            continue

        savings = round(original_price - ebay_price, 2)

        return {

            "platform": "eBay",

            "title": item["title"],

            "price": f"${ebay_price:.2f}",

            "url": item["itemWebUrl"],

            "image_url": item.get("image_url") or "",

            "savings": f"${savings:.2f}",

        }



    return None





def _numeric_price(product_data: dict) -> float | None:

    raw = product_data.get("numeric_price")

    try:

        value = float(raw)

    except (TypeError, ValueError):

        return None

    if value <= 0.0:

        return None

    return value





def find_cheaper_alternative(product_data: dict) -> dict | None:

    original_price = _numeric_price(product_data)

    if original_price is None:

        return None



    queries = build_ebay_queries(product_data)



    for query in queries:

        listing = _search_cheaper_listing(query, original_price)

        if listing:

            logger.info("Found cheaper eBay listing via query %r", query[:80])

            return listing



    return None





def get_ebay_comparison(product_data: dict) -> dict:


    if _numeric_price(product_data) is None:

        return {"searched": False, "found": False, "listing": None}



    listing = find_cheaper_alternative(product_data)

    if listing:

        return {"searched": True, "found": True, "listing": listing}

    return {"searched": True, "found": False, "listing": None}


