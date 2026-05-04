"""eBay OAuth (client credentials) and Browse API item search."""

from __future__ import annotations

import base64
import logging
import threading
import time
from typing import Any

import httpx

from src.constants import (
    EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET,
    EBAY_MARKETPLACE_ID,
    EBAY_USE_SANDBOX,
)

logger = logging.getLogger(__name__)

_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"


def _parse_item_summary(item: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize ItemSummary to fields used by OpenScout."""
    price_block = item.get("price")
    if not isinstance(price_block, dict):
        return None
    raw = price_block.get("value")
    if raw is None:
        return None
    try:
        price_f = float(raw)
    except (TypeError, ValueError):
        return None

    title = (item.get("title") or "").strip()
    url = (item.get("itemWebUrl") or "").strip()
    if not url:
        return None

    image_url = ""
    image = item.get("image")
    if isinstance(image, dict):
        image_url = (image.get("imageUrl") or "").strip()
    if not image_url:
        thumbs = item.get("thumbnailImages")
        if isinstance(thumbs, list) and thumbs:
            first = thumbs[0]
            if isinstance(first, dict):
                image_url = (first.get("imageUrl") or "").strip()

    return {
        "title": title,
        "price": price_f,
        "itemWebUrl": url,
        "image_url": image_url,
    }


class EbayBrowseClient:
    """Minimal client: token cache + item_summary search."""

    def __init__(self) -> None:
        sandbox = str(EBAY_USE_SANDBOX).lower() in ("1", "true", "yes")
        host = "api.sandbox.ebay.com" if sandbox else "api.ebay.com"
        self._token_url = f"https://{host}/identity/v1/oauth2/token"
        self._browse_base = f"https://{host}/buy/browse/v1"
        self._marketplace_id = (EBAY_MARKETPLACE_ID or "EBAY_US").strip()
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._token_deadline_monotonic: float = 0.0

    def is_configured(self) -> bool:
        return bool(EBAY_CLIENT_ID and EBAY_CLIENT_SECRET)

    def _mint_token_locked(self) -> str:
        """Obtain a new token. Caller must hold ``self._lock``."""
        if not self.is_configured():
            raise RuntimeError("eBay client credentials are not configured")

        raw = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
        basic = base64.b64encode(raw.encode("utf-8")).decode("ascii")

        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                self._token_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {basic}",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": _OAUTH_SCOPE,
                },
            )

        if not response.is_success:
            logger.warning(
                "eBay OAuth token request failed: %s %s",
                response.status_code,
                (response.text or "")[:400],
            )
            response.raise_for_status()

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("eBay OAuth response missing access_token")

        expires_in = int(payload.get("expires_in") or 7200)
        skew = min(300, max(30, expires_in // 10))
        self._access_token = token
        self._token_deadline_monotonic = time.monotonic() + max(60, expires_in - skew)
        return token

    def access_token(self) -> str:
        with self._lock:
            if self._access_token and time.monotonic() < self._token_deadline_monotonic:
                return self._access_token
            return self._mint_token_locked()

    def invalidate_token(self) -> None:
        with self._lock:
            self._access_token = None
            self._token_deadline_monotonic = 0.0

    def search_items(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """
        Run item_summary search. Returns normalized dicts (title, price, itemWebUrl, image_url).
        """
        if not self.is_configured():
            logger.warning("eBay credentials missing; set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET")
            return []

        trimmed = (query or "").strip()
        if not trimmed:
            return []

        base_params: list[tuple[str, str]] = [
            ("q", trimmed),
            ("limit", str(max(1, min(limit, 50)))),
            ("sort", "price"),
        ]
        fixed_price_filter: list[tuple[str, str]] = [
            *base_params,
            ("filter", "buyingOptions:{FIXED_PRICE}"),
        ]
        url = f"{self._browse_base}/item_summary/search"
        headers = {
            "Authorization": f"Bearer {self.access_token()}",
            "X-EBAY-C-MARKETPLACE-ID": self._marketplace_id,
        }

        with httpx.Client(timeout=25.0) as client:
            response = client.get(url, headers=headers, params=fixed_price_filter)
            if response.status_code == 400:
                logger.info("eBay search retrying without FIXED_PRICE filter (first request was 400)")
                response = client.get(url, headers=headers, params=base_params)

        if response.status_code == 401:
            self.invalidate_token()
            headers["Authorization"] = f"Bearer {self.access_token()}"
            with httpx.Client(timeout=25.0) as client:
                response = client.get(url, headers=headers, params=fixed_price_filter)
                if response.status_code == 400:
                    response = client.get(url, headers=headers, params=base_params)

        if response.status_code in (204,):
            return []

        if not response.is_success:
            logger.warning(
                "eBay search failed (%s) for query %r: %s",
                response.status_code,
                trimmed[:80],
                (response.text or "")[:500],
            )
            return []

        try:
            data = response.json()
        except ValueError:
            logger.warning("eBay search returned non-JSON body")
            return []

        summaries = data.get("itemSummaries")
        if not isinstance(summaries, list):
            return []

        out: list[dict[str, Any]] = []
        for item in summaries:
            if not isinstance(item, dict):
                continue
            parsed = _parse_item_summary(item)
            if parsed:
                out.append(parsed)
        return out
