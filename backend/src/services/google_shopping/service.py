"""Google Shopping price comparison via SerpApi (multi-retailer)."""

from __future__ import annotations

import math
import re
from urllib.parse import parse_qs, urlparse

from src.constants import (
    GOOGLE_SHOPPING_GL,
    GOOGLE_SHOPPING_HL,
    GOOGLE_SHOPPING_LOCATION,
)
from src.pipeline_log import (
    shopping_link_unresolved,
    shopping_search_query,
    shopping_search_response,
)
from src.services.marketplace.offer_links import wrap_offer_url
from src.services.marketplace.queries import build_search_query
from src.services.marketplace.serpapi import SerpApiClient
from src.services.marketplace.verdict import listings_from_bucket_verdict

_search_client: SerpApiClient | None = None
_SHOPPING_RESULT_LIMIT = 50


def _get_search_client() -> SerpApiClient:
    global _search_client
    if _search_client is None:
        _search_client = SerpApiClient()
    return _search_client


def _numeric_price(product_data: dict) -> float | None:
    raw = product_data.get("numeric_price")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0.0 else None


def _listing_price(listing: dict) -> float:
    cleaned = re.sub(r"[^0-9.]", "", str(listing.get("price") or ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _is_google_host(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    return host.endswith("google.com") or host.endswith("google.co.uk")


def _unwrap_google_redirect(url: str) -> str:
    """Pull the real merchant URL out of a Google redirect (/url?q=, /aclk?adurl=)."""
    if not url or not _is_google_host(url):
        return url
    try:
        query = parse_qs(urlparse(url).query)
    except ValueError:
        return url
    for key in ("q", "url", "adurl"):
        values = query.get(key)
        if values and values[0].startswith("http") and not _is_google_host(values[0]):
            return values[0]
    return url


# Sellers we query through their own API — skip their Google Shopping rows since the
# direct integration has better data. Add "amazon"/"amazon." when that API lands.
_DIRECT_API_SELLERS = frozenset({"ebay"})
_DIRECT_API_HOST_FRAGMENTS = ("ebay.",)


def _is_direct_api_offer(url: str, seller: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    seller_lower = (seller or "").strip().lower()
    if seller_lower in _DIRECT_API_SELLERS:
        return True
    return any(fragment in host for fragment in _DIRECT_API_HOST_FRAGMENTS)


def _resolve_offer_url(item: dict) -> str:
    """Direct merchant link if present, else a Google link to resolve later."""
    link = _unwrap_google_redirect((item.get("link") or "").strip())
    if link and not _is_google_host(link):
        return link

    # SerpApi google_shopping rows usually only expose a Google product page; we
    # resolve the real merchant URL later via the product_id offers lookup.
    return (item.get("product_link") or "").strip()


def _offer_direct_link(offer: dict) -> str:
    for key in ("direct_link", "link", "merchant_link", "offer_link", "product_link", "url"):
        value = _unwrap_google_redirect((offer.get(key) or "").strip())
        if value and not _is_google_host(value):
            return value
    return ""


def _normalize_seller(name: str) -> str:
    """Compare on the store, ignoring SerpApi's '<Store> - <3rd-party seller>' suffix."""
    return (name or "").strip().lower().split(" - ")[0].strip()


def _immersive_stores(token: str) -> list[dict]:
    """Fetch the per-store offers (with direct merchant links) for a product."""
    if not token:
        return []
    client = _get_search_client()
    if not client.is_configured():
        return []
    try:
        data = client.search(
            engine="google_immersive_product",
            params={
                "page_token": token,
                "gl": GOOGLE_SHOPPING_GL,
                "hl": GOOGLE_SHOPPING_HL,
            },
            timeout=30.0,
        )
    except Exception:
        return []
    product_results = data.get("product_results")
    stores = product_results.get("stores") if isinstance(product_results, dict) else None
    if not isinstance(stores, list):
        return []
    return [s for s in stores if isinstance(s, dict)]


def _resolve_direct_merchant_url(token: str, seller: str, price: float | None) -> str:
    """
    Resolve a Google Shopping row to the real merchant URL for the SAME offer.

    SerpApi's google_shopping rows expose a Google product page; the offers (per
    store, with direct links) come from the google_immersive_product engine keyed
    by the row's immersive_product_page_token. We match the store by seller name
    and/or price so the destination matches the price we display.

    Returns "" when nothing matches (caller then drops the listing).
    """
    stores = _immersive_stores(token)
    if not stores:
        return ""

    target_seller = _normalize_seller(seller)

    same_seller = [
        s
        for s in stores
        if _normalize_seller(s.get("name")) == target_seller and _offer_direct_link(s)
    ]
    if same_seller:
        if price is not None:
            same_seller.sort(
                key=lambda s: abs(float(s.get("extracted_price") or 0) - price)
            )
        return _offer_direct_link(same_seller[0])

    # Seller label differs but the price pins the exact same offer.
    if price is not None:
        for s in stores:
            ep = s.get("extracted_price")
            if isinstance(ep, (int, float)) and abs(float(ep) - price) < 0.01:
                link = _offer_direct_link(s)
                if link:
                    return link

    return ""


def _resolve_listing_links(listings: list[dict]) -> list[dict]:
    """
    Replace Google-Shopping links with direct merchant URLs for verified listings.
    Drops any listing whose real store link cannot be resolved.
    """
    resolved: list[dict] = []
    for listing in listings:
        seller = listing.get("platform") or ""
        url = (listing.get("url") or "").strip()
        if url and not _is_google_host(url):
            # Skip stores we already query directly (e.g. eBay) so the same item
            # isn't listed twice when the eBay API also returned it.
            if _is_direct_api_offer(url, seller):
                continue
            resolved.append(listing)
            continue

        token = (listing.get("immersive_token") or "").strip()
        direct = _resolve_direct_merchant_url(token, seller, _listing_price(listing))
        if not direct:
            shopping_link_unresolved(
                seller=seller,
                product_token=listing.get("product_id") or "",
            )
            continue

        # The Google row only revealed it was eBay once resolved to a real link —
        # drop it; our eBay integration covers that store.
        if _is_direct_api_offer(direct, seller):
            continue

        updated = dict(listing)
        updated["url"] = wrap_offer_url(
            direct,
            seller=seller,
            product_id=listing.get("product_id") or "",
        )
        resolved.append(updated)
    return resolved


def _condition_label(item: dict) -> tuple[str, str]:
    raw_parts = [
        str(item.get("second_hand_condition") or ""),
        str(item.get("durability") or ""),
        str(item.get("condition") or ""),
        str(item.get("tag") or ""),
    ]
    extensions = item.get("extensions")
    if isinstance(extensions, list):
        raw_parts.extend(str(x) for x in extensions)
    lowered = " ".join(raw_parts).lower()

    if "refurb" in lowered:
        return "refurbished", "Refurbished"
    if "used" in lowered or "pre-owned" in lowered or "preowned" in lowered:
        return "used", "Used"
    return "new", "New"


def _parse_shopping_item(item: dict, original_price: float) -> dict | None:
    price = item.get("extracted_price")
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    if price >= original_price:
        return None

    url = _resolve_offer_url(item)
    if not url:
        return None

    seller = (item.get("source") or item.get("seller") or "").strip() or "Store"
    if _is_direct_api_offer(url, seller):
        return None

    condition_type, condition_label = _condition_label(item)
    if condition_type != "new":
        return None

    product_id = str(item.get("product_id") or "").strip()
    immersive_token = str(item.get("immersive_product_page_token") or "").strip()
    savings = round(original_price - float(price), 2)
    display_price = item.get("price") or f"${price:.2f}"
    thumbnail = (item.get("thumbnail") or item.get("image") or "").strip()

    return {
        "platform": seller,
        "condition_type": condition_type,
        "condition_label": condition_label,
        "title": (item.get("title") or "").strip(),
        "price": display_price if "$" in str(display_price) else f"${price:.2f}",
        "url": wrap_offer_url(url, seller=seller, product_id=product_id),
        "image_url": thumbnail,
        "raw_condition": condition_label,
        "savings": f"${savings:.2f}",
        "product_id": product_id,
        "google_product_id": product_id,
        "immersive_token": immersive_token,
    }


def _iter_shopping_items(data: dict) -> list[dict]:
    rows: list[dict] = []
    for key in ("shopping_results", "inline_shopping_results"):
        block = data.get(key)
        if not isinstance(block, list):
            continue
        for item in block:
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _search_google_shopping(query: str, *, max_price: float) -> list[dict]:
    client = _get_search_client()
    data = client.search(
        engine="google_shopping",
        params={
            "q": query,
            "gl": GOOGLE_SHOPPING_GL,
            "hl": GOOGLE_SHOPPING_HL,
            "location": GOOGLE_SHOPPING_LOCATION,
            "google_domain": "google.com",
            # Closest-to-original prices first (most likely the same product), and
            # cap at the page price so we only consider cheaper offers. SerpApi
            # requires max_price to be an integer; ceil keeps borderline items, and
            # the exact price filter in _parse_shopping_item enforces the real cap.
            "sort_by": "2",  # 2 = Price: high to low
            "max_price": str(max(1, math.ceil(max_price))),
        },
    )
    return _iter_shopping_items(data)


def collect_shopping_candidates(product_data: dict) -> dict:
    """Search Google Shopping (all retailers). Returns {searched, candidates}."""
    original_price = _numeric_price(product_data)
    if original_price is None:
        return {"searched": False, "candidates": []}

    client = _get_search_client()
    if not client.is_configured():
        return {"searched": False, "candidates": []}

    query = build_search_query(product_data)
    if not query:
        return {"searched": False, "candidates": []}

    shopping_search_query(query)
    try:
        items = _search_google_shopping(query, max_price=original_price)
    except Exception:
        shopping_search_response(query, [])
        items = []

    candidates: list[dict] = []
    seen_urls: set[str] = set()

    for item in items:
        listing = _parse_shopping_item(item, original_price)
        if not listing:
            continue
        url = listing.get("url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(listing)
        if len(candidates) >= _SHOPPING_RESULT_LIMIT:
            break

    candidates.sort(key=_listing_price, reverse=True)
    shopping_search_response(query, candidates)
    return {"searched": True, "candidates": candidates}


def finalize_shopping_comparison(collect_result: dict, shopping_verdict: dict) -> dict:
    """Apply combined Gemini shopping verdict to collected candidates."""
    if not collect_result.get("searched"):
        return {
            "searched": False,
            "found": False,
            "listing": None,
            "listings": [],
            "options": {"new": None, "refurbished": None},
            "match_summary": {"has_exact_match": False, "has_close_match": False},
            "verification": {"shopping": shopping_verdict},
        }

    candidates = collect_result.get("candidates") or []
    listings = listings_from_bucket_verdict(
        candidates, shopping_verdict or {}, source="shopping", bucket="new"
    )
    listings = _resolve_listing_links(listings)
    options = {"new": listings[0] if listings else None, "refurbished": None}
    listing = listings[0] if listings else None
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
            "verification": {"shopping": shopping_verdict},
        }

    return {
        "searched": True,
        "found": False,
        "listing": None,
        "listings": [],
        "options": {"new": None, "refurbished": None},
        "match_summary": match_summary,
        "verification": {"shopping": shopping_verdict},
    }
