"""Append SHEIN KOC/affiliate tracking parameters to product URLs.

There is no SHEIN search API call in OpenScout. This is only applied when a
Google Shopping result points at SHEIN, so our affiliate params are attached.
"""

from __future__ import annotations

import secrets
import uuid
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.constants import (
    SHEIN_AFFILIATE_CAMPAIGN_ID,
    SHEIN_AFFILIATE_KOC_ID,
    SHEIN_AFFILIATE_ONELINK,
)

# Params observed on SHEIN KOC affiliate product links.
_SHEIN_AFFILIATE_QUERY_KEYS = frozenset(
    {
        "onelink",
        "requestid",
        "campaign_id",
        "url_from",
        "behaviorid",
    }
)


def _normalize_product_url(url: str, product_id: str | None) -> str:
    cleaned = (url or "").strip()
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    if cleaned and not cleaned.startswith("http"):
        cleaned = f"https://{cleaned.lstrip('/')}"

    parsed = urlparse(cleaned)
    if parsed.netloc and "-p-" in (parsed.path or ""):
        return cleaned

    pid = (product_id or "").strip()
    if not pid:
        return cleaned

    host = (parsed.netloc or "us.shein.com").lower()
    if not host.endswith("shein.com"):
        host = "us.shein.com"

    return f"https://{host}/-p-{pid}.html"


def _koc_query_params(product_id: str | None = None) -> list[tuple[str, str]] | None:
    """
    SHEIN KOC-style query params, or None when not configured.

    Matches observed affiliate links:
      url_from=affiliate_koc_{koc_id}&campaign_id=...&onelink=...&requestId=olw-...&behaviorId=goods.{uuid}
    """
    if not SHEIN_AFFILIATE_KOC_ID:
        return None

    params: list[tuple[str, str]] = [
        ("url_from", f"affiliate_koc_{SHEIN_AFFILIATE_KOC_ID}"),
    ]
    if SHEIN_AFFILIATE_CAMPAIGN_ID:
        params.append(("campaign_id", SHEIN_AFFILIATE_CAMPAIGN_ID))
    if SHEIN_AFFILIATE_ONELINK:
        params.append(("onelink", SHEIN_AFFILIATE_ONELINK))

    params.append(("requestId", f"olw-{secrets.token_hex(8)}"))
    behavior_seed = (product_id or "").strip() or secrets.token_hex(16)
    params.append(("behaviorId", f"goods.{uuid.uuid5(uuid.NAMESPACE_URL, behavior_seed)}"))
    return params


def wrap_shein_affiliate_url(url: str, *, product_id: str | None = None) -> str:
    """
    Add SHEIN affiliate parameters when env is configured; otherwise return url unchanged.

    Reference KOC links use:
      onelink, requestId, campaign_id, url_from=affiliate_koc_{id}, behaviorId=goods.{uuid}
    """
    affiliate = _koc_query_params(product_id=product_id)
    if affiliate is None:
        return url

    target = _normalize_product_url(url, product_id)
    if not target:
        return url

    parsed = urlparse(target)
    if "shein.com" not in (parsed.netloc or "").lower():
        return url

    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _SHEIN_AFFILIATE_QUERY_KEYS
    ]
    query = urlencode([*kept, *affiliate])

    return urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path,
            "",
            query,
            "",
        )
    )
