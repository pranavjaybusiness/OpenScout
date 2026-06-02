"""Structured JSON logs on stdout — Lambda forwards to CloudWatch Logs."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any

_LOGGER_NAME = "openscout"


def _level_name() -> str:
    return (os.environ.get("LOG_LEVEL") or "INFO").upper()


def _should_log(level: str) -> bool:
    order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
    configured = order.get(_level_name(), 20)
    return order.get(level.upper(), 20) >= configured


def configure_logging() -> None:
    """Suppress noisy third-party loggers; OpenScout uses stdout JSON via log_event."""
    for name in (
        "httpx",
        "httpcore",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "botocore",
        "boto3",
        "urllib3",
        "google",
        "google_genai",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def log_event(event: str, level: str = "INFO", **fields: Any) -> None:
    if not _should_log(level):
        return
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "event": event,
        **fields,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def log_exception(event: str, exc: BaseException, **fields: Any) -> None:
    log_event(
        event,
        level="ERROR",
        error=str(exc),
        traceback=traceback.format_exc(),
        **fields,
    )


def _log_step(step: str, payload: Any) -> None:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass
    log_event(step, payload=payload)


def request_started(*, method: str, path: str, user_id: str | None = None) -> float:
    log_event("request_started", method=method, path=path, user_id=user_id)
    return time.perf_counter()


def request_finished(
    *,
    method: str,
    path: str,
    status_code: int,
    started_at: float,
    user_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    fields: dict[str, Any] = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        "user_id": user_id,
    }
    if extra:
        fields.update(extra)
    log_event("request_finished", **fields)


def request_error(
    *,
    method: str,
    path: str,
    status_code: int,
    started_at: float,
    error: str,
    user_id: str | None = None,
    exc: BaseException | None = None,
) -> None:
    fields: dict[str, Any] = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
        "user_id": user_id,
        "error": error,
    }
    if exc is not None:
        fields["traceback"] = traceback.format_exc()
    log_event("request_error", level="ERROR", **fields)


def parse_cache_hit(*, product_url: str, legacy_upgrade: bool = False) -> None:
    log_event(
        "parse_cache_hit",
        product_url=product_url,
        legacy_upgrade=legacy_upgrade,
    )


def parse_cache_miss(*, product_url: str) -> None:
    log_event("parse_cache_miss", product_url=product_url)


def parse_error(*, product_url: str, error: str, exc: BaseException | None = None) -> None:
    if exc is not None:
        log_exception("parse_error", exc, product_url=product_url)
    else:
        log_event("parse_error", level="ERROR", product_url=product_url, error=error)


def feedback_received(
    *,
    scan_id: str,
    product_url: str,
    user_feedback: str,
    user_id: str | None = None,
) -> None:
    log_event(
        "feedback_received",
        scan_id=scan_id,
        product_url=product_url,
        user_feedback=user_feedback,
        user_id=user_id,
    )


def dynamodb_error(*, operation: str, error: str) -> None:
    log_event("dynamodb_error", level="WARNING", operation=operation, error=error)


def gemini_product_extraction(response: str) -> None:
    _log_step("gemini_product_extraction", response)


def ebay_search_query(query: str) -> None:
    _log_step("ebay_search_query", query)


def ebay_search_response(query: str, items: list[dict[str, Any]]) -> None:
    _log_step(
        "ebay_search_response",
        {
            "query": query,
            "count": len(items),
            "items": items,
        },
    )


def gemini_verification_prompt(prompt: str) -> None:
    _log_step("gemini_verification_prompt", prompt)


def gemini_verification_response(response: str) -> None:
    _log_step("gemini_verification_response", response)
