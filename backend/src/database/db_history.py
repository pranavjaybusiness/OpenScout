import json
import time
import uuid

from botocore.exceptions import ClientError

from src.database.db_core import dynamodb, clean_url
from src.pipeline_log import dynamodb_error

history_table = dynamodb.Table("OpenScoutHistory")


def _new_scan_id() -> str:
    return str(uuid.uuid4())


def _verification_snapshot(ebay: dict | None) -> str:
    """JSON blob of Gemini verdict + selected listings for audit."""
    if not ebay:
        return ""
    verification = ebay.get("verification") or {}
    options = ebay.get("options") or {}
    snapshot = {"gemini_verification": verification, "selected": {}}
    for bucket in ("new", "refurbished"):
        listing = options.get(bucket)
        if not listing:
            continue
        snapshot["selected"][bucket] = {
            "title": listing.get("title"),
            "url": listing.get("url"),
            "price": listing.get("price"),
            "match_quality": listing.get("match_quality"),
            "gemini_match_reason": listing.get("gemini_match_reason"),
            "close_match_note": listing.get("close_match_note"),
        }
    try:
        return json.dumps(snapshot, ensure_ascii=False)[:350000]
    except (TypeError, ValueError):
        return ""


def log_analysis(
    url: str,
    product_data: str,
    ebay_listing_url: str | None = None,
    *,
    ebay: dict | None = None,
    user_id: str | None = None,
) -> str | None:
    """Write a history row; returns scan_id (partition key) or None on failure."""
    base_url = clean_url(url)
    if not base_url:
        return None

    try:
        scan_id = _new_scan_id()
        timestamp_ms = int(time.time() * 1000)

        item = {
            "scan_id": scan_id,
            "product_url": base_url,
            "analyzed_at": timestamp_ms,
            "product_data": product_data,
            "ebay_listing_url": (ebay_listing_url or "").strip(),
        }
        item["ebay_match_found"] = bool(item["ebay_listing_url"])

        verification_json = _verification_snapshot(ebay)
        if verification_json:
            item["gemini_verification"] = verification_json

        if user_id:
            item["user_id"] = str(user_id)[:128]

        history_table.put_item(Item=item)
        return scan_id
    except ClientError as e:
        dynamodb_error(operation="history_put", error=str(e))
        return None
    except Exception as e:
        dynamodb_error(operation="history_put", error=str(e))
        return None


def save_user_feedback(
    scan_id: str,
    product_url: str,
    user_feedback: str,
    *,
    user_id: str | None = None,
) -> bool:
    """Set user_feedback ('yes' | 'no') on an existing history row."""
    sid = (scan_id or "").strip()
    base_url = clean_url(product_url)
    if not sid or not base_url:
        return False

    feedback = (user_feedback or "").strip().lower()
    if feedback not in ("yes", "no"):
        return False

    try:
        update_expr = "SET user_feedback = :uf"
        values: dict = {":uf": feedback}
        if user_id:
            update_expr += ", user_id = :uid"
            values[":uid"] = str(user_id)[:128]

        history_table.update_item(
            Key={
                "scan_id": sid,
                "product_url": base_url,
            },
            UpdateExpression=update_expr,
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(scan_id)",
        )
        return True
    except ClientError as e:
        dynamodb_error(operation="history_feedback", error=str(e))
        return False
