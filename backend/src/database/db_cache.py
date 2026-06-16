import json
import time

from botocore.exceptions import ClientError

from src.database.db_core import dynamodb, clean_url
from src.pipeline_log import dynamodb_error

cache_table = dynamodb.Table("OpenScoutCache")
TTL_SECONDS = 21600  # 6 hours


def _normalize_cached_payload(raw: dict) -> dict | None:
    """Accept {data, ebay, shopping} blobs and legacy product-only blobs."""
    if not isinstance(raw, dict):
        return None
    if "data" in raw and "ebay" in raw:
        shopping = raw.get("shopping")
        if shopping is None:
            shopping = raw.get("shein")
        return {
            "data": raw["data"],
            "ebay": raw["ebay"],
            "shopping": shopping,
            "alternatives": raw.get("alternatives"),
        }
    # Legacy: entire blob was Gemini product extraction only.
    if raw.get("name") is not None or raw.get("search_optimized_name") is not None:
        return {"data": raw, "ebay": None, "shopping": None, "alternatives": None}
    return None


def get_cached_parse(url: str) -> dict | None:
    """
    Return cached parse result: {'data', 'ebay', 'shopping'} (may be None on legacy rows).
    """
    base_url = clean_url(url)
    if not base_url:
        return None

    try:
        response = cache_table.get_item(Key={"product_url": base_url})
        item = response.get("Item")

        if item and item["expires_at"] > int(time.time()):
            raw = json.loads(item["product_data"])
            return _normalize_cached_payload(raw)
    except ClientError as e:
        dynamodb_error(operation="cache_get", error=str(e))
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return None


def save_parse_to_cache(
    url: str,
    data: dict,
    ebay: dict,
    shopping: dict | None = None,
    alternatives: list | None = None,
) -> None:
    """Store full parse outcome (Gemini extraction + marketplace comparisons)."""
    base_url = clean_url(url)
    if not base_url:
        return

    payload = json.dumps(
        {"data": data, "ebay": ebay, "shopping": shopping, "alternatives": alternatives},
        ensure_ascii=False,
    )
    try:
        cache_table.put_item(
            Item={
                "product_url": base_url,
                "product_data": payload,
                "expires_at": int(time.time()) + TTL_SECONDS,
            }
        )
    except ClientError as e:
        dynamodb_error(operation="cache_put", error=str(e))


# Backwards-compatible aliases (tests / older imports)
def get_cached_product(url: str):
    cached = get_cached_parse(url)
    return cached["data"] if cached else None


def save_to_cache(url: str, product_data: str) -> None:
    """Legacy: product_data JSON string only. Prefer save_parse_to_cache."""
    base_url = clean_url(url)
    if not base_url:
        return
    try:
        cache_table.put_item(
            Item={
                "product_url": base_url,
                "product_data": product_data,
                "expires_at": int(time.time()) + TTL_SECONDS,
            }
        )
    except ClientError as e:
        dynamodb_error(operation="cache_put", error=str(e))
