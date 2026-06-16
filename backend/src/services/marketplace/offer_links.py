"""Wrap retailer offer URLs with affiliate params when configured."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from src.services.ebay.affiliate import wrap_ebay_affiliate_url
from src.services.shein.affiliate import wrap_shein_affiliate_url

_SHEIN_PRODUCT_ID = re.compile(r"-p-(\d+)", re.IGNORECASE)


def _shein_product_id_from_url(url: str) -> str | None:
    match = _SHEIN_PRODUCT_ID.search(url or "")
    return match.group(1) if match else None


def wrap_offer_url(url: str, *, seller: str = "", product_id: str = "") -> str:
    """
    Apply affiliate tracking when OpenScout supports the retailer; otherwise return
    the merchant link unchanged (e.g. Walmart with no affiliate program).
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return url

    host = (urlparse(cleaned).netloc or "").lower()
    seller_lower = (seller or "").lower()

    if "ebay." in host or seller_lower == "ebay":
        return wrap_ebay_affiliate_url(cleaned)

    if "shein.com" in host or "shein" in seller_lower:
        pid = (product_id or "").strip() or _shein_product_id_from_url(cleaned)
        return wrap_shein_affiliate_url(cleaned, product_id=pid or None)

    return cleaned
