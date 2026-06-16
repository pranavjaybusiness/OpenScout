"""SearchAPI.io client (Google Shopping, legacy engines, etc.)."""

from __future__ import annotations

from typing import Any

import httpx

from src.constants import SEARCHAPI_API_KEY

_SEARCHAPI_BASE = "https://www.searchapi.io/api/v1/search"


class SearchApiClient:
    def __init__(self) -> None:
        self._api_key = (SEARCHAPI_API_KEY or "").strip()

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def search(
        self,
        *,
        engine: str,
        params: dict[str, Any],
        timeout: float = 45.0,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("SEARCHAPI_API_KEY is not configured")

        query = {"engine": engine, "api_key": self._api_key, **params}
        with httpx.Client(timeout=timeout) as client:
            response = client.get(_SEARCHAPI_BASE, params=query)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError("SearchAPI returned non-object JSON")
            return data
