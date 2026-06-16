"""Orchestrate parallel marketplace search + one combined Gemini verification."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from src.constants import ENABLE_EBAY, ENABLE_SHOPPING
from src.services.ebay import collect_ebay_candidates, finalize_ebay_comparison
from src.services.google_shopping import collect_shopping_candidates, finalize_shopping_comparison
from src.services.llm import verify_marketplace_candidates


def _empty_ebay_collect() -> dict:
    return {"searched": False, "candidates": {"new": [], "refurbished": []}}


def _empty_shopping_collect() -> dict:
    return {"searched": False, "candidates": []}


def get_marketplace_comparisons(product_data: dict) -> tuple[dict, dict]:
    """
    Run enabled marketplace searches in parallel, then one Gemini call for both.

    Toggle per marketplace via .env or shell (no code changes):
      OPENSCOUT_ENABLE_EBAY=false      — skip eBay
      OPENSCOUT_ENABLE_SHOPPING=false  — skip Google Shopping (all retailers)
    """
    ebay_enabled = ENABLE_EBAY
    shopping_enabled = ENABLE_SHOPPING

    ebay_collect = _empty_ebay_collect()
    shopping_collect = _empty_shopping_collect()

    if ebay_enabled or shopping_enabled:
        max_workers = int(ebay_enabled) + int(shopping_enabled)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            ebay_future = (
                pool.submit(collect_ebay_candidates, product_data)
                if ebay_enabled
                else None
            )
            shopping_future = (
                pool.submit(collect_shopping_candidates, product_data)
                if shopping_enabled
                else None
            )
            if ebay_future is not None:
                ebay_collect = ebay_future.result()
            if shopping_future is not None:
                shopping_collect = shopping_future.result()

    verification = verify_marketplace_candidates(
        product_data,
        ebay_collect.get("candidates") or {},
        shopping_collect.get("candidates") or [],
    )

    ebay = finalize_ebay_comparison(ebay_collect, verification.get("ebay") or {})
    shopping = finalize_shopping_comparison(
        shopping_collect, verification.get("shopping") or {}
    )
    return ebay, shopping
