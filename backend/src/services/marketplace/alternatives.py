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


def build_alternatives(ebay_result: dict, shopping_result: dict) -> list[dict]:
    """
    Verified cheaper listings across eBay and Google Shopping, cheapest first,
    keeping only the cheapest option per store.
    """
    combined: list[dict] = []
    for listing in ebay_result.get("listings") or []:
        if isinstance(listing, dict):
            combined.append(listing)
    for listing in shopping_result.get("listings") or []:
        if isinstance(listing, dict):
            combined.append(listing)

    combined.sort(key=_listing_price)

    seen_stores: set[str] = set()
    unique: list[dict] = []
    for listing in combined:
        url = (listing.get("url") or "").strip()
        if not url:
            continue
        store = _store_key(listing)
        if store in seen_stores:
            continue
        seen_stores.add(store)
        unique.append(listing)

    return unique
