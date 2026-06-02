"""eBay OAuth (client credentials) and Browse API item search."""

from __future__ import annotations

import base64
import threading
import time
from typing import Any

import httpx

from src.constants import (
    EBAY_CLIENT_ID,
    EBAY_CLIENT_SECRET,
    EBAY_MARKETPLACE_ID,
)

_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"

# Browse API conditionIds: New, Certified Refurbished, Seller Refurbished (no Used).
_CONDITION_IDS_FILTER = "conditionIds:{1000|2000|2500}"


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
        "condition": (item.get("condition") or "").strip(),
        "condition_id": str(item.get("conditionId") or "").strip(),
    }


class EbayBrowseClient:
    """Minimal client: token cache + item_summary search."""

    def __init__(self) -> None:
        # Production-only (no sandbox)
        self._token_url = "https://api.ebay.com/identity/v1/oauth2/token"
        self._browse_base = "https://api.ebay.com/buy/browse/v1"
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

    def search_items(
        self,
        query: str,
        *,
        limit: int = 20,
        sort: str | None = "-price",
        max_price: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run item_summary search. Returns normalized dicts (title, price, itemWebUrl, image_url).

        Uses sort=-price so eBay returns the highest-priced matches first (closest to the
        retail page price). Optional max_price caps results below the page price dynamically.
        """
        if not self.is_configured():
            return []

        trimmed = (query or "").strip()
        if not trimmed:
            return []

        base_params: list[tuple[str, str]] = [
            ("q", trimmed),
            ("limit", str(max(1, min(limit, 50)))),
        ]
        if sort:
            base_params.append(("sort", sort))

        filters: list[str] = [
            "buyingOptions:{FIXED_PRICE}",
            _CONDITION_IDS_FILTER,
        ]
        if max_price is not None and max_price > 0:
            cap = max(1.0, float(max_price) - 0.01)
            filters.append(f"price:[1..{cap:.2f}]")
            filters.append("priceCurrency:USD")

        filtered_params = [*base_params, ("filter", ",".join(filters))]
        url = f"{self._browse_base}/item_summary/search"
        headers = {
            "Authorization": f"Bearer {self.access_token()}",
            "X-EBAY-C-MARKETPLACE-ID": self._marketplace_id,
        }

        with httpx.Client(timeout=25.0) as client:
            response = client.get(url, headers=headers, params=filtered_params)
            if response.status_code == 400:
                response = client.get(url, headers=headers, params=base_params)

        if response.status_code == 401:
            self.invalidate_token()
            headers["Authorization"] = f"Bearer {self.access_token()}"
            with httpx.Client(timeout=25.0) as client:
                response = client.get(url, headers=headers, params=filtered_params)
                if response.status_code == 400:
                    response = client.get(url, headers=headers, params=base_params)

        if response.status_code in (204,):
            return []

        if not response.is_success:
            return []

        try:
            data = response.json()
        except ValueError:
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
        # eBay sort=-price should already be high→low; keep stable ordering.
        out.sort(key=lambda item: item["price"], reverse=True)
        return out
