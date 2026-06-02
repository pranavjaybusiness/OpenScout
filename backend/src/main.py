import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.constants import OPENSCOUT_ALLOWED_ORIGINS
from src.pipeline_log import (
    configure_logging,
    feedback_received,
    log_event,
    parse_cache_hit,
    parse_cache_miss,
    parse_error,
    request_error,
    request_finished,
    request_started,
)
from src.services.llm_service import parse_product_text
from src.services.ebay_service import get_ebay_comparison
from src.database.db_cache import get_cached_parse, save_parse_to_cache
from src.database.db_history import log_analysis, save_user_feedback
from src.observability.cloudwatch_metrics import (
    record_match_feedback_no,
    record_match_feedback_no_response,
    record_match_feedback_yes,
)

configure_logging()

app = FastAPI()

_cors_origins = OPENSCOUT_ALLOWED_ORIGINS if OPENSCOUT_ALLOWED_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _finish(request: Request, response, started_at: float, **extra):
    request_finished(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        started_at=started_at,
        extra=extra or None,
    )
    return response


@app.middleware("http")
async def openscout_request_logging(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    started = request_started(method=request.method, path=request.url.path)

    if OPENSCOUT_ALLOWED_ORIGINS:
        origin = (request.headers.get("origin") or "").strip()
        if origin and origin not in OPENSCOUT_ALLOWED_ORIGINS:
            return _finish(
                request,
                JSONResponse(status_code=403, content={"detail": "Forbidden"}),
                started,
                blocked_origin=origin,
            )

    try:
        response = await call_next(request)
    except Exception as exc:
        request_error(
            method=request.method,
            path=request.url.path,
            status_code=500,
            started_at=started,
            error=str(exc),
            exc=exc,
        )
        raise

    return _finish(request, response, started)


class ScrapeRequest(BaseModel):
    raw_text: str


class MatchFeedbackRequest(BaseModel):
    scan_id: str
    product_url: str
    user_feedback: str


class FeedbackSkippedRequest(BaseModel):
    scan_id: str
    product_url: str


@app.post("/feedback")
async def feedback_endpoint(body: MatchFeedbackRequest):
    feedback = (body.user_feedback or "").strip().lower()
    if feedback not in ("yes", "no"):
        raise HTTPException(status_code=400, detail="user_feedback must be yes or no.")

    saved = save_user_feedback(
        scan_id=body.scan_id,
        product_url=body.product_url,
        user_feedback=feedback,
    )
    if not saved:
        raise HTTPException(status_code=400, detail="Could not save feedback.")

    feedback_received(
        scan_id=body.scan_id,
        product_url=body.product_url,
        user_feedback=feedback,
    )

    if feedback == "yes":
        record_match_feedback_yes()
    else:
        record_match_feedback_no()

    return {"status": "success"}


@app.post("/feedback/skipped")
async def feedback_skipped_endpoint(body: FeedbackSkippedRequest):
    """User closed the modal without answering Same product? — metrics only."""
    record_match_feedback_no_response()
    log_event(
        "feedback_skipped",
        scan_id=body.scan_id,
        product_url=body.product_url,
    )
    return {"status": "success"}


@app.post("/parse")
async def parse_endpoint(body: ScrapeRequest):
    product_url = ""
    try:
        incoming_data = json.loads(body.raw_text)

        product_url = incoming_data.get("identifiers", {}).get("url", "")

        cached = get_cached_parse(product_url)
        if cached:
            parsed_product_data = cached["data"]
            ebay = cached["ebay"]
            legacy_upgrade = ebay is None
            parse_cache_hit(product_url=product_url, legacy_upgrade=legacy_upgrade)
            if legacy_upgrade:
                # Legacy cache row: product only — run eBay once and upgrade cache.
                ebay = get_ebay_comparison(parsed_product_data)
                save_parse_to_cache(product_url, parsed_product_data, ebay)
            ebay_listing_url = ((ebay.get("listing") or {}).get("url") or "").strip()
            scan_id = log_analysis(
                product_url,
                json.dumps(parsed_product_data),
                ebay_listing_url=ebay_listing_url,
                ebay=ebay,
            )
            return {
                "status": "success",
                "data": parsed_product_data,
                "ebay": ebay,
                "scan_id": scan_id,
            }

        parse_cache_miss(product_url=product_url)
        llm_response_string = parse_product_text(body.raw_text)

        parsed_product_data = json.loads(llm_response_string)

        ebay = get_ebay_comparison(parsed_product_data)
        ebay_listing_url = ((ebay.get("listing") or {}).get("url") or "").strip()

        save_parse_to_cache(product_url, parsed_product_data, ebay)
        scan_id = log_analysis(
            product_url,
            llm_response_string,
            ebay_listing_url=ebay_listing_url,
            ebay=ebay,
        )
        return {
            "status": "success",
            "data": parsed_product_data,
            "ebay": ebay,
            "scan_id": scan_id,
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format received from extension.")
    except HTTPException:
        raise
    except Exception as e:
        parse_error(product_url=product_url, error=str(e), exc=e)
        raise HTTPException(status_code=500, detail=str(e))
