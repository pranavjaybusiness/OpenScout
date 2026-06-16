"""Shared marketplace search query builder (one query per product)."""

# Only cross-retailer codes help eBay/SHEIN search. Retailer IDs (ASIN, store SKU, etc.)
# stay in product_data for Gemini verification—not in the search string.
_UNIVERSAL_SEARCH_IDENTIFIERS = frozenset(
    {
        "GTIN13",
        "GTIN12",
        "GTIN8",
        "GTIN",
        "UPC",
        "EAN",
        "ISBN",
        "MPN",
    }
)

_UNIVERSAL_SEARCH_ORDER = (
    "GTIN13",
    "GTIN12",
    "GTIN8",
    "UPC",
    "GTIN",
    "EAN",
    "ISBN",
    "MPN",
)

_MODEL_KEYS = ("MODEL", "MODEL NUMBER")


def _parse_identifiers(product_data: dict) -> dict[str, str]:
    ids: dict[str, str] = {}
    for item in product_data.get("identification_numbers") or []:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip().upper()
        value = item.get("value")
        if name and value:
            ids[name] = str(value).strip()
    return ids


def _universal_search_ids(ids: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in ids.items() if key in _UNIVERSAL_SEARCH_IDENTIFIERS}


def _query_contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _append_identifiers(base: str, ids: dict[str, str]) -> str:
    """Append universal identifier values not already present in the base query."""
    parts = [base] if base else []
    for key in _UNIVERSAL_SEARCH_ORDER:
        value = ids.get(key)
        if not value or _query_contains(base, value):
            continue
        parts.append(value)
    return " ".join(parts).strip()


def build_search_query(product_data: dict) -> str | None:
    """
    Build a single search string: product name plus universal identifiers (GTIN/UPC/EAN/etc.).

    Retailer-specific IDs (e.g. ASIN on Amazon) are excluded—they do not help on eBay/SHEIN.
    All identification_numbers are still available to Gemini for verification.
    """
    ids = _parse_identifiers(product_data)
    universal = _universal_search_ids(ids)
    brand = (product_data.get("brand") or "").strip()

    name = (product_data.get("search_optimized_name") or product_data.get("name") or "").strip()
    if name:
        query = _append_identifiers(name, universal)
        return query or None

    model = ids.get("MODEL") or ids.get("MODEL NUMBER")
    if brand and model:
        return _append_identifiers(f"{brand} {model}".strip(), universal) or None

    for key in _UNIVERSAL_SEARCH_ORDER:
        value = universal.get(key)
        if value:
            return value

    return None
