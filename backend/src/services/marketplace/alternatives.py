"""Merge verified marketplace listings into one price-sorted list."""

from urllib.parse import urlparse


def _listing_price(listing: dict) -> float:
    raw = listing.get("numeric_price")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    text = str(listing.get("price") or "$0")
    cleaned = text.replace("US$", "").replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return float("inf")


def _store_key(listing: dict) -> str:
    """Normalize the seller so each website appears at most once."""
    platform = (listing.get("platform") or "").strip().lower()
    if platform and platform != "store":
        return platform
    host = (urlparse(listing.get("url") or "").netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "store"


def _match_quality(listing: dict) -> str:
    return (listing.get("match_quality") or "exact").strip().lower()


def build_alternatives(ebay_result: dict, shopping_result: dict) -> list[dict]:
    """
    Verified cheaper listings across eBay and Google Shopping, cheapest first.

    Exact matches (same model + same variant) are always kept. Close matches
    (same model, different variant—e.g. another color) are kept only when they are
    cheaper than the cheapest exact match, since a close match that costs more than
    the exact item adds no value. When there is no exact match at all, every close
    match is kept. At most one exact and one close listing survive per store.
    """
    combined: list[dict] = []
    for listing in ebay_result.get("listings") or []:
        if isinstance(listing, dict):
            combined.append(listing)
    for listing in shopping_result.get("listings") or []:
        if isinstance(listing, dict):
            combined.append(listing)

    combined.sort(key=_listing_price)

    exact_prices = [
        _listing_price(x) for x in combined if _match_quality(x) == "exact"
    ]
    cheapest_exact = min(exact_prices) if exact_prices else None

    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for listing in combined:
        url = (listing.get("url") or "").strip()
        if not url:
            continue
        quality = _match_quality(listing)
        if (
            quality == "close"
            and cheapest_exact is not None
            and _listing_price(listing) >= cheapest_exact
        ):
            continue
        key = (_store_key(listing), quality)
        if key in seen:
            continue
        seen.add(key)
        unique.append(listing)

    return unique
